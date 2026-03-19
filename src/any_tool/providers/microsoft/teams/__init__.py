"""Microsoft Teams provider.

API docs:
  - Teams: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

from .tools import (
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
    "microsoft_teams_explore_workspace",
    "microsoft_teams_get_channel_info",
    "microsoft_teams_list_chats",
    "microsoft_teams_read_channel_messages",
    "microsoft_teams_read_chat_messages",
    "microsoft_teams_read_message_replies",
    "microsoft_teams_send_channel_message",
    "microsoft_teams_send_chat_message",
]
