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
    IM_READ = "im:read"
    IM_WRITE = "im:write"
    MPIM_HISTORY = "mpim:history"
    MPIM_READ = "mpim:read"
    REACTIONS_READ = "reactions:read"
    REACTIONS_WRITE = "reactions:write"
    TEAM_READ = "team:read"
    USERS_READ = "users:read"


# Tool-to-scope mappings reflect the user-token path. They are the scopes
# the OAuth re-consent modal recommends when a tool call fails with a
# missing-scope error, so they must cover every scope Slack checks for that
# tool at runtime — including scopes for channel types (public, private,
# group DM, DM) that the tool only discovers at call time. Missing mappings
# trigger a silent re-consent loop because the user cannot grant a scope
# the modal doesn't surface.
SCOPES: dict[str, list[SlackScope]] = {
    # slack_explore_workspace lists public channels (channels:read), private
    # channels (groups:read), users (users:read), and the workspace name
    # (team:read). All four are listed so the missing-scope modal recommends
    # the full set; the tool degrades gracefully when some scopes are absent.
    "slack_explore_workspace": [
        SlackScope.CHANNELS_READ,
        SlackScope.GROUPS_READ,
        SlackScope.TEAM_READ,
        SlackScope.USERS_READ,
    ],
    # slack_send_channel_message intentionally does NOT list channels:join.
    # channels:join is a Slack bot-only scope — irrelevant when sending as
    # the user — and listing it caused the agent to loop into
    # request_app_connection on unrelated failures (e.g. channel_not_found
    # from passing a channel name as channel_id). slack_join_channel below
    # still legitimately requires channels:join because joining IS the
    # operation.
    "slack_send_channel_message": [SlackScope.CHAT_WRITE],
    "slack_send_user_message": [SlackScope.CHAT_WRITE, SlackScope.IM_WRITE],
    # The channel-id-taking tools below accept a channel_id whose type is
    # only known at runtime. Slack's conversations.info / .history /
    # .replies validate scope per channel type, so the read variants for
    # all four types (public, private, im, mpim) are listed so the modal
    # can recommend whichever is missing.
    "slack_read_channel_messages": [
        SlackScope.CHANNELS_HISTORY,
        SlackScope.GROUPS_HISTORY,
        SlackScope.IM_HISTORY,
        SlackScope.MPIM_HISTORY,
        SlackScope.USERS_READ,
    ],
    "slack_get_channel_info": [
        SlackScope.CHANNELS_READ,
        SlackScope.GROUPS_READ,
        SlackScope.IM_READ,
        SlackScope.MPIM_READ,
    ],
    "slack_read_thread": [
        SlackScope.CHANNELS_HISTORY,
        SlackScope.GROUPS_HISTORY,
        SlackScope.IM_HISTORY,
        SlackScope.MPIM_HISTORY,
        SlackScope.USERS_READ,
    ],
    "slack_join_channel": [SlackScope.CHANNELS_JOIN],
    "slack_edit_message": [SlackScope.CHAT_WRITE],
    # slack_get_permalink accepts a channel_id of any type (C/G/D). Slack's
    # chat.getPermalink resolves the channel server-side and can return
    # missing_scope for a private channel, DM, or group DM if the
    # corresponding read scope isn't granted, so list all four here to let
    # the re-consent modal recommend the one the user actually needs.
    "slack_get_permalink": [
        SlackScope.CHANNELS_READ,
        SlackScope.GROUPS_READ,
        SlackScope.IM_READ,
        SlackScope.MPIM_READ,
    ],
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
