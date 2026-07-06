# Google Drive testdata

- **Drive API docs:** https://developers.google.com/drive/api/reference/rest/v3
- **Endpoint references:**
  - List files: https://developers.google.com/drive/api/reference/rest/v3/files/list
  - Get file: https://developers.google.com/drive/api/reference/rest/v3/files/get
  - Create file: https://developers.google.com/drive/api/reference/rest/v3/files/create
  - Update file: https://developers.google.com/drive/api/reference/rest/v3/files/update
  - Create permission: https://developers.google.com/drive/api/reference/rest/v3/permissions/create
- **Auth:** OAuth 2.0 Bearer token
- **list_files.json:** Based on Drive files.list response.
- **create_folder.json:** Based on Drive files.create response for a folder.
- **get_file_info.json:** Based on Drive files.get response with detailed fields.
- **move_file_meta.json:** Drive files.get response for current parents.
- **move_file.json:** Drive files.update response after moving.
- **search.json:** Based on Drive files.list response with name search query.
- **share_file.json:** Based on Drive permissions.create response (type=user).
- **share_file_group.json:** Drive permissions.create response for a group grant (type=group).
- **share_file_domain.json:** Drive permissions.create response for a domain grant (type=domain).
- **share_file_anyone.json:** Drive permissions.create response for anyone-with-link (type=anyone).
