"""Atlassian Confluence provider.

API docs: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
"""

from .tools import (
    atlassian_confluence_create_page,
    atlassian_confluence_explore_spaces,
    atlassian_confluence_get_child_pages,
    atlassian_confluence_get_page_content,
    atlassian_confluence_search_content,
    atlassian_confluence_update_page,
)

__all__ = [
    "atlassian_confluence_create_page",
    "atlassian_confluence_explore_spaces",
    "atlassian_confluence_get_child_pages",
    "atlassian_confluence_get_page_content",
    "atlassian_confluence_search_content",
    "atlassian_confluence_update_page",
]
