"""Microsoft Teams provider.

API docs:
  - Teams: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
"""

from .tools import (
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
    "explore_workspace",
    "get_channel_info",
    "list_chats",
    "read_channel_messages",
    "read_chat_messages",
    "read_message_replies",
    "send_channel_message",
    "send_chat_message",
]
