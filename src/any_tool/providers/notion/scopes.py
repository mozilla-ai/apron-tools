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
    "explore_teamspace": [NotionScope.READ_CONTENT],
    "create_page": [NotionScope.INSERT_CONTENT],
    "update_page": [NotionScope.UPDATE_CONTENT],
    "read_page": [NotionScope.READ_CONTENT],
    "get_database_schema": [NotionScope.READ_CONTENT],
    "query_database": [NotionScope.READ_CONTENT],
    "get_database_entry": [NotionScope.READ_CONTENT],
    "create_or_update_database_entry": [NotionScope.INSERT_CONTENT, NotionScope.UPDATE_CONTENT],
    "create_database": [NotionScope.INSERT_CONTENT],
    "update_database_schema": [NotionScope.UPDATE_CONTENT],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="notion",
    display_name="Notion",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
