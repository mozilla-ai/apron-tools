"""OAuth scope definitions for Google Drive tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GoogleDriveScope(StrEnum):
    """OAuth scopes for Google Drive API access."""

    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleDriveScope]] = {
    "list_files": [GoogleDriveScope.DRIVE],
    "create_folder": [GoogleDriveScope.DRIVE],
    "get_file_info": [GoogleDriveScope.DRIVE],
    "move_file": [GoogleDriveScope.DRIVE],
    "search": [GoogleDriveScope.DRIVE],
    "share_file": [GoogleDriveScope.DRIVE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_drive",
    display_name="Google Drive",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
