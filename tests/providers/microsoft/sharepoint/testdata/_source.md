# Microsoft SharePoint testdata

- **Graph API docs:** https://learn.microsoft.com/en-us/graph/api/resources/sharepoint
- **Endpoint references:**
  - List sites: https://learn.microsoft.com/en-us/graph/api/site-list
  - List drives: https://learn.microsoft.com/en-us/graph/api/drive-list
  - Drive children: https://learn.microsoft.com/en-us/graph/api/driveitem-list-children
  - Create folder: https://learn.microsoft.com/en-us/graph/api/driveitem-post-children
  - Search: https://learn.microsoft.com/en-us/graph/api/driveitem-search
  - Update item: https://learn.microsoft.com/en-us/graph/api/driveitem-update
- **Auth:** OAuth 2.0 Bearer token (Microsoft Graph)
- **list_sites.json:** Based on GET /sites response.
- **list_drives.json:** Based on GET /sites/{siteId}/drives response.
- **drive_children.json:** Based on GET /drives/{driveId}/root/children response.
- **create_folder.json:** Based on POST /drives/{driveId}/root/children response.
- **search_results.json:** Based on GET /drives/{driveId}/root/search(q='{query}') response.
- **get_item.json:** Based on GET /drives/{driveId}/items/{itemId} response.
- **move_file.json:** Based on PATCH /drives/{driveId}/items/{itemId} response.
