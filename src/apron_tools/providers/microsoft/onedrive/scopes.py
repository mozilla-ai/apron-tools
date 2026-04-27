"""OAuth scope definitions for Microsoft OneDrive tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftOnedriveScope(Scope):
    """OAuth scopes for Microsoft Graph Files / OneDrive API access."""

    FILES_READ = (
        "Files.Read",
        "View Files",
        "View your OneDrive files and folders",
        "read",
        False,
    )
    FILES_READ_WRITE = (
        "Files.ReadWrite",
        "Edit Files",
        "Create, edit, and manage your OneDrive files and folders",
        "write",
        False,
    )


SCOPES: dict[str, list[MicrosoftOnedriveScope]] = {
    "microsoft_onedrive_list_files": [MicrosoftOnedriveScope.FILES_READ],
    "microsoft_onedrive_search": [MicrosoftOnedriveScope.FILES_READ],
    "microsoft_onedrive_get_file_info": [MicrosoftOnedriveScope.FILES_READ],
    "microsoft_onedrive_create_folder": [MicrosoftOnedriveScope.FILES_READ_WRITE],
    "microsoft_onedrive_move_files": [MicrosoftOnedriveScope.FILES_READ_WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_onedrive",
    display_name="Microsoft OneDrive",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
