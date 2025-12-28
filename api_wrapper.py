from __future__ import print_function
import configparser
import json
import os
import requests
import json_to_csv
import sys
import pandas as pd
import time
import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

def unnest(field):
   return re.sub(r'^\w+\.','', field)

def get_json_val(parser, section, option, fallback=None):
    val = parser.get(section, option, fallback=None)
    return json.loads(val) if val is not None else fallback

def get_primary_key(entity):
    use_patent_id = {
        "g_brf_sum_text", "g_claim", "g_detail_desc_text", "g_draw_desc_text",
        "patent", "patent/foreign_citation", "patent/other_reference",
        "patent/rel_app_text", "patent/us_application_citation",
        "patent/us_patent_citation",
    }
    use_doc_num = {
        "pg_brf_sum_text", "pg_claim", "pg_detail_desc_text",
        "pg_draw_desc_text", "publication", "publication/rel_app_text"
    }

    if entity in use_patent_id:
        return "patent_id"
    if entity in use_doc_num:
        return "document_number"

    clean_name = entity.removeprefix("patent/")
    return f"{clean_name}_id"

def get_secondary_key(entity):
    key_map = {
        "g_claim": "claim_sequence",
        "pg_claim": "claim_sequence",
        "g_draw_desc_text": "draw_desc_sequence",
        "pg_draw_desc_text": "draw_desc_sequence",
        "patent/foreign_citation": "citation_sequence",
        "patent/us_application_citation": "citation_sequence",
        "patent/us_patent_citation": "citation_sequence",
        "patent/other_reference": "reference_sequence",
    }

    return key_map.get(entity)

def get_sort_config(parser, section, available_fields):
    """
    Extracts and validates sort fields and directions from the parser.
    Returns a tuple of (sort_fields, sort_directions).

    If specified, 'sort' should be a list of dictionaries, specifying
    the order of keys and direction of each key.
    """

    default_config = (None, None)
    raw_sort = parser.get(section, 'sort', fallback=None)
    if not raw_sort:
        return default_config

    try:
        sort_data = json.loads(raw_sort)

        validated = [
            (field, direction)
            for item in sort_data
            for field, direction in item.items()
            if field in available_fields
        ]

        if validated:
            fields, directions = zip(*validated)
            return list(fields), list(directions)

    except (json.JSONDecodeError, TypeError, KeyError):
        # Catch specific errors only (e.g., malformed JSON or unexpected structure)
        pass

    return default_config

@dataclass
class QueryConfig:
    name: str
    entity: str
    input_file: Path
    input_type: str
    fields: list
    directory: Path
    join_on: str | None
    criteria: dict
    user_sort_fields: list
    user_sort_directions: list
    added_fields: list[str] = field(default_factory=list)
    api_sort: list = field(init=False)
    pk: str = field(init=False)
    sk: str = field(init=False)
    input_df: pd.DataFrame | None = None

    def __post_init__(self):
        self.pk = get_primary_key(self.entity)
        self.sk = get_secondary_key(self.entity)
        sort_keys = [k for k in (self.pk, self.sk) if k]
        self.api_sort = [{k: "asc"} for k in sort_keys]
        # give the user the API sort if they didn't supply one
        if self.user_sort_fields is None:
           self.user_sort_fields = sort_keys
           self.user_sort_directions = ["asc" for k in sort_keys]
        # Ensure PK/SK are in fields for paging- removed later
        for k in sort_keys:
            if k not in self.fields:
                self.fields.append(k)
                self.added_fields.append(k)

def safe_patentsview_post(entity, headers, json_data):
    url="https://search.patentsview.org/api/v1/" + entity
    r = requests.post(url, headers=headers, json=json_data)
    if r.status_code == 429:
        wait = int(r.headers.get("Retry-After", 60))
        print(f"Throttled. Retrying in {wait}s...")
        time.sleep(wait)
        return requests.post(url, headers=headers, json=json_data)
    return r

def handle_error(r, entity, field, value):
    details=f"{entity} endpoint for field {field} value {value}"
    match r.status_code:
        case 403:
            print(f"API key not accepted at {details}")
        case code if 400 <= code <= 499:
            print(f"Client error {code} at {details}")
            print(r.headers.get("X-Status-Reason", "No reason provided"))
        case code if code >= 500:
            print(f"Server error {code} at {details}. Request may exceed 1GB limit.")
        case _:
            print(f"Unexpected error {code} at {details}")

    sys.exit(1)

def fetch_pages(config, item, api_key):
    """
    Query the API, paging through the results util we receive a partial page
    """
    after, secondary = None, None
    headers = {'X-Api-Key': api_key, 'User-Agent': 'https://github.com/mustberuss/PatentsView-APIWrapper'}

    while True:
        params = {
            'q': {"_and": [{config.input_type: item}, config.criteria]},
            'f': config.fields,
            'o': {"size": 1000, "after": [after, secondary] if secondary else after},
            's': config.api_sort
        }
        if not after: params['o'].pop('after') # Clean first request

        r = safe_patentsview_post(config.entity, headers, params)

        if r.status_code != 200:
            handle_error(r, config.entity, config.input_type, item)
            break

        data = r.json()
        yield data

        if data['count'] < 1000:
            break

        # Update paging keys from last row
        entity_key = list(data.keys())[3]
        last_row = data[entity_key][-1]
        after = last_row[config.pk]
        secondary = last_row.get(config.sk)

def strip_unrequested_fields(json_response, fields):
    """
    Cover for an API bug
    The API occasionally sends back unrequested fields while paging,
    creating havoc in our dataframe and csv files
    """
    error, page_size, total_size, entity = list(json_response.keys())
    raw_data = json_response[entity]

    # from the requested fields, create a unique list of the highlevel entities
    # (unfully-qualify and dedupe) We'll keep only requested fields
    requested_entities =  list(set([s.split('.', 1)[0] for s in fields]))

    filtered_data = [{key: value for key, value in d.items() if key in requested_entities} for d in raw_data]

    # TODO: test if this is needed:
    # we want the opposite too, we might have requested fields that weren't returned
    # ex gov_interest_organizations.  remove items that don't have all the requested entities
    trimmed_data = [
        item for item in filtered_data
        if all(field in item for field in requested_entities)
    ]

    json_response[entity] = trimmed_data
    return json_response

def repack_output(config, q_name):
    """
    The original version of this script did a lot of file io that
    we still do here- ahead of a potential refactor.
    We'll apply the join_on if specified, reorder columns, drop duplicates,
    apply user requested sort (or API default), then resave the csv file
    """
    output_filename = os.path.join(config.directory, q_name+'.csv')
    df = pd.read_csv(output_filename, dtype=object, encoding='Latin-1')

    if config.join_on is not None:
        print(f"joining input on {config.join_on} to output on {config.input_type}")

        config.input_df.columns = 'input_' + config.input_df.columns
        left_key = 'input_' + config.join_on

        config.fields = config.input_df.columns.to_list() + config.fields
        right_key = unnest(config.input_type)
        df = pd.merge(config.input_df, df, how="inner", left_on=left_key, right_on=right_key)
        config.added_fields.append(right_key)

    # Now that we're done making API calls, we need to remove any nesting
    # from fields and sort fields
    config.fields = [unnest(field) for field in config.fields]
    config.user_sort_fields = [unnest(sf) for sf in config.user_sort_fields]  # unnest sort fields too

    df = df[config.fields].drop_duplicates().sort_values(by=config.user_sort_fields,
       ascending=[direction != 'desc' for direction in config.user_sort_directions])

    # remove fields we added, pk sk or a join key
    for field in config.added_fields: df.drop(field, axis=1, inplace=True)

    df.to_csv(output_filename, index=False)
    rows, cols = df.shape
    print(f"({rows:,d} rows returned)\n")

def run_queries(config_path, api_key):
    """
    Iterate through the queries in the specified configuration file
    """
    parser = configparser.ConfigParser()
    parser.read(config_path)

    for q_name in parser.sections():
        print(f"Running query: {q_name}")

        # 1. Build Config
        config = load_query_config(parser, q_name) # Uses QueryConfig class

        # 2. Load Worklist
        items = get_item_list(config) # Logic with pd.read_csv or open()

        # 3. Process
        results_count = 0
        for item in items:
            for page_data in fetch_pages(config, item, api_key):
                if page_data['count'] > 0:
                    page_data = strip_unrequested_fields(page_data, config.fields)
                    save_json(page_data, config.directory, q_name, results_count)
                    results_count += 1
                else:
                    print(f"zero results for {config.input_type} {item} at {config.entity} endpoint")

        # 4. Finalize
        if results_count == 0:
            print(f"Query {q_name} returned no results")
        else:
            # generate csvs from saved jsons and combine into a single csv
            json_to_csv.main(str(config.directory), q_name, results_count)
            repack_output(config, q_name)


def get_item_list(config: QueryConfig) -> list:
    """
    Reads the input file and returns a deduplicated list of items.
    Handles both raw text files and CSV columns based on config.join_on.
    """
    file_path = config.directory / config.input_file

    # 1. Validation: Ensure the file actually exists
    if not file_path.is_file():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # 2. Logic for CSV files (Structured data)
    if config.join_on:
        df = pd.read_csv(file_path, dtype=object, encoding='Latin-1')
        if config.join_on not in df.columns:
            raise KeyError(f"join_on column '{config.join_on}' missing in {file_path.name}")

        config.input_df = df
        return df[config.join_on].unique().tolist()

    # 3. Logic for Plain Text files (Simple list)
    with file_path.open(encoding='utf-8') as f:
        if str(config.input_file).endswith('.csv'):
            f.readline() # eat the header on non-joined csv file
        return list({line.strip() for line in f if line.strip()})


def get_json_val(parser, section, option, fallback=None):
    """Helper to handle the 'get-and-parse' pattern for JSON strings in INI files."""
    val = parser.get(section, option, fallback=None)
    if val is None:
        return fallback
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        # Professional fallback: Return the raw string if it's not valid JSON
        return val

def load_query_config(parser: configparser.ConfigParser, section: str) -> QueryConfig:
    """
    Factory function that maps an INI section to a QueryConfig object.
    """
    raw_dir = get_json_val(parser, section, 'directory')
    directory = Path(raw_dir) if raw_dir else str(Path.cwd())

    # 2. Extract criteria using a list comprehension (Standard Pythonic filtering)
    # This filters all options starting with 'criteria' into a single dictionary
    criteria_list = [
        get_json_val(parser, section, opt)
        for opt in parser.options(section) if opt.startswith('criteria')
    ]
    criteria = {"_and": criteria_list}

    fields = get_json_val(parser, section, 'fields')
    sort_fields, sort_directions = get_sort_config(parser, section, fields)

    # 3. Construct the dataclass
    return QueryConfig(
        name=section,
        entity=get_json_val(parser, section, 'entity'),
        input_file=Path(get_json_val(parser, section, 'input_file')),
        input_type=get_json_val(parser, section, 'input_type'),
        fields=fields,
        directory=directory,
        join_on=get_json_val(parser, section, 'join_output_on'),
        criteria=criteria,
        user_sort_fields=sort_fields,
        user_sort_directions=sort_directions
    )


def save_json(data: dict, directory: str, query_name: str, index: int):
    """
    Saves the JSON response to a file using the query name and results index.
    """
    # 1. Construct the filename using f-strings and Pathlib
    # Result: "directory/queryname_0.json"
    file_path = f"{directory}/{query_name}_{index}.json"

    # 2. Use a Context Manager to safely write the file
    # This ensures the file handle is closed even if an error occurs
    with open(file_path, 'w', encoding='utf-8') as f:
        # Use indent=None (default) for compact files, or 4 for readability
        json.dump(data, f, ensure_ascii=False)


if __name__ == '__main__':
    if sys.version_info[0] != 3:
        print("Please use Python version 3; you are using version:", sys.version)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("USAGE: python api_wrapper.py config_file")
        sys.exit(1)

    if not os.path.isfile(sys.argv[1]):
        print("File not found: ", sys.argv[1])

    api_key = os.getenv('PATENTSVIEW_API_KEY')
    
    if api_key is None:
        print("""
Please set environmental variable PATENTSVIEW_API_KEY to your api key obtained from
https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18
""")
        sys.exit(1)

    run_queries(sys.argv[1], api_key)

