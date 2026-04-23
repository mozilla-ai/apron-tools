# Microsoft OneDrive testdata

- **Graph API docs:** https://learn.microsoft.com/en-us/graph/api/resources/onedrive
- **Endpoint references:**
  - List children: https://learn.microsoft.com/en-us/graph/api/driveitem-list-children
  - Search: https://learn.microsoft.com/en-us/graph/api/driveitem-search
  - Get item: https://learn.microsoft.com/en-us/graph/api/driveitem-get
  - Create folder: https://learn.microsoft.com/en-us/graph/api/driveitem-post-children
  - Update item (move): https://learn.microsoft.com/en-us/graph/api/driveitem-update
- **Auth:** OAuth 2.0 Bearer token (Microsoft Graph)
- **list_files.json:** Based on GET /me/drive/root/children response.
- **search_results.json:** Based on GET /me/drive/root/search(q='...') response.
- **get_file_info.json:** Based on GET /me/drive/items/{id} response.
- **create_folder.json:** Based on POST /me/drive/root/children response.
- **get_item_name.json:** Minimal GET /me/drive/items/{id}?$select=id,name response (preflight for move).
- **move_item.json:** Based on PATCH /me/drive/items/{id} response.
