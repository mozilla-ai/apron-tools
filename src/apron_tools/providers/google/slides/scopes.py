"""OAuth scope definitions for Google Slides tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class GoogleSlidesScope(StrEnum):
    """OAuth scopes for Google Slides and Drive API access."""

    PRESENTATIONS = "https://www.googleapis.com/auth/presentations"
    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleSlidesScope]] = {
    "google_slides_list_presentations": [GoogleSlidesScope.DRIVE],
    "google_slides_create_presentation": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_copy_presentation": [GoogleSlidesScope.DRIVE],
    "google_slides_read_presentation": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_add_slide": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_update_slide_text": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_duplicate_slide": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_insert_element": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_update_table_cell": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_format_text": [GoogleSlidesScope.PRESENTATIONS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_slides",
    display_name="Google Slides",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
