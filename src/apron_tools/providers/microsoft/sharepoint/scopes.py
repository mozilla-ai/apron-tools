"""OAuth scope definitions for Microsoft SharePoint tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftSharePointScope(Scope):
    """OAuth scopes for Microsoft Graph SharePoint API access."""

    SITES_READ_ALL = (
        "Sites.Read.All",
        "View SharePoint Sites",
        "View SharePoint sites and their content",
        "read",
        False,
    )
    SITES_READ_WRITE_ALL = (
        "Sites.ReadWrite.All",
        "Edit SharePoint Sites",
        "Create and modify content on SharePoint sites",
        "write",
        False,
    )
    FILES_READ_WRITE_ALL = (
        "Files.ReadWrite.All",
        "Edit All Files",
        "Create, edit, and manage all files across SharePoint",
        "write",
        False,
    )


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
