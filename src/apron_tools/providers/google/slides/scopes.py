"""OAuth scope definitions for Google Slides tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GoogleSlidesScope(Scope):
    """OAuth scopes for Google Slides and Drive API access."""

    PRESENTATIONS = (
        "https://www.googleapis.com/auth/presentations",
        "Full Presentation Access",
        "View, edit, create, and delete all Google Slides presentations",
        "write",
        False,
    )
    DRIVE = (
        "https://www.googleapis.com/auth/drive",
        "Full Drive Access",
        "View, edit, create, delete, and share all Google Drive files",
        "write",
        False,
    )


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
    "google_slides_insert_image": [GoogleSlidesScope.PRESENTATIONS, GoogleSlidesScope.DRIVE],
    "google_slides_delete_shape": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_delete_slide": [GoogleSlidesScope.PRESENTATIONS],
    "google_slides_update_slide_background": [GoogleSlidesScope.PRESENTATIONS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_slides",
    display_name="Google Slides",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
