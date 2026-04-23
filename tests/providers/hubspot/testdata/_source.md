# HubSpot testdata

- **CRM overview:** https://developers.hubspot.com/docs/api/crm/understanding-the-crm
- **Search API:** https://developers.hubspot.com/docs/api/crm/search
- **Contacts API:** https://developers.hubspot.com/docs/api/crm/contacts
- **Companies API:** https://developers.hubspot.com/docs/api/crm/companies
- **Deals API:** https://developers.hubspot.com/docs/api/crm/deals
- **Notes API:** https://developers.hubspot.com/docs/api/crm/notes
- **Tasks API:** https://developers.hubspot.com/docs/api/crm/tasks
- **Calls API:** https://developers.hubspot.com/docs/api/crm/calls
- **Emails API:** https://developers.hubspot.com/docs/api/crm/email
- **Meetings API:** https://developers.hubspot.com/docs/api/crm/meetings
- **Pipelines API:** https://developers.hubspot.com/docs/api/crm/pipelines
- **Owners API:** https://developers.hubspot.com/docs/api/crm/owners
- **Auth:** Bearer token (OAuth 2.0 private-app access token)
- **Base URL:** `https://api.hubapi.com`

Testdata JSON bodies mirror the response shapes documented by HubSpot for the
CRM v3 endpoints listed above (object records with `id`, `properties`,
`createdAt`, `updatedAt`, `archived`; pipelines with `id`, `label`, `stages`;
owners with `id`, `email`, `firstName`, `lastName`, `userId`, `teams`).
