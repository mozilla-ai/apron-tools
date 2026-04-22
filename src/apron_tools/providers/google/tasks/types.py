"""Pydantic models for Google Tasks API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Shared resource models
# ---------------------------------------------------------------------------


class TaskList(BaseModel):
    """A Google Tasks task list resource."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    title: str = ""
    updated: str | None = None
    self_link: str | None = Field(default=None, alias="selfLink")


class Task(BaseModel):
    """A Google Tasks task resource."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    title: str = ""
    status: str | None = None
    notes: str | None = None
    due: str | None = None
    completed: str | None = None
    updated: str | None = None
    parent: str | None = None
    position: str | None = None
    self_link: str | None = Field(default=None, alias="selfLink")


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListTasklistsParams(BaseModel):
    """Parameters for listing task lists."""

    max_results: int = 100


class ListTasksParams(BaseModel):
    """Parameters for listing tasks in a task list.

    ``max_results`` is clamped to ``[1, 100]`` at the tool boundary because
    the Tasks API rejects values outside that range with HTTP 400.
    """

    tasklist_id: str = "@default"
    max_results: int = 20
    show_completed: bool = False
    due_min: str | None = None
    due_max: str | None = None
    page_token: str | None = None


class GetTaskParams(BaseModel):
    """Parameters for retrieving a single task."""

    tasklist_id: str = "@default"
    task_id: str


class CreateTaskParams(BaseModel):
    """Parameters for creating a new task.

    Google Tasks only persists the date portion of ``due``; pass a full
    RFC 3339 timestamp (e.g. ``2024-01-16T00:00:00Z``). When
    ``parent_task_id`` is set, the task is created as a subtask and the
    value is sent as a ``parent`` query parameter.
    """

    tasklist_id: str = "@default"
    title: str
    notes: str | None = None
    due: str | None = None
    parent_task_id: str | None = None


class UpdateTaskParams(BaseModel):
    """Parameters for updating an existing task.

    Only the fields the caller sets are overridden; the remaining fields
    are preserved from the current server-side representation. To mark
    a task complete, prefer ``google_tasks_complete_task``.
    """

    tasklist_id: str = "@default"
    task_id: str
    title: str | None = None
    notes: str | None = None
    due: str | None = None
    status: str | None = None


class CompleteTaskParams(BaseModel):
    """Parameters for marking a task as completed."""

    tasklist_id: str = "@default"
    task_id: str


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListTasklistsResult(ToolResult):
    """Result of listing task lists."""

    model_config = ConfigDict(extra="ignore")

    tasklists: list[TaskList] = []
    next_page_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the task lists."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.tasklists:
            return "No task lists found."
        lines = [f"Found {len(self.tasklists)} task list(s):"]
        for tl in self.tasklists:
            lines.append(f"  - {tl.title} (id={tl.id})")
        return "\n".join(lines)


class ListTasksResult(ToolResult):
    """Result of listing tasks in a task list."""

    model_config = ConfigDict(extra="ignore")

    tasks: list[Task] = []
    next_page_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the tasks."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.tasks:
            return "No tasks found."
        lines = [f"Found {len(self.tasks)} task(s):"]
        for t in self.tasks:
            marker = " [completed]" if t.status == "completed" else ""
            lines.append(f"  - {t.title}{marker} (id={t.id})")
        return "\n".join(lines)


class GetTaskResult(ToolResult):
    """Result of retrieving a single task."""

    model_config = ConfigDict(extra="ignore")

    task: Task | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the task."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.task:
            return "No task found."
        t = self.task
        status = f" [{t.status}]" if t.status else ""
        due = f"\nDue: {t.due}" if t.due else ""
        notes = f"\nNotes: {t.notes}" if t.notes else ""
        return f"Task: {t.title}{status} (id={t.id}){due}{notes}"


class CreateTaskResult(ToolResult):
    """Result of creating a new task."""

    model_config = ConfigDict(extra="ignore")

    task: Task | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created task."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.task:
            return "Task created but no details returned."
        return f"Task '{self.task.title}' created (id={self.task.id})."


class UpdateTaskResult(ToolResult):
    """Result of updating an existing task."""

    model_config = ConfigDict(extra="ignore")

    task: Task | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated task."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.task:
            return "Task updated but no details returned."
        return f"Task '{self.task.title}' updated (id={self.task.id})."


class CompleteTaskResult(ToolResult):
    """Result of marking a task as completed."""

    model_config = ConfigDict(extra="ignore")

    task: Task | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the completed task."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.task:
            return "Task completed but no details returned."
        return f"Task '{self.task.title}' marked as completed (id={self.task.id})."
