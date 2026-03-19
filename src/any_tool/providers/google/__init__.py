"""Google provider.

API docs:
  - Calendar: https://developers.google.com/workspace/calendar/api/v3/reference
  - Docs: https://developers.google.com/workspace/docs/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
  - Gmail: https://developers.google.com/workspace/gmail/api/reference/rest
  - Sheets: https://developers.google.com/workspace/sheets/api/reference/rest
  - Slides: https://developers.google.com/workspace/slides/api/reference/rest
"""

from .calendar import (
    google_calendar_create_event,
    google_calendar_get_event,
    google_calendar_list_calendars,
    google_calendar_list_events,
    google_calendar_update_event,
)
from .docs import (
    google_docs_copy_document,
    google_docs_create_document,
    google_docs_list_documents,
    google_docs_read_document,
    google_docs_update_document,
)
from .drive import (
    google_drive_create_folder,
    google_drive_get_file_info,
    google_drive_list_files,
    google_drive_move_file,
    google_drive_search,
    google_drive_share_file,
)
from .gmail import (
    gmail_add_label_to_email,
    gmail_create_draft,
    gmail_edit_draft,
    gmail_get_thread_replies,
    gmail_list_emails,
    gmail_list_labels,
    gmail_read_email,
    gmail_remove_label_from_email,
    gmail_reply_to_email,
    gmail_send_email,
)
from .sheets import (
    google_sheets_add_sheet,
    google_sheets_append_row,
    google_sheets_copy_spreadsheet,
    google_sheets_create_spreadsheet,
    google_sheets_find_row,
    google_sheets_list_spreadsheets,
    google_sheets_read_spreadsheet,
    google_sheets_update_spreadsheet,
)
from .slides import (
    google_slides_add_slide,
    google_slides_copy_presentation,
    google_slides_create_presentation,
    google_slides_duplicate_slide,
    google_slides_format_text,
    google_slides_insert_element,
    google_slides_list_presentations,
    google_slides_read_presentation,
    google_slides_update_slide_text,
    google_slides_update_table_cell,
)

__all__ = [
    "gmail_add_label_to_email",
    "gmail_create_draft",
    "gmail_edit_draft",
    "gmail_get_thread_replies",
    "gmail_list_emails",
    "gmail_list_labels",
    "gmail_read_email",
    "gmail_remove_label_from_email",
    "gmail_reply_to_email",
    "gmail_send_email",
    "google_calendar_create_event",
    "google_calendar_get_event",
    "google_calendar_list_calendars",
    "google_calendar_list_events",
    "google_calendar_update_event",
    "google_docs_copy_document",
    "google_docs_create_document",
    "google_docs_list_documents",
    "google_docs_read_document",
    "google_docs_update_document",
    "google_drive_create_folder",
    "google_drive_get_file_info",
    "google_drive_list_files",
    "google_drive_move_file",
    "google_drive_search",
    "google_drive_share_file",
    "google_sheets_add_sheet",
    "google_sheets_append_row",
    "google_sheets_copy_spreadsheet",
    "google_sheets_create_spreadsheet",
    "google_sheets_find_row",
    "google_sheets_list_spreadsheets",
    "google_sheets_read_spreadsheet",
    "google_sheets_update_spreadsheet",
    "google_slides_add_slide",
    "google_slides_copy_presentation",
    "google_slides_create_presentation",
    "google_slides_duplicate_slide",
    "google_slides_format_text",
    "google_slides_insert_element",
    "google_slides_list_presentations",
    "google_slides_read_presentation",
    "google_slides_update_slide_text",
    "google_slides_update_table_cell",
]
