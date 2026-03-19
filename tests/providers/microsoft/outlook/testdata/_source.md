# Microsoft Outlook testdata

- **Graph API docs:** https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview
- **Endpoint references:**
  - List messages: https://learn.microsoft.com/en-us/graph/api/user-list-messages
  - Get message: https://learn.microsoft.com/en-us/graph/api/message-get
  - Send mail: https://learn.microsoft.com/en-us/graph/api/user-sendmail
  - Create draft: https://learn.microsoft.com/en-us/graph/api/user-post-messages
  - Send draft: https://learn.microsoft.com/en-us/graph/api/message-send
- **Auth:** OAuth 2.0 Bearer token (Microsoft Graph)
- **list_messages.json:** Based on GET /me/messages response.
- **get_message.json:** Based on GET /me/messages/{messageId} response (includes body).
- **create_draft.json:** Based on POST /me/messages response.
