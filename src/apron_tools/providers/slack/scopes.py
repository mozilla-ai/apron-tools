"""OAuth scope definitions for Slack tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class SlackScope(StrEnum):
    """OAuth scopes for Slack API access."""

    CHANNELS_HISTORY = "channels:history"
    CHANNELS_JOIN = "channels:join"
    CHANNELS_READ = "channels:read"
    CHAT_WRITE = "chat:write"
    FILES_READ = "files:read"
    GROUPS_HISTORY = "groups:history"
    GROUPS_READ = "groups:read"
    IM_HISTORY = "im:history"
    IM_WRITE = "im:write"
    REACTIONS_READ = "reactions:read"
    REACTIONS_WRITE = "reactions:write"
    TEAM_READ = "team:read"
    USERS_READ = "users:read"


SCOPES: dict[str, list[SlackScope]] = {
    "slack_explore_workspace": [
        SlackScope.CHANNELS_READ,
        SlackScope.TEAM_READ,
        SlackScope.USERS_READ,
    ],
    "slack_send_channel_message": [SlackScope.CHAT_WRITE],
    "slack_send_user_message": [SlackScope.CHAT_WRITE, SlackScope.IM_WRITE],
    "slack_read_channel_messages": [
        SlackScope.CHANNELS_HISTORY,
        SlackScope.GROUPS_HISTORY,
        SlackScope.USERS_READ,
    ],
    "slack_get_channel_info": [SlackScope.CHANNELS_READ, SlackScope.GROUPS_READ],
    "slack_read_thread": [
        SlackScope.CHANNELS_HISTORY,
        SlackScope.GROUPS_HISTORY,
        SlackScope.USERS_READ,
    ],
    "slack_join_channel": [SlackScope.CHANNELS_JOIN],
    "slack_edit_message": [SlackScope.CHAT_WRITE],
    "slack_get_permalink": [SlackScope.CHANNELS_READ],
    "slack_get_file_info": [SlackScope.FILES_READ],
    "slack_download_file": [SlackScope.FILES_READ],
    "slack_save_file_for_upload": [SlackScope.FILES_READ],
    "slack_get_reactions": [SlackScope.REACTIONS_READ],
    "slack_add_reaction": [SlackScope.REACTIONS_WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="slack",
    display_name="Slack",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
