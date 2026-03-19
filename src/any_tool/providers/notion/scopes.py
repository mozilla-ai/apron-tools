"""Scope definitions for Notion tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class NotionScope(StrEnum):
    """Integration capability scopes for Notion API access."""

    READ_CONTENT = "read_content"
    UPDATE_CONTENT = "update_content"
    INSERT_CONTENT = "insert_content"


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
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="notion",
    display_name="Notion",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
