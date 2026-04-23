# Google Slides testdata

- **Slides API docs:** https://developers.google.com/workspace/slides/api/reference/rest
- **Drive API docs:** https://developers.google.com/drive/api/reference/rest/v3
- **Endpoint references:**
  - List presentations (Drive): https://developers.google.com/drive/api/reference/rest/v3/files/list
  - Create presentation: https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/create
  - Get presentation: https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/get
  - BatchUpdate: https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate
  - Copy (Drive): https://developers.google.com/drive/api/reference/rest/v3/files/copy
- **Auth:** OAuth 2.0 Bearer token
- **list_presentations.json:** Based on Drive files.list response with presentation mimeType filter.
- **create_presentation.json:** Based on Slides presentations.create response.
- **copy_presentation_meta.json:** Drive file metadata response for the original presentation.
- **copy_presentation.json:** Drive files.copy response.
- **read_presentation.json:** Slides presentations.get response.
- **read_presentation_with_layouts.json:** Slides presentations.get response that exposes
  multiple named layouts (BLANK, TITLE_AND_BODY, SECTION_HEADER) plus a slide
  with a text-bearing shape and an empty shape. Used for layout fallback and
  update-slide-text robustness tests.
- **batch_update_add_slide.json:** Slides presentations.batchUpdate response for createSlide.
- **batch_update_duplicate.json:** Slides presentations.batchUpdate response for duplicateObject.
- **batch_update_generic.json:** Generic batchUpdate response for text/element operations.
