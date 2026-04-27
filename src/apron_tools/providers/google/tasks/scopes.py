"""OAuth scope definitions for Google Tasks tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GoogleTasksScope(Scope):
    """OAuth scopes for Google Tasks API access."""

    TASKS_READONLY = (
        "https://www.googleapis.com/auth/tasks.readonly",
        "View Tasks",
        "View your Google Tasks and task lists",
        "read",
        False,
    )
    # tasks implies tasks.readonly via scope-implication rules; the
    # description leads with "View" so the consent screen wording matches
    # what the user grants in practice.
    TASKS = (
        "https://www.googleapis.com/auth/tasks",
        "Manage Tasks",
        "View, create, edit, organize, and delete your Google Tasks and task lists",
        "write",
        False,
    )


# Write tools declare both scopes because the Tasks API rejects writes without
# the write scope even when read is held separately. Tokens issued with only
# the write scope are upgraded at runtime via scope-implication rules.
SCOPES: dict[str, list[GoogleTasksScope]] = {
    "google_tasks_list_tasklists": [GoogleTasksScope.TASKS_READONLY],
    "google_tasks_list_tasks": [GoogleTasksScope.TASKS_READONLY],
    "google_tasks_get_task": [GoogleTasksScope.TASKS_READONLY],
    "google_tasks_create_task": [GoogleTasksScope.TASKS_READONLY, GoogleTasksScope.TASKS],
    "google_tasks_update_task": [GoogleTasksScope.TASKS_READONLY, GoogleTasksScope.TASKS],
    "google_tasks_complete_task": [GoogleTasksScope.TASKS_READONLY, GoogleTasksScope.TASKS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_tasks",
    display_name="Google Tasks",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
