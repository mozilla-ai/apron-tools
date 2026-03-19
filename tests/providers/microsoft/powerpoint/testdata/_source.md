# Microsoft PowerPoint testdata

- **Graph API docs:** https://learn.microsoft.com/en-us/graph/api/resources/onedrive
- **Endpoint references:**
  - Search files: https://learn.microsoft.com/en-us/graph/api/driveitem-search
  - Download file: https://learn.microsoft.com/en-us/graph/api/driveitem-get-content
  - Upload file: https://learn.microsoft.com/en-us/graph/api/driveitem-put-content
  - Get metadata: https://learn.microsoft.com/en-us/graph/api/driveitem-get
  - List children: https://learn.microsoft.com/en-us/graph/api/driveitem-list-children
- **Auth:** OAuth 2.0 Bearer token (Microsoft Graph)
- **search_files.json:** Based on GET /me/drive/root/search(q='pptx') response.
- **folder_children.json:** Based on GET /me/drive/items/{id}/children response.
- **file_metadata.json:** Based on GET /me/drive/items/{id} response.
- **upload_response.json:** Based on PUT /me/drive/root:/{path}:/content response.
