"""Atlassian Confluence provider.

API docs: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
"""

from .tools import (
    create_page,
    explore_spaces,
    get_child_pages,
    get_page_content,
    search_content,
    update_page,
)

__all__ = [
    "create_page",
    "explore_spaces",
    "get_child_pages",
    "get_page_content",
    "search_content",
    "update_page",
]
