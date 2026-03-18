# Google Docs testdata

- **Docs API docs:** https://developers.google.com/workspace/docs/api/reference/rest
- **Drive API docs:** https://developers.google.com/drive/api/reference/rest/v3
- **Endpoint references:**
  - List documents (Drive): https://developers.google.com/drive/api/reference/rest/v3/files/list
  - Create document: https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/create
  - Get document: https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get
  - BatchUpdate: https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate
  - Copy (Drive): https://developers.google.com/drive/api/reference/rest/v3/files/copy
- **Auth:** OAuth 2.0 Bearer token
- **list_documents.json:** Based on Drive files.list response with document mimeType filter.
- **create_document.json:** Based on Docs documents.create response.
- **read_document.json:** Based on Docs documents.get response with full body content.
- **update_document.json:** Based on Docs documents.batchUpdate response.
- **copy_document.json:** Drive files.copy response.
- **copy_document_meta.json:** Drive file metadata response for the original document.
