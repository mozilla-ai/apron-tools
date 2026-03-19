"""Google Slides provider.

API docs:
  - Slides: https://developers.google.com/workspace/slides/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
"""

from .tools import (
    add_slide,
    copy_presentation,
    create_presentation,
    duplicate_slide,
    format_text,
    insert_element,
    list_presentations,
    read_presentation,
    update_slide_text,
    update_table_cell,
)

__all__ = [
    "add_slide",
    "copy_presentation",
    "create_presentation",
    "duplicate_slide",
    "format_text",
    "insert_element",
    "list_presentations",
    "read_presentation",
    "update_slide_text",
    "update_table_cell",
]
