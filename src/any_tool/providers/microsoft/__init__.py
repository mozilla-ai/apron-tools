"""Microsoft provider.

API docs:
  - Excel: https://learn.microsoft.com/en-us/graph/api/resources/excel
  - Teams: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

from .excel import (
    microsoft_excel_add_worksheet,
    microsoft_excel_append_row,
    microsoft_excel_create_workbook,
    microsoft_excel_get_workbook_info,
    microsoft_excel_list_workbooks,
    microsoft_excel_read_worksheet,
    microsoft_excel_update_worksheet,
)
from .teams import (
    microsoft_teams_explore_workspace,
    microsoft_teams_get_channel_info,
    microsoft_teams_list_chats,
    microsoft_teams_read_channel_messages,
    microsoft_teams_read_chat_messages,
    microsoft_teams_read_message_replies,
    microsoft_teams_send_channel_message,
    microsoft_teams_send_chat_message,
)

__all__ = [
    "microsoft_excel_add_worksheet",
    "microsoft_excel_append_row",
    "microsoft_excel_create_workbook",
    "microsoft_excel_get_workbook_info",
    "microsoft_excel_list_workbooks",
    "microsoft_excel_read_worksheet",
    "microsoft_excel_update_worksheet",
    "microsoft_teams_explore_workspace",
    "microsoft_teams_get_channel_info",
    "microsoft_teams_list_chats",
    "microsoft_teams_read_channel_messages",
    "microsoft_teams_read_chat_messages",
    "microsoft_teams_read_message_replies",
    "microsoft_teams_send_channel_message",
    "microsoft_teams_send_chat_message",
]
