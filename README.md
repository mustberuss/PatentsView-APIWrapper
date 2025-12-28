PatentsView API Wrapper
===================================

The purpose of this API Wrapper is to extend the functionality of the new version of the
[PatentsView API](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference) 
 (renamed the PatentSearch API, as
 [announced in 2024](https://search.patentsview.org/docs/#naming-update)).
The wrapper can take in a list of 
values (such as patent numbers), retrieve multiple data points, and then convert
and merge the results into a CSV file.

## Background and required acknowledgement ##
Just to clear up any potential confusion, 
this has nothing to do with a snake in a hoodie laying down rhythmic rhymes, that would be *Python The Rapper* (sorry, I couldn't resist). The real story begins,
"Once upon a time the Patentsview API team created a python wrapper for its API and the programming world was grateful".  Later, for reasons unknown,
they archived the [wrapper's repo](https://github.com/PatentsView/PatentsView-APIWrapper) rather than updating it for the new version of the API.  Here I undo that injustice and 
[acknowledge their work](https://github.com/PatentsView/PatentsView-APIWrapper#license)
to keep the Creative Commons police at bay.  Yes, the API team did a fabulous job writing it and I reworked it for the new verion of the API.  Need I say more?  (Seriously, I hope I've said enough to meet the [Creative Commons 4.0](https://creativecommons.org/licenses/by/4.0/) requirements).

And lastly, I'm doing this to fill a void.  I haven't done much python, pandas are only begrudgingly becoming friends and I desperatly long to become pythonic.  What's here is the result of AI's suggestions while mocking my code, not any degree of honestly earned pythonic-ness acquired by practicing the art. In otherwords, don't take this code as a good example of anything other than void filling.  

## How To Use the API Wrapper
1. Clone or download this repository
```bash
git clone https://github.com/mustberuss/PatentsView-APIWrapper
```

2. Install dependencies
```bash
cd PatentsView-APIWrapper
pip install -r requirements.txt
```

3. Modify the sample config file `sample_config.cfg` or create a copy with your own configuration settings

4. Request an [API key](https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18) and set its value as an evironmental variable.  In windows: 

```bash
set PATENTSVIEW_API_KEY=<the API key you received>  (no double quotes)
```
In unix:
```bash
export PATENTSVIEW_API_KEY="<the API key you received>"
```

5. Run the API Wrapper using Python 3:
```bash
python api_wrapper.py sample_config.cfg
```

## How to modify your query configuration file
The PatentsView API Wrapper reads in query specifications from the configuration file you point it to. The configuration file should define at least one query but it can contain multiple queries. Below is a description of each parameter that defines each query.

### Query Name
The name of the query, and the name given to the resulting file (for example, [QUERY1] produces QUERY1.csv). If your configuration file contains multiple queries, each query should have a distinct name. Query parameters must directly follow the query name. 

### Entity
The type of object you want to return. This must be one of the PatentsView API endpoints:
```
    "assignee"
    "cpc_class"
    "cpc_group"
    "cpc_subclass"
    "g_brf_sum_text"
    "g_claim"
    "g_detail_desc_text"
    "g_draw_desc_text"
    "inventor"
    "ipc"
    "location"
    "patent"
    "patent/attorney"
    "patent/foreign_citation"
    "patent/other_reference"
    "patent/rel_app_text"
    "patent/us_application_citation"
    "patent/us_patent_citation"
    "pg_brf_sum_text"
    "pg_claim"
    "pg_detail_desc_text"
    "pg_draw_desc_text"
    "publication"
    "publication/rel_app_text"
    "uspc_mainclass"
    "uspc_subclass"
    "wipo"
```

### Input File
The name or relative path of the input file containing the values you want to query. For example, `sample_config.cfg` points to `sample_patents.txt`, which contains a list of patent numbers; the API wrapper will query for each of these patents.

### Input Type
The type of object represented in the input file. The full list of 
input types can be found in the [PatentsView API Documentation](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference). 
Common input types include:

```
    "patent_id"  ("patent_number" in the original version)
    "inventor_id"
    "assignee_id"
    "cpc_subclass_id"
    "location_id"
    "uspc_mainclass_id"
```

### Fields
The list of fields determines what columns will be in the generated csv file. Valid fields for each endpoint can be found in the [PatentsView API Documentation](https://patentsview.org/apis/api-endpoints). Fields should be specified as an array of strings and may contain nested fields the API returns, such as:

```fields = ["patent_id", "patent_title", "patent_date", "application.filing_date"]```

There is also a new API shorthand[^1] where all the fields of a nested object can be
requested by just specifying its name as field.  As an example, for the patent endpoint, "appication" can be used as a field name rather than fully qualifying each of its fields
"application.application_id", "application.application_type",
"application.filing_date", "application.filing_type",
"application.rule_47_flag", "application.series_code"


### Directory (Optional)
The absolute path of the directory of your input file and results. Use forward slashes (`/`) instead of backward slashes (`\`). For Windows, this may look like:

```directory = "/Users/jsennett/Code/PatentsView-APIWrapper"```

For OSX/Unix systems:

```directory = "C:/Users/jsennett/Code/PatentsView-APIWrapper"```

The current directory will be used if a directory is not specified.

### Criteria (optional)
Additional rules, written in the PatentsView API syntax, to be applied to each query. Each criteria can specify multiple rules combined with OR or AND operators. If multiple criteria are listed, they will be combined with the AND operator. Multiple criteria should be named criteria1, criteria2, criteria3, etc.

For example, the following criteria will limit results to patents from Jan 1 to Dec 31, 2015 with a patent abstract containing either "cell" or "mobile".
```
criteria1 = {"_gte":{"patent_date":"2015-1-1"}}
criteria2 = {"_lte":{"patent_date":"2015-12-31"}}
criteria3 = {"_or":[{"_contains":{"patent_abstract":"cell"}, {"_contains":{"patent_abstract":"mobile"}]}
```

### Sort (optional)
The fields and directions over which the output file will be sorted. This should be specified as an array of JSON objects, pairing the field with its direction. The sort order will follow the array order.
To sort just by patent number (ascending):

```sort = [{"patent_id": "asc"}]```

To sort first by patent_date (descending), and then by patent title (ascending):

```sort = [{"patent_date": "desc"}, {"patent_title":, "asc"}]```

If a sort is not specified, one using the API's primary and secondary key (if applicable) will be applied. (Only the endpoints with a sequence field have secondary keys.)

### Chaining (Optional Concept)
This is something you can do in a configuration file, it's not a parameter setting as the other entries are.  This is here to explain chaining ahead of the next entry which is a new parameter that can be used while chaining queries. 

As mentioned above, you can put more than one query in a configuration file, they will be executed in top to bottom order.  We can take advantage of this, the output of one query can be used as input to a subsequent query. This is especially useful if the data you want now comes from two different endpoints.   

Below is an example of chaining, where the output of the first query's calls to the patent/us_patent_citations endpoint, INITIAL_QUERY.csv, becomes the input for the NESTED_QUERY's calls to the patent endpoint. 

When chaining queries, the only requirement is that the earlier query's output file can only contain a single column, there can  only be one value per row.  This mimicks other input files, like sample_patents.txt, that must only contain a single value per line. You could chain queries using the original version of the PatentsView-APIWrapper, as I [pointed out](https://patentsview.org/forum/9/topic/159#comment-190) in the Patentsview forum. 
```
# nested_query.cfg
[INITIAL_QUERY]
entity = "patent/us_patent_citation"
input_file = "sample_patents.txt"
input_type = "patent_id"
fields = ["citation_patent_id"]

[NESTED_QUERY]
entity = "patent"
input_file = "INITIAL_QUERY.csv"
input_type = "patent_id"
fields = ["patent_id","patent_title","patent_date"]
sort = [{"patent_id":"asc"}]
```

### Join_output_on (Optional)
There is a new, optional parameter ```join_output_on``` that we can specify in a chained query. 
If specified, the input file must be a csv file containing one or more columns, one of which must be the specified join_output_on column.  The values in the join_output_on column are used to make the specified chained query and the rest of the input columns are written to the output file along with the return from the chained query.

A concrete example should make this clear.  Say, like in the preceding example, we want the same data fields of patents citing the patents in sample_patents.txt but we also want the output to contain the patent_id from sample_patents.txt that the citing patent cited.  Let that sink in for a second. Without the patent_id from sample_patents.txt in the output file, we'd only know that patents in NESTED_QUERY.csv cited one or more patents in sample_patents.txt, we wouldn't know specifically which one(s).

To accomplish our goal, all we need to do is make two changes to the configuration file of the previous example. We'll also make a third, not required, change for fun. The first is to change the output of the initial query to write both the patent_id as well as the citation_patent_id to INITIAL_QUERY.csv.  The second change is to specify join_output_on = "citation_patent_id".
Setting a join_ountput_on field causes the input file to be read into a data frame that is then joined with what the API returned where the API's input_type field = the input file's join_output_on field.  The third change lets us sort the chained output.

```
# joined_query.cfg
[INITIAL_QUERY_FOR_JOIN]
entity = "patent/us_patent_citation"
input_file = "sample_patents.txt"
input_type = "patent_id"
# change 1:
fields = ["citation_patent_id", "patent_id"]

[JOINED_QUERY]
entity = "patent"
input_file = "INITIAL_QUERY.csv"
input_type = "patent_id"
fields = ["patent_id","patent_title","patent_date"]
# change 2:
join_output_on = "citation_patent_id"
# change 3:
sort = [{"input_patent_id":"asc"},{"citation_patent_id":"asc"}]
```
With the join_output_on set as shown we get these columns in NESTED_QUERY.csv
```
input_patent_id, citation_patent_id, patent_title, patent_date
```
Note that "input_" was prepended to the column names of the input file to distinguish them from the columns the API returned. The input_patent_id would show the patent_id from sample_patents.txt along with the data of the patent that cited it. We can even sort on an input column as shown above.  How cool is that? 

## Notes
Listed here are things the API does, intentionally or unintentionally.  They should not be considered api-wrapper bugs.
1. The original version of the API had a handy ```mtchd_subent_only``` option that would filter the data returned in sub-entities.  This option is not available in the new verison however.  It's no longer possible to limit the cpc_current sub-entity by adding something like ```criteria1 = {"cpc_current.cpc_sequence": 0}``` The output file will still contain all available cpc_sequences.
2. Something similarly unexpected can happen with what the API team calls *related entity queries*, querying the patent endpoint for inventor's first and last name for example.  What's concidered a match could be inventor 1's first name with inventor 2's last name, which might not be what you intended (if you assumed both matches had to occur on the same inventor).  Also, because of the lack of a mtchd_subent_only option, you get all the inventors back where at least one related entity match was found, leaving you to figure out how the match occurred (single inventors or pairs of them).  There is more [online about this](https://nbviewer.org/github/mustberuss/PatentsView-Code-Snippets/blob/master/07_PatentSearch_API_demo/PV%20PatentSearch%20API%20tutorial.ipynb#Queries-using-related-entity-fields) and there is also a related-entity.cfg you could run. 
3. Also, as long as we've mentioned sequences and the API's behavior, lets point out that most of the time sequences are zero based but a handful are one based, depending on sub-entity.  For example, cpc_current's cpc_sequence is zero based while cpc_at_issue's cpc_sequence is one based.   applicant_sequence seems to be the only other one based sequence.  You could always specify a secondary sort on the sequence in question so the first one floats to the top. 
4. patent_ids are strings to accomodate non-utility patents like plants (which begin PP followed by digits). Because of this, a sort on patent_id will list utility patents 10,0000,000 and above before patents in the four or five millions etc.  The API offers a leading-zero padding option when calling the patent endpoint so a string sort behaves better.  The api-wrapper does not use this option as it's only available at the patent endpoint and would break joins with patent_ids from other endpoints. It would also require padding when querying by patent_id. Under consideration within the api-wrapper is sorting by the length of the patent_id first with a secondary alpa sort to not break joining and not require padding while querying by patent_id.
5. When there weren't any results matching your query, the API returns an HTTP code of 200 (success) with a "count" of 0.  If you get an HTTP code of 404 (page not found) from the API, your entity most likey does not match one of the API's endpoints.
   
## Compatibility

The API wrapper is currently compatible with Python 3.10.

## License

Users are free to use, share, or adapt the material for any purpose, subject to the standards of the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

Attribution should be given to [mustberuss](https://github.com/mustberuss/) for use, distribution, or derivative works.

## See also

My [jupyter notebook](https://github.com/mustberuss/PatentsView-Code-Snippets/blob/master/07_PatentSearch_API_demo/PV%20PatentSearch%20API%20tutorial.ipynb) forked from the USPTO's [PatentsView-Code-Examples](https://github.com/PatentsView/PatentsView-Code-Examples) 

The Patentsview [forum](https://patentsview.org/forum)

The API team's [Relationships Behind Inventions That Propel Innovation](https://datatool.patentsview.org/#viz/relationships)

[PatentsView API Reference](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/)

[PatentsView Query Language](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/#api-query-language)

[Swagger UI page](https://search.patentsview.org/swagger-ui/) for the new version of the API

The [R package](https://github.com/ropensci/patentsview/) for the new version of the API, especially its data-raw/fieldsdf.csv of fields per endpoint.

An [R based CPC tool](https://github.com/nateapathy/patentsview2) that uses the aforementioned R package

A different [python wrapper](https://github.com/mikeym88/PatentsView-API-Wrapper) that builds a local SQLite database (note to self: need to check that it still works)

\<link to your repo\> when you write a python library for the new version of the API

[^1]: Mentioned in the [API team's jupyter notebook](https://github.com/PatentsView/PatentsView-Code-Examples/blob/ce759fccc9f1f43e8fce333369fab7149b9480a4/PatentSearch/0-patentsearch-api-demo.ipynb#L187))