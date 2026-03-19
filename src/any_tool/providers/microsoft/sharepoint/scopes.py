"""OAuth scope definitions for Microsoft SharePoint tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class MicrosoftSharePointScope(StrEnum):
    """OAuth scopes for Microsoft Graph SharePoint API access."""

    SITES_READ_ALL = "Sites.Read.All"
    SITES_READ_WRITE_ALL = "Sites.ReadWrite.All"
    FILES_READ_WRITE_ALL = "Files.ReadWrite.All"


SCOPES: dict[str, list[MicrosoftSharePointScope]] = {
    "microsoft_sharepoint_list_sites": [MicrosoftSharePointScope.SITES_READ_ALL],
    "microsoft_sharepoint_list_drives": [MicrosoftSharePointScope.SITES_READ_ALL],
    "microsoft_sharepoint_explore_drive": [MicrosoftSharePointScope.FILES_READ_WRITE_ALL],
    "microsoft_sharepoint_create_folder": [MicrosoftSharePointScope.FILES_READ_WRITE_ALL],
    "microsoft_sharepoint_search": [MicrosoftSharePointScope.FILES_READ_WRITE_ALL],
    "microsoft_sharepoint_move_file": [MicrosoftSharePointScope.FILES_READ_WRITE_ALL],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_sharepoint",
    display_name="Microsoft SharePoint",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
