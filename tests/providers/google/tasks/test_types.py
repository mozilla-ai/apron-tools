"""Tests for Google Tasks provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

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

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models.
# ---------------------------------------------------------------------------


class TestListTasklistsParams:
    def test_defaults(self):
        params = ListTasklistsParams()
        assert params.max_results == 100

    def test_custom(self):
        params = ListTasklistsParams(max_results=25)
        assert params.max_results == 25


class TestListTasksParams:
    def test_defaults(self):
        params = ListTasksParams()
        assert params.tasklist_id == "@default"
        assert params.max_results == 20
        assert params.show_completed is False
        assert params.due_min is None
        assert params.due_max is None
        assert params.page_token is None

    def test_custom(self):
        params = ListTasksParams(
            tasklist_id="list-001",
            max_results=50,
            show_completed=True,
            due_min="2024-01-01T00:00:00Z",
            due_max="2024-01-31T23:59:59Z",
            page_token="abc",
        )
        assert params.tasklist_id == "list-001"
        assert params.show_completed is True
        assert params.due_min == "2024-01-01T00:00:00Z"


class TestGetTaskParams:
    def test_required(self):
        params = GetTaskParams(task_id="task-001")
        assert params.tasklist_id == "@default"
        assert params.task_id == "task-001"

    def test_custom_list(self):
        params = GetTaskParams(tasklist_id="list-001", task_id="task-001")
        assert params.tasklist_id == "list-001"


class TestCreateTaskParams:
    def test_required(self):
        params = CreateTaskParams(title="Buy groceries")
        assert params.tasklist_id == "@default"
        assert params.title == "Buy groceries"
        assert params.notes is None
        assert params.due is None
        assert params.parent_task_id is None

    def test_full(self):
        params = CreateTaskParams(
            tasklist_id="list-001",
            title="Buy groceries",
            notes="pick up milk and eggs",
            due="2024-01-16T00:00:00Z",
            parent_task_id="parent-001",
        )
        assert params.notes == "pick up milk and eggs"
        assert params.parent_task_id == "parent-001"


class TestUpdateTaskParams:
    def test_required(self):
        params = UpdateTaskParams(task_id="task-001")
        assert params.tasklist_id == "@default"
        assert params.task_id == "task-001"
        assert params.title is None
        assert params.notes is None

    def test_partial(self):
        params = UpdateTaskParams(task_id="task-001", title="New title")
        assert params.title == "New title"
        assert params.notes is None


class TestCompleteTaskParams:
    def test_required(self):
        params = CompleteTaskParams(task_id="task-001")
        assert params.tasklist_id == "@default"
        assert params.task_id == "task-001"


# ---------------------------------------------------------------------------
# TaskList resource.
# ---------------------------------------------------------------------------


class TestTaskList:
    def test_parse_from_api(self):
        data = _load_json("list_tasklists.json")
        tasklist = TaskList.model_validate(data["items"][0])

        assert tasklist.id == "MDAwMDAwMDAwMA"
        assert tasklist.title == "My Tasks"
        assert tasklist.updated == "2024-01-15T12:00:00.000Z"
        assert tasklist.self_link is not None


# ---------------------------------------------------------------------------
# Task resource.
# ---------------------------------------------------------------------------


class TestTask:
    def test_parse_full_task(self):
        data = _load_json("get_task.json")
        task = Task.model_validate(data)

        assert task.id == "task-001"
        assert task.title == "Buy groceries"
        assert task.status == "needsAction"
        assert task.notes == "pick up milk and eggs"
        assert task.due == "2024-01-16T00:00:00.000Z"

    def test_parse_completed_task(self):
        data = _load_json("list_tasks.json")
        task = Task.model_validate(data["items"][2])

        assert task.id == "task-003"
        assert task.status == "completed"
        assert task.completed == "2024-01-12T10:00:00.000Z"

    def test_parse_minimal_task(self):
        data = _load_json("list_tasks.json")
        task = Task.model_validate(data["items"][1])

        assert task.id == "task-002"
        assert task.title == "Email design review"
        assert task.notes is None
        assert task.due is None


# ---------------------------------------------------------------------------
# ListTasklistsResult.
# ---------------------------------------------------------------------------


class TestListTasklistsResult:
    def test_str_output(self):
        data = _load_json("list_tasklists.json")
        tasklists = [TaskList.model_validate(t) for t in data["items"]]
        result = ListTasklistsResult(success=True, tasklists=tasklists)
        text = str(result)

        assert "2 task list(s)" in text
        assert "My Tasks" in text
        assert "Work" in text

    def test_str_on_error(self):
        result = ListTasklistsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListTasklistsResult(success=True, tasklists=[])
        assert str(result) == "No task lists found."


# ---------------------------------------------------------------------------
# ListTasksResult.
# ---------------------------------------------------------------------------


class TestListTasksResult:
    def test_str_output(self):
        data = _load_json("list_tasks.json")
        tasks = [Task.model_validate(t) for t in data["items"]]
        result = ListTasksResult(success=True, tasks=tasks)
        text = str(result)

        assert "3 task(s)" in text
        assert "Buy groceries" in text
        assert "Ship it [completed]" in text

    def test_str_on_error(self):
        result = ListTasksResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"

    def test_str_empty(self):
        result = ListTasksResult(success=True, tasks=[])
        assert str(result) == "No tasks found."


# ---------------------------------------------------------------------------
# GetTaskResult.
# ---------------------------------------------------------------------------


class TestGetTaskResult:
    def test_str_output(self):
        data = _load_json("get_task.json")
        task = Task.model_validate(data)
        result = GetTaskResult(success=True, task=task)
        text = str(result)

        assert "Buy groceries" in text
        assert "needsAction" in text
        assert "pick up milk and eggs" in text

    def test_str_on_error(self):
        result = GetTaskResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"

    def test_str_no_task(self):
        result = GetTaskResult(success=True, task=None)
        assert str(result) == "No task found."


# ---------------------------------------------------------------------------
# CreateTaskResult.
# ---------------------------------------------------------------------------


class TestCreateTaskResult:
    def test_str_output(self):
        data = _load_json("create_task.json")
        task = Task.model_validate(data)
        result = CreateTaskResult(success=True, task=task)
        text = str(result)

        assert "Follow up" in text
        assert "created" in text
        assert "task-042" in text

    def test_str_on_error(self):
        result = CreateTaskResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# UpdateTaskResult.
# ---------------------------------------------------------------------------


class TestUpdateTaskResult:
    def test_str_output(self):
        data = _load_json("update_task.json")
        task = Task.model_validate(data)
        result = UpdateTaskResult(success=True, task=task)
        text = str(result)

        assert "Buy groceries (updated)" in text
        assert "updated" in text

    def test_str_on_error(self):
        result = UpdateTaskResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"


# ---------------------------------------------------------------------------
# CompleteTaskResult.
# ---------------------------------------------------------------------------


class TestCompleteTaskResult:
    def test_str_output(self):
        data = _load_json("complete_task.json")
        task = Task.model_validate(data)
        result = CompleteTaskResult(success=True, task=task)
        text = str(result)

        assert "Buy groceries" in text
        assert "completed" in text

    def test_str_on_error(self):
        result = CompleteTaskResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"
