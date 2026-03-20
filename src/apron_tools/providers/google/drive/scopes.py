"""OAuth scope definitions for Google Drive tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class GoogleDriveScope(StrEnum):
    """OAuth scopes for Google Drive API access."""

    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleDriveScope]] = {
    "google_drive_list_files": [GoogleDriveScope.DRIVE],
    "google_drive_create_folder": [GoogleDriveScope.DRIVE],
    "google_drive_get_file_info": [GoogleDriveScope.DRIVE],
    "google_drive_move_file": [GoogleDriveScope.DRIVE],
    "google_drive_search": [GoogleDriveScope.DRIVE],
    "google_drive_share_file": [GoogleDriveScope.DRIVE],
    "google_drive_upload_file": [GoogleDriveScope.DRIVE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_drive",
    display_name="Google Drive",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
