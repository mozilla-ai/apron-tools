"""Atlassian provider.

API docs:
  - Jira: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
  - Confluence: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
"""

from .confluence import (
    atlassian_confluence_create_page,
    atlassian_confluence_explore_spaces,
    atlassian_confluence_get_child_pages,
    atlassian_confluence_get_page_content,
    atlassian_confluence_search_content,
    atlassian_confluence_update_page,
    atlassian_confluence_upload_attachment,
)
from .jira import (
    atlassian_jira_add_comment,
    atlassian_jira_assign_issue,
    atlassian_jira_create_issue,
    atlassian_jira_edit_issue,
    atlassian_jira_explore_issues,
    atlassian_jira_explore_projects,
    atlassian_jira_list_boards,
    atlassian_jira_list_sprints,
    atlassian_jira_list_versions,
    atlassian_jira_upload_attachment,
)

__all__ = [
    "atlassian_confluence_create_page",
    "atlassian_confluence_explore_spaces",
    "atlassian_confluence_get_child_pages",
    "atlassian_confluence_get_page_content",
    "atlassian_confluence_search_content",
    "atlassian_confluence_update_page",
    "atlassian_confluence_upload_attachment",
    "atlassian_jira_add_comment",
    "atlassian_jira_assign_issue",
    "atlassian_jira_create_issue",
    "atlassian_jira_edit_issue",
    "atlassian_jira_explore_issues",
    "atlassian_jira_explore_projects",
    "atlassian_jira_list_boards",
    "atlassian_jira_list_sprints",
    "atlassian_jira_list_versions",
    "atlassian_jira_upload_attachment",
]
