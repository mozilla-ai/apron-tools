"""Google provider.

API docs:
  - Calendar: https://developers.google.com/workspace/calendar/api/v3/reference
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
    "copy_spreadsheet",
    "create_draft",
    "create_event",
    "create_spreadsheet",
    "edit_draft",
    "find_row",
    "get_event",
    "get_thread_replies",
    "list_calendars",
    "list_emails",
    "list_events",
    "list_labels",
    "list_spreadsheets",
    "read_email",
    "read_spreadsheet",
    "remove_label_from_email",
    "reply_to_email",
    "send_email",
    "update_event",
    "update_spreadsheet",
]
