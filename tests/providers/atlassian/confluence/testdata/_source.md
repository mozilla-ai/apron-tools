# Atlassian Confluence testdata

- **API docs (v2):** https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- **API docs (v1):** https://developer.atlassian.com/cloud/confluence/rest/v1/intro/
- **Endpoint references:**
  - Explore spaces: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-space/#api-wiki-api-v2-spaces-get
  - Get page: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-wiki-api-v2-pages-id-get
  - Create page: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-wiki-api-v2-pages-post
  - Update page: same as get page (PUT on same path)
  - Child pages: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-children/#api-pages-id-direct-children-get
  - Search: https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-search/#api-wiki-rest-api-search-get
- **Auth:** OAuth 2.0 Bearer token
- **Cloud ID:** Resolved via https://api.atlassian.com/oauth/token/accessible-resources
- **accessible_resources.json:** Based on example from Atlassian OAuth docs.
- **explore_spaces.json:** Based on example response from spaces endpoint docs.
- **get_page.json:** Based on example response from get page endpoint docs.
- **create_page.json:** Based on example response from create page endpoint docs.
- **update_page.json:** Based on example response from update page endpoint docs (PUT).
- **search_content.json:** Based on example response from CQL search endpoint docs.
- **get_child_pages.json:** Based on example response from direct-children endpoint docs.
