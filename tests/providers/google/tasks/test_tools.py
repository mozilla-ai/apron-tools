"""Tests for Google Tasks tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.google.tasks.tools import (
    google_tasks_complete_task,
    google_tasks_create_task,
    google_tasks_get_task,
    google_tasks_list_tasklists,
    google_tasks_list_tasks,
    google_tasks_update_task,
)
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
    UpdateTaskParams,
    UpdateTaskResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test-oauth-token"
_TASKS_BASE = "https://tasks.googleapis.com/tasks/v1"
_LIST_ID = "MDAwMDAwMDAwMA"
_TASK_ID = "task-001"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_tasklists
# ---------------------------------------------------------------------------


class TestListTasklists:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/users/@me/lists?maxResults=100",
            json=_load_json("list_tasklists.json"),
        )

        result = await google_tasks_list_tasklists(ListTasklistsParams(), token=_TOKEN)

        assert isinstance(result, ListTasklistsResult)
        assert result.success is True
        assert len(result.tasklists) == 2
        assert result.tasklists[0].title == "My Tasks"
        assert result.tasklists[1].title == "Work"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_tasks_list_tasklists(ListTasklistsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_list_tasklists._tool_definition
        assert defn.name == "google_tasks_list_tasklists"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        result = await google_tasks_list_tasks(ListTasksParams(tasklist_id=_LIST_ID), token=_TOKEN)

        assert isinstance(result, ListTasksResult)
        assert result.success is True
        assert len(result.tasks) == 3
        assert result.tasks[0].title == "Buy groceries"
        assert result.tasks[2].status == "completed"

    async def test_hides_completed_by_default(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        await google_tasks_list_tasks(ListTasksParams(), token=_TOKEN)

        request = httpx_mock.get_request()
        assert "showCompleted=false" in str(request.url)

    async def test_show_completed_opt_in(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        await google_tasks_list_tasks(ListTasksParams(show_completed=True), token=_TOKEN)

        request = httpx_mock.get_request()
        assert "showCompleted=true" in str(request.url)

    async def test_clamps_max_results_upper(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        await google_tasks_list_tasks(ListTasksParams(max_results=500), token=_TOKEN)

        request = httpx_mock.get_request()
        assert "maxResults=100" in str(request.url)

    async def test_clamps_max_results_lower(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        await google_tasks_list_tasks(ListTasksParams(max_results=-10), token=_TOKEN)

        request = httpx_mock.get_request()
        assert "maxResults=1" in str(request.url)

    async def test_passes_due_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_tasks.json"))

        await google_tasks_list_tasks(
            ListTasksParams(
                tasklist_id="list1",
                due_min="2024-01-01T00:00:00Z",
                due_max="2024-01-31T23:59:59Z",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        url = str(request.url)
        assert "/lists/list1/tasks" in url
        assert "dueMin=2024-01-01" in url
        assert "dueMax=2024-01-31" in url

    async def test_returns_next_page_token(self, httpx_mock: HTTPXMock) -> None:
        payload = _load_json("list_tasks.json")
        payload["nextPageToken"] = "page-2"
        httpx_mock.add_response(json=payload)

        result = await google_tasks_list_tasks(ListTasksParams(), token=_TOKEN)

        assert result.next_page_token == "page-2"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_tasks_list_tasks(ListTasksParams(tasklist_id="missing"), token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_list_tasks._tool_definition
        assert defn.name == "google_tasks_list_tasks"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------


class TestGetTask:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            json=_load_json("get_task.json"),
        )

        result = await google_tasks_get_task(
            GetTaskParams(tasklist_id=_LIST_ID, task_id=_TASK_ID),
            token=_TOKEN,
        )

        assert isinstance(result, GetTaskResult)
        assert result.success is True
        assert result.task is not None
        assert result.task.id == _TASK_ID
        assert result.task.title == "Buy groceries"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_tasks_get_task(
            GetTaskParams(tasklist_id=_LIST_ID, task_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_get_task._tool_definition
        assert defn.name == "google_tasks_get_task"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


class TestCreateTask:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks",
            json=_load_json("create_task.json"),
        )

        result = await google_tasks_create_task(
            CreateTaskParams(
                tasklist_id=_LIST_ID,
                title="Follow up",
                notes="ping next week",
                due="2024-03-01T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateTaskResult)
        assert result.success is True
        assert result.task is not None
        assert result.task.id == "task-042"

    async def test_sends_correct_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_task.json"))

        await google_tasks_create_task(
            CreateTaskParams(
                tasklist_id="list1",
                title="Follow up",
                notes="ping next week",
                due="2024-03-01T00:00:00Z",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert "/lists/list1/tasks" in str(request.url)
        body = json.loads(request.content)
        assert body == {
            "title": "Follow up",
            "notes": "ping next week",
            "due": "2024-03-01T00:00:00Z",
        }

    async def test_parent_sent_as_query_param(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_task.json"))

        await google_tasks_create_task(
            CreateTaskParams(title="Child", parent_task_id="parent-001"),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert "parent=parent-001" in str(request.url)
        # parent must be on the URL, not in the JSON body.
        body = json.loads(request.content)
        assert "parent" not in body

    async def test_minimal_task(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_task.json"))

        await google_tasks_create_task(
            CreateTaskParams(title="Quick task"),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body == {"title": "Quick task"}

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_tasks_create_task(
            CreateTaskParams(title="Bad"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_create_task._tool_definition
        assert defn.name == "google_tasks_create_task"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks" in defn.scopes


# ---------------------------------------------------------------------------
# update_task
# ---------------------------------------------------------------------------


class TestUpdateTask:
    async def test_merges_partial_fields(self, httpx_mock: HTTPXMock) -> None:
        # GET fetches the existing resource.
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            json=_load_json("get_task.json"),
        )
        # PUT with merged body.
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            json=_load_json("update_task.json"),
        )

        result = await google_tasks_update_task(
            UpdateTaskParams(
                tasklist_id=_LIST_ID,
                task_id=_TASK_ID,
                title="Buy groceries (updated)",
                notes="pick up milk, eggs, and bread",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateTaskResult)
        assert result.success is True
        assert result.task is not None
        assert result.task.title == "Buy groceries (updated)"

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        put_body = json.loads(requests[1].content)
        # Caller-provided fields overridden.
        assert put_body["title"] == "Buy groceries (updated)"
        assert put_body["notes"] == "pick up milk, eggs, and bread"
        # Untouched fields preserved from GET.
        assert put_body["status"] == "needsAction"
        assert put_body["due"] == "2024-01-16T00:00:00.000Z"

    async def test_get_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_tasks_update_task(
            UpdateTaskParams(task_id="bad-id", title="Update"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_put_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            json=_load_json("get_task.json"),
        )
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            status_code=403,
            text="Forbidden",
        )

        result = await google_tasks_update_task(
            UpdateTaskParams(
                tasklist_id=_LIST_ID,
                task_id=_TASK_ID,
                title="Update",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_update_task._tool_definition
        assert defn.name == "google_tasks_update_task"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks" in defn.scopes


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------


class TestCompleteTask:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_TASKS_BASE}/lists/{_LIST_ID}/tasks/{_TASK_ID}",
            method="PATCH",
            json=_load_json("complete_task.json"),
        )

        result = await google_tasks_complete_task(
            CompleteTaskParams(tasklist_id=_LIST_ID, task_id=_TASK_ID),
            token=_TOKEN,
        )

        assert isinstance(result, CompleteTaskResult)
        assert result.success is True
        assert result.task is not None
        assert result.task.status == "completed"

    async def test_sends_status_patch(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="PATCH",
            json=_load_json("complete_task.json"),
        )

        await google_tasks_complete_task(
            CompleteTaskParams(tasklist_id=_LIST_ID, task_id=_TASK_ID),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request.method == "PATCH"
        body = json.loads(request.content)
        assert body == {"status": "completed"}

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, method="PATCH", text="Not Found")

        result = await google_tasks_complete_task(
            CompleteTaskParams(task_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_tasks_complete_task._tool_definition
        assert defn.name == "google_tasks_complete_task"
        assert defn.provider == "google"
        assert defn.service == "google_tasks"
        assert "https://www.googleapis.com/auth/tasks" in defn.scopes
