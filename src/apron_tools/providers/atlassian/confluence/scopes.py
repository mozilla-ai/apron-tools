"""OAuth scope definitions for Atlassian Confluence tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class ConfluenceScope(Scope):
    """OAuth scopes for Atlassian Confluence API access."""

    READ_CONFLUENCE_CONTENT = (
        "read:confluence-content.all",
        "Read Content",
        "View Confluence pages, blog posts, comments, and attachments across all spaces",
        "read",
        False,
    )
    WRITE_CONFLUENCE_CONTENT = (
        "write:confluence-content",
        "Write Content",
        "Create and modify Confluence pages, blog posts, and attachments",
        "write",
        False,
    )
    SEARCH_CONFLUENCE = (
        "search:confluence",
        "Search",
        "Search across Confluence content",
        "read",
        False,
    )


SCOPES: dict[str, list[ConfluenceScope]] = {
    "atlassian_confluence_explore_spaces": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
    "atlassian_confluence_get_page_content": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
    "atlassian_confluence_create_page": [ConfluenceScope.WRITE_CONFLUENCE_CONTENT],
    "atlassian_confluence_update_page": [
        ConfluenceScope.READ_CONFLUENCE_CONTENT,
        ConfluenceScope.WRITE_CONFLUENCE_CONTENT,
    ],
    "atlassian_confluence_search_content": [ConfluenceScope.SEARCH_CONFLUENCE],
    "atlassian_confluence_get_child_pages": [ConfluenceScope.READ_CONFLUENCE_CONTENT],
    "atlassian_confluence_upload_attachment": [ConfluenceScope.WRITE_CONFLUENCE_CONTENT],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="atlassian_confluence",
    display_name="Atlassian Confluence",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
