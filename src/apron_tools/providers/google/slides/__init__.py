"""Google Slides provider.

API docs:
  - Slides: https://developers.google.com/workspace/slides/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
"""

from .tools import (
    google_slides_add_slide,
    google_slides_copy_presentation,
    google_slides_create_presentation,
    google_slides_duplicate_slide,
    google_slides_format_text,
    google_slides_insert_element,
    google_slides_insert_image,
    google_slides_list_presentations,
    google_slides_read_presentation,
    google_slides_update_slide_text,
    google_slides_update_table_cell,
)

__all__ = [
    "google_slides_add_slide",
    "google_slides_copy_presentation",
    "google_slides_create_presentation",
    "google_slides_duplicate_slide",
    "google_slides_format_text",
    "google_slides_insert_element",
    "google_slides_insert_image",
    "google_slides_list_presentations",
    "google_slides_read_presentation",
    "google_slides_update_slide_text",
    "google_slides_update_table_cell",
]
