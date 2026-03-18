"""Google provider.

API docs:
  - Calendar: https://developers.google.com/workspace/calendar/api/v3/reference
  - Docs: https://developers.google.com/workspace/docs/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
  - Gmail: https://developers.google.com/workspace/gmail/api/reference/rest
  - Sheets: https://developers.google.com/workspace/sheets/api/reference/rest
"""

from .calendar import (
    create_event,
    get_event,
    list_calendars,
    list_events,
    update_event,
)
from .docs import (
    copy_document,
    create_document,
    list_documents,
    read_document,
    update_document,
)
from .drive import (
    create_folder,
    get_file_info,
    list_files,
    move_file,
    search,
    share_file,
)
from .gmail import (
    add_label_to_email,
    create_draft,
    edit_draft,
    get_thread_replies,
    list_emails,
    list_labels,
    read_email,
    remove_label_from_email,
    reply_to_email,
    send_email,
)
from .sheets import (
    add_sheet,
    append_row,
    copy_spreadsheet,
    create_spreadsheet,
    find_row,
    list_spreadsheets,
    read_spreadsheet,
    update_spreadsheet,
)

__all__ = [
    "add_label_to_email",
    "add_sheet",
    "append_row",
    "copy_document",
    "copy_spreadsheet",
    "create_document",
    "create_draft",
    "create_event",
    "create_folder",
    "create_spreadsheet",
    "edit_draft",
    "find_row",
    "get_event",
    "get_file_info",
    "get_thread_replies",
    "list_calendars",
    "list_documents",
    "list_emails",
    "list_events",
    "list_files",
    "list_labels",
    "list_spreadsheets",
    "move_file",
    "read_document",
    "read_email",
    "read_spreadsheet",
    "remove_label_from_email",
    "reply_to_email",
    "search",
    "send_email",
    "share_file",
    "update_document",
    "update_event",
    "update_spreadsheet",
]
