"""OAuth scope definitions for Microsoft Teams tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftTeamsScope(Scope):
    """OAuth scopes for Microsoft Graph Teams API access."""

    TEAM_READ_BASIC = (
        "Team.ReadBasic.All",
        "View Teams",
        "Read basic information about your teams",
        "read",
        False,
    )
    CHANNEL_READ_BASIC = (
        "Channel.ReadBasic.All",
        "View Channels",
        "Read basic information about Teams channels",
        "read",
        False,
    )
    CHAT_READ = (
        "Chat.Read",
        "Read Chats",
        "View chat messages in Microsoft Teams",
        "read",
        False,
    )
    CHAT_READ_WRITE = (
        "Chat.ReadWrite",
        "Send Chat Messages",
        "Send and manage chat messages in Teams",
        "write",
        False,
    )
    CHANNEL_MESSAGE_READ = (
        "ChannelMessage.Read.All",
        "Read Channel Messages",
        "View messages in Teams channels",
        "read",
        False,
    )
    CHANNEL_MESSAGE_SEND = (
        "ChannelMessage.Send",
        "Send Channel Messages",
        "Send messages to Teams channels",
        "write",
        False,
    )


SCOPES: dict[str, list[MicrosoftTeamsScope]] = {
    "microsoft_teams_explore_workspace": [
        MicrosoftTeamsScope.TEAM_READ_BASIC,
        MicrosoftTeamsScope.CHANNEL_READ_BASIC,
    ],
    "microsoft_teams_get_channel_info": [MicrosoftTeamsScope.CHANNEL_READ_BASIC],
    "microsoft_teams_list_chats": [MicrosoftTeamsScope.CHAT_READ],
    "microsoft_teams_read_chat_messages": [MicrosoftTeamsScope.CHAT_READ],
    "microsoft_teams_read_channel_messages": [MicrosoftTeamsScope.CHANNEL_MESSAGE_READ],
    "microsoft_teams_read_message_replies": [MicrosoftTeamsScope.CHANNEL_MESSAGE_READ],
    "microsoft_teams_send_chat_message": [MicrosoftTeamsScope.CHAT_READ_WRITE],
    "microsoft_teams_send_channel_message": [MicrosoftTeamsScope.CHANNEL_MESSAGE_SEND],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_teams",
    display_name="Microsoft Teams",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
