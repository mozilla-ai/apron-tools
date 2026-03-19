"""OAuth scope definitions for Microsoft Teams tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class MicrosoftTeamsScope(StrEnum):
    """OAuth scopes for Microsoft Graph Teams API access."""

    TEAM_READ_BASIC = "Team.ReadBasic.All"
    CHANNEL_READ_BASIC = "Channel.ReadBasic.All"
    CHAT_READ = "Chat.Read"
    CHAT_READ_WRITE = "Chat.ReadWrite"
    CHANNEL_MESSAGE_READ = "ChannelMessage.Read.All"
    CHANNEL_MESSAGE_SEND = "ChannelMessage.Send"


SCOPES: dict[str, list[MicrosoftTeamsScope]] = {
    "explore_workspace": [
        MicrosoftTeamsScope.TEAM_READ_BASIC,
        MicrosoftTeamsScope.CHANNEL_READ_BASIC,
    ],
    "get_channel_info": [MicrosoftTeamsScope.CHANNEL_READ_BASIC],
    "list_chats": [MicrosoftTeamsScope.CHAT_READ],
    "read_chat_messages": [MicrosoftTeamsScope.CHAT_READ],
    "read_channel_messages": [MicrosoftTeamsScope.CHANNEL_MESSAGE_READ],
    "read_message_replies": [MicrosoftTeamsScope.CHANNEL_MESSAGE_READ],
    "send_chat_message": [MicrosoftTeamsScope.CHAT_READ_WRITE],
    "send_channel_message": [MicrosoftTeamsScope.CHANNEL_MESSAGE_SEND],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_teams",
    display_name="Microsoft Teams",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
