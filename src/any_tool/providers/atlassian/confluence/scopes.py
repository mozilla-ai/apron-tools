"""OAuth scope definitions for Atlassian Confluence tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class ConfluenceScope(StrEnum):
    """OAuth scopes for Atlassian Confluence API access."""

    READ_CONFLUENCE_CONTENT = "read:confluence-content.all"
    WRITE_CONFLUENCE_CONTENT = "write:confluence-content"
    SEARCH_CONFLUENCE = "search:confluence"


SCOPES: dict[str, list[ConfluenceScope]] = {
    "explore_spaces": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
    "get_page_content": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
    "create_page": [ConfluenceScope.WRITE_CONFLUENCE_CONTENT],
    "update_page": [
        ConfluenceScope.READ_CONFLUENCE_CONTENT,
        ConfluenceScope.WRITE_CONFLUENCE_CONTENT,
    ],
    "search_content": [ConfluenceScope.SEARCH_CONFLUENCE],
    "get_child_pages": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="atlassian_confluence",
    display_name="Atlassian Confluence",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
