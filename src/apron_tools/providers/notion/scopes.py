"""Scope definitions for Notion tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class NotionScope(Scope):
    """Integration capability scopes for Notion API access.

    Notion's OAuth flow does not return per-user scopes; capabilities are
    granted via the integration's settings page in the workspace and
    enforced server-side by the page-/database-sharing model. The values
    below are capability identifiers used by apron-tools to surface the
    integration's permission shape in a consent UI alongside other
    OAuth-based providers.
    """

    READ_CONTENT = (
        "read_content",
        "Read Content",
        "Read pages and databases shared with the integration",
        "read",
        False,
    )
    UPDATE_CONTENT = (
        "update_content",
        "Update Content",
        "Modify content of pages and databases shared with the integration",
        "write",
        False,
    )
    INSERT_CONTENT = (
        "insert_content",
        "Insert Content",
        "Create new pages and database entries within shared workspaces",
        "write",
        False,
    )


SCOPES: dict[str, list[NotionScope]] = {
    "notion_explore_teamspace": [NotionScope.READ_CONTENT],
    "notion_create_page": [NotionScope.INSERT_CONTENT],
    "notion_update_page": [NotionScope.UPDATE_CONTENT],
    "notion_read_page": [NotionScope.READ_CONTENT],
    "notion_get_database_schema": [NotionScope.READ_CONTENT],
    "notion_query_database": [NotionScope.READ_CONTENT],
    "notion_get_database_entry": [NotionScope.READ_CONTENT],
    "notion_create_or_update_database_entry": [NotionScope.INSERT_CONTENT, NotionScope.UPDATE_CONTENT],
    "notion_create_database": [NotionScope.INSERT_CONTENT],
    "notion_update_database_schema": [NotionScope.UPDATE_CONTENT],
    "notion_embed_external_file": [NotionScope.UPDATE_CONTENT],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="notion",
    display_name="Notion",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
