# Linear testdata

- **API docs:** https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- **Auth:** API key passed directly as `Authorization` header (not Bearer)
- **Protocol:** All requests are POST to `https://api.linear.app/graphql` with `{"query": "...", "variables": {...}}`
- **whoami.json:** Based on `viewer` query response schema.
- **list_teams.json:** Based on `teams` query response schema.
- **list_users.json:** Based on `users` query response schema.
- **list_issues.json:** Based on `issues` query response schema.
- **read_issue.json:** Based on `issue(id: ...)` query response schema.
- **create_issue.json:** Based on `issueCreate` mutation response schema.
- **update_issue.json:** Based on `issueUpdate` mutation response schema.
- **list_projects.json:** Based on `projects` query response schema.
- **create_project.json:** Based on `projectCreate` mutation response schema.
- **update_project.json:** Based on `projectUpdate` mutation response schema.
- **list_cycles.json:** Based on `cycles` query response schema.
- **error.json:** Standard GraphQL error response.
