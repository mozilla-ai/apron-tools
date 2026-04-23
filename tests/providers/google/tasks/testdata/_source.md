# Google Tasks testdata

- **Tasks API docs:** https://developers.google.com/tasks/reference/rest
- **Endpoint references:**
  - List tasklists: https://developers.google.com/tasks/reference/rest/v1/tasklists/list
  - List tasks: https://developers.google.com/tasks/reference/rest/v1/tasks/list
  - Get task: https://developers.google.com/tasks/reference/rest/v1/tasks/get
  - Insert task: https://developers.google.com/tasks/reference/rest/v1/tasks/insert
  - Update task: https://developers.google.com/tasks/reference/rest/v1/tasks/update
  - Patch task: https://developers.google.com/tasks/reference/rest/v1/tasks/patch
- **Auth:** OAuth 2.0 Bearer token
- **list_tasklists.json:** Based on Tasklists.list response (``tasks#taskLists``).
- **list_tasks.json:** Based on Tasks.list response (``tasks#tasks``).
- **get_task.json:** Based on Tasks.get response (single ``tasks#task`` resource).
- **create_task.json:** Based on Tasks.insert response (single ``tasks#task`` resource).
- **update_task.json:** Based on Tasks.update response (single ``tasks#task`` resource).
- **complete_task.json:** Based on Tasks.patch response (single ``tasks#task`` resource with ``status=completed``).
