# Salesforce testdata

- **REST API docs:** https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
- **Endpoint references:**
  - Describe Global: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_describeGlobal.htm
  - Query: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm
  - Get Record: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_get_field_values.htm
  - Create Record: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm
  - Update Record: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_retrieve.htm
  - Search: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_search.htm
- **Auth:** Bearer token (OAuth 2.0)
- **Instance URL resolution:** GET https://login.salesforce.com/services/oauth2/userinfo
- **userinfo.json:** Based on Salesforce OAuth userinfo response schema.
- **explore_org.json:** Based on Describe Global response schema from API docs.
- **query_records.json:** Based on Query response schema from API docs.
- **get_record.json:** Based on SObject Get response from API docs.
- **create_record.json:** Based on SObject Create response from API docs.
- **search_records.json:** Based on Search response schema from API docs.
