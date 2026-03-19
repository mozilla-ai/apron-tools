"""Microsoft provider.

API docs:
  - Excel: https://learn.microsoft.com/en-us/graph/api/resources/excel
  - Teams: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

from .excel import (
    add_worksheet,
    append_row,
    create_workbook,
    get_workbook_info,
    list_workbooks,
    read_worksheet,
    update_worksheet,
)
from .teams import (
    explore_workspace,
    get_channel_info,
    list_chats,
    read_channel_messages,
    read_chat_messages,
    read_message_replies,
    send_channel_message,
    send_chat_message,
)

__all__ = [
    "add_worksheet",
    "append_row",
    "create_workbook",
    "explore_workspace",
    "get_channel_info",
    "get_workbook_info",
    "list_chats",
    "list_workbooks",
    "read_channel_messages",
    "read_chat_messages",
    "read_message_replies",
    "read_worksheet",
    "send_channel_message",
    "send_chat_message",
    "update_worksheet",
]
