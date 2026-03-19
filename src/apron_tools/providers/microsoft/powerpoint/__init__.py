"""Microsoft PowerPoint provider.

API docs:
  - OneDrive: https://learn.microsoft.com/en-us/graph/api/resources/onedrive
  - PowerPoint: https://learn.microsoft.com/en-us/graph/api/resources/presentation
"""

from .tools import (
    microsoft_powerpoint_add_slide,
    microsoft_powerpoint_create_presentation,
    microsoft_powerpoint_explore_presentations,
    microsoft_powerpoint_read_presentation,
    microsoft_powerpoint_update_slide_text,
    microsoft_powerpoint_upload_to_onedrive,
)

__all__ = [
    "microsoft_powerpoint_add_slide",
    "microsoft_powerpoint_create_presentation",
    "microsoft_powerpoint_explore_presentations",
    "microsoft_powerpoint_read_presentation",
    "microsoft_powerpoint_update_slide_text",
    "microsoft_powerpoint_upload_to_onedrive",
]
