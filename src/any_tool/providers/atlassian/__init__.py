"""Atlassian provider.

API docs:
  - Jira: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
  - Confluence: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
"""

from .confluence import (
    create_page,
    explore_spaces,
    get_child_pages,
    get_page_content,
    search_content,
    update_page,
)
from .jira import (
    add_comment,
    assign_issue,
    create_issue,
    edit_issue,
    explore_issues,
    explore_projects,
    list_boards,
    list_sprints,
    list_versions,
)

__all__ = [
    "add_comment",
    "assign_issue",
    "create_issue",
    "create_page",
    "edit_issue",
    "explore_issues",
    "explore_projects",
    "explore_spaces",
    "get_child_pages",
    "get_page_content",
    "list_boards",
    "list_sprints",
    "list_versions",
    "search_content",
    "update_page",
]
