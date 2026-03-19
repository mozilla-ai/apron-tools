"""OAuth scope definitions for Google Slides tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GoogleSlidesScope(StrEnum):
    """OAuth scopes for Google Slides and Drive API access."""

    PRESENTATIONS = "https://www.googleapis.com/auth/presentations"
    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleSlidesScope]] = {
    "list_presentations": [GoogleSlidesScope.DRIVE],
    "create_presentation": [GoogleSlidesScope.PRESENTATIONS],
    "copy_presentation": [GoogleSlidesScope.DRIVE],
    "read_presentation": [GoogleSlidesScope.PRESENTATIONS],
    "add_slide": [GoogleSlidesScope.PRESENTATIONS],
    "update_slide_text": [GoogleSlidesScope.PRESENTATIONS],
    "duplicate_slide": [GoogleSlidesScope.PRESENTATIONS],
    "insert_element": [GoogleSlidesScope.PRESENTATIONS],
    "update_table_cell": [GoogleSlidesScope.PRESENTATIONS],
    "format_text": [GoogleSlidesScope.PRESENTATIONS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_slides",
    display_name="Google Slides",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
