"""Google Tasks tool functions for interacting with the Tasks REST API."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from apron_tools.providers.google.tasks.types import (
    CompleteTaskParams,
    CompleteTaskResult,
    CreateTaskParams,
    CreateTaskResult,
    GetTaskParams,
    GetTaskResult,
    ListTasklistsParams,
    ListTasklistsResult,
    ListTasksParams,
    ListTasksResult,
    Task,
    TaskList,
    UpdateTaskParams,
    UpdateTaskResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_TASKS_BASE_URL = "https://tasks.googleapis.com/tasks/v1"
_TIMEOUT = 60.0

# Google's tasks.list endpoint rejects maxResults outside [1, 100] with a
# 400 response. Clamping at the tool boundary keeps bad LLM inputs out of
# the agent loop where they would just retry with the same bad value.
_MAX_RESULTS_FLOOR = 1
_MAX_RESULTS_CEILING = 100


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Google API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _clamp_max_results(value: int) -> int:
    """Clamp ``max_results`` to the Tasks API's accepted [1, 100] range."""
    return max(_MAX_RESULTS_FLOOR, min(value, _MAX_RESULTS_CEILING))


@tool(
    scopes=SCOPES["google_tasks_list_tasklists"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasklists/list",
    provider="google",
    service="google_tasks",
)
async def google_tasks_list_tasklists(
    params: ListTasklistsParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> ListTasklistsResult:
    """List all task lists accessible by the user."""
    query_params: dict[str, str | int] = {
        "maxResults": _clamp_max_results(params.max_results),
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/users/@me/lists",
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListTasklistsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListTasklistsResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    tasklists = [TaskList.model_validate(item) for item in data.get("items", [])]
    return ListTasklistsResult(
        success=True,
        tasklists=tasklists,
        next_page_token=data.get("nextPageToken"),
    )


@tool(
    scopes=SCOPES["google_tasks_list_tasks"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasks/list",
    provider="google",
    service="google_tasks",
)
async def google_tasks_list_tasks(
    params: ListTasksParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> ListTasksResult:
    """List tasks in a task list."""
    encoded_list = quote(params.tasklist_id, safe="")
    query_params: dict[str, str | int | bool] = {
        "maxResults": _clamp_max_results(params.max_results),
        # Strings "true"/"false" because the Tasks API expects query-string
        # booleans rather than python's capitalised "True"/"False".
        "showCompleted": "true" if params.show_completed else "false",
        "showHidden": "false",
        "showDeleted": "false",
    }
    if params.due_min:
        query_params["dueMin"] = params.due_min
    if params.due_max:
        query_params["dueMax"] = params.due_max
    if params.page_token:
        query_params["pageToken"] = params.page_token

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/lists/{encoded_list}/tasks",
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListTasksResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListTasksResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    tasks = [Task.model_validate(item) for item in data.get("items", [])]
    return ListTasksResult(
        success=True,
        tasks=tasks,
        next_page_token=data.get("nextPageToken"),
    )


@tool(
    scopes=SCOPES["google_tasks_get_task"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasks/get",
    provider="google",
    service="google_tasks",
)
async def google_tasks_get_task(
    params: GetTaskParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> GetTaskResult:
    """Retrieve a single task by ID."""
    encoded_list = quote(params.tasklist_id, safe="")
    encoded_task = quote(params.task_id, safe="")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/lists/{encoded_list}/tasks/{encoded_task}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetTaskResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetTaskResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    task = Task.model_validate(resp.json())
    return GetTaskResult(success=True, task=task)


@tool(
    scopes=SCOPES["google_tasks_create_task"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasks/insert",
    provider="google",
    service="google_tasks",
)
async def google_tasks_create_task(
    params: CreateTaskParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> CreateTaskResult:
    """Create a new task in a task list."""
    encoded_list = quote(params.tasklist_id, safe="")

    body: dict[str, str] = {"title": params.title}
    if params.notes is not None:
        body["notes"] = params.notes
    if params.due is not None:
        body["due"] = params.due

    # The Tasks API accepts ``parent`` as a query parameter on insert to
    # create the task as a subtask of an existing task on the same list.
    query_params: dict[str, str] = {}
    if params.parent_task_id is not None:
        query_params["parent"] = params.parent_task_id

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/lists/{encoded_list}/tasks",
                headers=_headers(token, content_type=True),
                params=query_params,
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateTaskResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateTaskResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    task = Task.model_validate(resp.json())
    return CreateTaskResult(success=True, task=task)


@tool(
    scopes=SCOPES["google_tasks_update_task"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasks/update",
    provider="google",
    service="google_tasks",
)
async def google_tasks_update_task(
    params: UpdateTaskParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> UpdateTaskResult:
    """Update an existing task, merging provided fields into the current resource."""
    encoded_list = quote(params.tasklist_id, safe="")
    encoded_task = quote(params.task_id, safe="")

    # Fetch the existing task first so unset caller fields are preserved;
    # Tasks' PUT endpoint replaces the full resource representation.
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            get_resp = await client.get(
                f"{base_url}/lists/{encoded_list}/tasks/{encoded_task}",
                headers=_headers(token),
            )
            if not get_resp.is_success:
                return UpdateTaskResult(
                    success=False,
                    error=f"Tasks API error {get_resp.status_code}: {get_resp.text}",
                )

            body = get_resp.json()

            if params.title is not None:
                body["title"] = params.title
            if params.notes is not None:
                body["notes"] = params.notes
            if params.due is not None:
                body["due"] = params.due
            if params.status is not None:
                body["status"] = params.status

            resp = await client.put(
                f"{base_url}/lists/{encoded_list}/tasks/{encoded_task}",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return UpdateTaskResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateTaskResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    task = Task.model_validate(resp.json())
    return UpdateTaskResult(success=True, task=task)


@tool(
    scopes=SCOPES["google_tasks_complete_task"],
    api_docs="https://developers.google.com/tasks/reference/rest/v1/tasks/patch",
    provider="google",
    service="google_tasks",
)
async def google_tasks_complete_task(
    params: CompleteTaskParams,
    *,
    token: str,
    base_url: str = _TASKS_BASE_URL,
) -> CompleteTaskResult:
    """Mark a task as completed."""
    encoded_list = quote(params.tasklist_id, safe="")
    encoded_task = quote(params.task_id, safe="")

    # PATCH with just ``status=completed`` lets the server stamp the
    # ``completed`` timestamp; a manual PUT would require the caller to
    # compute and pass the timestamp themselves.
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.patch(
                f"{base_url}/lists/{encoded_list}/tasks/{encoded_task}",
                headers=_headers(token, content_type=True),
                json={"status": "completed"},
            )
    except httpx.HTTPError as exc:
        return CompleteTaskResult(success=False, error=str(exc))

    if not resp.is_success:
        return CompleteTaskResult(
            success=False,
            error=f"Tasks API error {resp.status_code}: {resp.text}",
        )

    task = Task.model_validate(resp.json())
    return CompleteTaskResult(success=True, task=task)
