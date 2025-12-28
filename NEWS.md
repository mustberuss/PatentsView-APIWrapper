# PatentsView-APIWrapper 1.0.0

### Breaking changes

* **API key required**: The new version of the API requires authentication. Request a key at <https://patentsview-support.atlassian.net/servicedesk/customer/portals> and set `PATENTSVIEW_API_KEY` environment variable.

* **Entity name changes**: Now 27 endpoints (up from 7). Endpoints are singular (e.g., `patent` not `patents`). The `nber_subcategory` endpoint was removed; `cpc_subsection` is now `cpc_group`.

* **Field changes**: `patent_number` is now `patent_id`. Raw inventor name fields (`rawinventor_first_name`, `rawinventor_last_name`) were removed. Some fields are now nested and require full qualification in queries (e.g., `cpc_current.cpc_group_id`).
See the API team's [Swagger UI page](https://search.patentsview.org/swagger-ui/) and [Endpoint Dictionary](https://search.patentsview.org/docs/docs/Search%20API/EndpointDictionary)
