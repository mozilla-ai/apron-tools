"""Slack tool functions for interacting with the Slack Web API."""

from __future__ import annotations

import base64
import re

import httpx
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from any_tool.providers.slack.types import (
    AddReactionParams,
    AddReactionResult,
    DownloadFileParams,
    DownloadFileResult,
    EditMessageParams,
    EditMessageResult,
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetChannelInfoParams,
    GetChannelInfoResult,
    GetFileInfoParams,
    GetFileInfoResult,
    GetPermalinkParams,
    GetPermalinkResult,
    GetReactionsParams,
    GetReactionsResult,
    JoinChannelParams,
    JoinChannelResult,
    ReadChannelMessagesParams,
    ReadChannelMessagesResult,
    ReadThreadParams,
    ReadThreadResult,
    SendChannelMessageParams,
    SendChannelMessageResult,
    SendUserMessageParams,
    SendUserMessageResult,
    SlackChannel,
    SlackFile,
    SlackMessage,
    SlackReaction,
    SlackUser,
)
from any_tool.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://slack.com/api/"

_REACTION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_+-]+(?:::[A-Za-z0-9_+-]+)*$")


def _client(token: str, base_url: str) -> AsyncWebClient:
    """Build an AsyncWebClient for the given token and base URL."""
    return AsyncWebClient(token=token, base_url=base_url)


def _build_user_map(members: list[dict]) -> dict[str, str]:
    """Build a mapping from user ID to display name."""
    user_map: dict[str, str] = {}
    for user in members:
        uid = user.get("id", "")
        display_name = (
            user.get("profile", {}).get("display_name")
            or user.get("profile", {}).get("real_name")
            or user.get("name", "Unknown")
        )
        user_map[uid] = display_name
    return user_map


@tool(
    scopes=SCOPES["slack_explore_workspace"],
    api_docs="https://docs.slack.dev/reference/web-api/team/info",
    provider="slack",
)
async def slack_explore_workspace(
    params: ExploreWorkspaceParams,  # noqa: ARG001
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreWorkspaceResult:
    """Explore the Slack workspace structure, including channels and users."""
    client = _client(token, base_url)
    workspace_name = "Slack Workspace"
    channels: list[SlackChannel] = []
    users: list[SlackUser] = []

    try:
        team_resp = await client.team_info()
        workspace_name = team_resp.get("team", {}).get("name", workspace_name)
    except SlackApiError:
        pass

    try:
        cursor = None
        while True:
            kwargs: dict = {"types": "public_channel,private_channel", "limit": 1000}
            if cursor:
                kwargs["cursor"] = cursor
            ch_resp = await client.conversations_list(**kwargs)
            for ch in ch_resp.get("channels", []):
                channels.append(
                    SlackChannel(
                        id=ch.get("id", ""),
                        name=ch.get("name", ""),
                        is_private=ch.get("is_private", False),
                        num_members=ch.get("num_members", 0),
                    )
                )
            cursor = ch_resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except SlackApiError:
        pass

    try:
        users_resp = await client.users_list(limit=1000)
        for u in users_resp.get("members", []):
            users.append(
                SlackUser(
                    id=u.get("id", ""),
                    name=u.get("name", ""),
                    real_name=u.get("profile", {}).get("real_name"),
                    deleted=u.get("deleted", False),
                )
            )
    except SlackApiError:
        pass

    return ExploreWorkspaceResult(
        success=True,
        workspace_name=workspace_name,
        channels=channels,
        users=users,
    )


@tool(
    scopes=SCOPES["slack_send_channel_message"],
    api_docs="https://docs.slack.dev/reference/web-api/chat/post-message",
    provider="slack",
)
async def slack_send_channel_message(
    params: SendChannelMessageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SendChannelMessageResult:
    """Send a message to a Slack channel."""
    client = _client(token, base_url)
    try:
        kwargs: dict = {"channel": params.channel_id, "text": params.message}
        if params.thread_ts:
            kwargs["thread_ts"] = params.thread_ts
        resp = await client.chat_postMessage(**kwargs)
        return SendChannelMessageResult(
            success=True,
            channel=resp.get("channel", ""),
            ts=resp.get("ts", ""),
            message=resp.get("message"),
        )
    except SlackApiError as exc:
        return SendChannelMessageResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_send_user_message"],
    api_docs="https://docs.slack.dev/reference/web-api/chat/post-message",
    provider="slack",
)
async def slack_send_user_message(
    params: SendUserMessageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SendUserMessageResult:
    """Send a direct message to a Slack user."""
    client = _client(token, base_url)
    try:
        conv_resp = await client.conversations_open(users=params.user_id)
        channel_id = conv_resp.get("channel", {}).get("id", "")
        resp = await client.chat_postMessage(channel=channel_id, text=params.message)
        return SendUserMessageResult(
            success=True,
            channel=resp.get("channel", ""),
            ts=resp.get("ts", ""),
            message=resp.get("message"),
        )
    except SlackApiError as exc:
        return SendUserMessageResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_read_channel_messages"],
    api_docs="https://docs.slack.dev/reference/web-api/conversations/history",
    provider="slack",
)
async def slack_read_channel_messages(
    params: ReadChannelMessagesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ReadChannelMessagesResult:
    """Read recent messages from a Slack channel."""
    client = _client(token, base_url)
    limit = min(params.limit, 100)
    try:
        kwargs: dict = {"channel": params.channel_id, "limit": limit}
        if params.oldest is not None:
            kwargs["oldest"] = params.oldest
        if params.latest is not None:
            kwargs["latest"] = params.latest

        history_resp = await client.conversations_history(**kwargs)
        raw_messages = history_resp.get("messages", [])

        users_resp = await client.users_list(limit=1000)
        user_map = _build_user_map(users_resp.get("members", []))

        messages = [
            SlackMessage(
                user=m.get("user"),
                text=m.get("text", ""),
                ts=m.get("ts", ""),
                reply_count=m.get("reply_count"),
                files=m.get("files"),
            )
            for m in reversed(raw_messages)
        ]

        return ReadChannelMessagesResult(
            success=True,
            messages=messages,
            has_more=history_resp.get("has_more", False),
            user_map=user_map,
        )
    except SlackApiError as exc:
        return ReadChannelMessagesResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_get_channel_info"],
    api_docs="https://docs.slack.dev/reference/web-api/conversations/info",
    provider="slack",
)
async def slack_get_channel_info(
    params: GetChannelInfoParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetChannelInfoResult:
    """Get information about a Slack channel."""
    client = _client(token, base_url)
    try:
        resp = await client.conversations_info(channel=params.channel_id)
        ch = resp.get("channel", {})
        channel = SlackChannel(
            id=ch.get("id", ""),
            name=ch.get("name", ""),
            is_private=ch.get("is_private", False),
            num_members=ch.get("num_members", 0),
        )
        return GetChannelInfoResult(
            success=True,
            channel=channel,
            topic=ch.get("topic", {}).get("value", ""),
            purpose=ch.get("purpose", {}).get("value", ""),
        )
    except SlackApiError as exc:
        return GetChannelInfoResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_read_thread"],
    api_docs="https://docs.slack.dev/reference/web-api/conversations/replies",
    provider="slack",
)
async def slack_read_thread(
    params: ReadThreadParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ReadThreadResult:
    """Read replies in a Slack thread."""
    client = _client(token, base_url)
    try:
        kwargs: dict = {
            "channel": params.channel_id,
            "ts": params.thread_ts,
            "limit": 100,
        }
        if params.oldest is not None:
            kwargs["oldest"] = params.oldest
        if params.latest is not None:
            kwargs["latest"] = params.latest

        resp = await client.conversations_replies(**kwargs)
        raw_messages = resp.get("messages", [])

        users_resp = await client.users_list(limit=1000)
        user_map = _build_user_map(users_resp.get("members", []))

        messages = [
            SlackMessage(
                user=m.get("user"),
                text=m.get("text", ""),
                ts=m.get("ts", ""),
                files=m.get("files"),
            )
            for m in raw_messages
        ]

        return ReadThreadResult(success=True, messages=messages, user_map=user_map)
    except SlackApiError as exc:
        return ReadThreadResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_join_channel"],
    api_docs="https://docs.slack.dev/reference/web-api/conversations/join",
    provider="slack",
)
async def slack_join_channel(
    params: JoinChannelParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> JoinChannelResult:
    """Join a Slack channel."""
    client = _client(token, base_url)
    try:
        resp = await client.conversations_join(channel=params.channel_id)
        ch = resp.get("channel", {})
        return JoinChannelResult(
            success=True,
            channel_id=ch.get("id", params.channel_id),
            channel_name=ch.get("name", params.channel_id),
        )
    except SlackApiError as exc:
        return JoinChannelResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_edit_message"],
    api_docs="https://docs.slack.dev/reference/web-api/chat/update",
    provider="slack",
)
async def slack_edit_message(
    params: EditMessageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> EditMessageResult:
    """Edit a previously sent Slack message."""
    client = _client(token, base_url)
    try:
        resp = await client.chat_update(
            channel=params.channel_id,
            ts=params.message_ts,
            text=params.new_text,
        )
        return EditMessageResult(
            success=True,
            channel=resp.get("channel", ""),
            ts=resp.get("ts", ""),
        )
    except SlackApiError as exc:
        return EditMessageResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_get_permalink"],
    api_docs="https://docs.slack.dev/reference/web-api/chat/get-permalink",
    provider="slack",
)
async def slack_get_permalink(
    params: GetPermalinkParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetPermalinkResult:
    """Get a permanent URL for a Slack message."""
    client = _client(token, base_url)
    try:
        resp = await client.chat_getPermalink(
            channel=params.channel_id,
            message_ts=params.message_ts,
        )
        return GetPermalinkResult(
            success=True,
            permalink=resp.get("permalink", ""),
        )
    except SlackApiError as exc:
        return GetPermalinkResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_get_file_info"],
    api_docs="https://docs.slack.dev/reference/web-api/files/info",
    provider="slack",
)
async def slack_get_file_info(
    params: GetFileInfoParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetFileInfoResult:
    """Get metadata for a file shared in Slack."""
    client = _client(token, base_url)
    try:
        resp = await client.files_info(file=params.file_id)
        f = resp.get("file", {})
        slack_file = SlackFile(
            id=f.get("id", ""),
            name=f.get("name", ""),
            title=f.get("title", ""),
            filetype=f.get("filetype", ""),
            pretty_type=f.get("pretty_type", ""),
            mimetype=f.get("mimetype", ""),
            size=f.get("size", 0),
            created=f.get("created", 0),
            user=f.get("user", ""),
            url_private_download=f.get("url_private_download", ""),
        )
        return GetFileInfoResult(success=True, file=slack_file)
    except SlackApiError as exc:
        return GetFileInfoResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_download_file"],
    api_docs="https://docs.slack.dev/reference/web-api/files/info",
    provider="slack",
)
async def slack_download_file(
    params: DownloadFileParams,
    *,
    token: str,
    base_url: str = _BASE_URL,  # noqa: ARG001
) -> DownloadFileResult:
    """Download a file from Slack using its private URL."""
    max_bytes = params.max_size_mb * 1024 * 1024
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as http_client:
            response = await http_client.get(params.url, headers=headers)
    except httpx.TimeoutException:
        return DownloadFileResult(success=False, error="Request timed out.")
    except httpx.HTTPError as exc:
        return DownloadFileResult(success=False, error=str(exc))

    if response.status_code != 200:
        return DownloadFileResult(success=False, error=f"HTTP {response.status_code}")

    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        size_mb = int(content_length) / (1024 * 1024)
        return DownloadFileResult(
            success=False,
            error=f"File too large: {size_mb:.1f} MB (max {params.max_size_mb} MB).",
        )

    if len(response.content) > max_bytes:
        size_mb = len(response.content) / (1024 * 1024)
        return DownloadFileResult(
            success=False,
            error=f"File too large: {size_mb:.1f} MB (max {params.max_size_mb} MB).",
        )

    content_type = response.headers.get("content-type", "application/octet-stream")
    mime_type = content_type.split(";")[0].strip()

    if mime_type.startswith("text/"):
        return DownloadFileResult(success=True, content=response.text, mime_type=mime_type)

    encoded = base64.b64encode(response.content).decode("ascii")
    return DownloadFileResult(success=True, content=encoded, mime_type=mime_type)


@tool(
    scopes=SCOPES["slack_get_reactions"],
    api_docs="https://docs.slack.dev/reference/web-api/reactions/get",
    provider="slack",
)
async def slack_get_reactions(
    params: GetReactionsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetReactionsResult:
    """Get reactions for a Slack message, file, or file comment."""
    if not ((params.channel_id and params.timestamp) or params.file_id or params.file_comment_id):
        return GetReactionsResult(
            success=False,
            error="Must provide either (channel_id and timestamp), file_id, or file_comment_id.",
        )

    client = _client(token, base_url)
    try:
        kwargs: dict = {}
        if params.channel_id and params.timestamp:
            kwargs["channel"] = params.channel_id
            kwargs["timestamp"] = params.timestamp
        elif params.file_id:
            kwargs["file"] = params.file_id
        elif params.file_comment_id:
            kwargs["file_comment"] = params.file_comment_id
        if params.full:
            kwargs["full"] = True

        resp = await client.reactions_get(**kwargs)
        item_type = resp.get("type", "")

        if item_type == "message":
            item = resp.get("message", {})
        elif item_type == "file":
            item = resp.get("file", {})
        else:
            item = resp.get("comment", {})

        reactions = [
            SlackReaction(
                name=r.get("name", ""),
                count=r.get("count", 0),
                users=r.get("users", []),
            )
            for r in item.get("reactions", [])
        ]

        return GetReactionsResult(success=True, reactions=reactions, item_type=item_type)
    except SlackApiError as exc:
        return GetReactionsResult(success=False, error=exc.response.get("error", str(exc)))


@tool(
    scopes=SCOPES["slack_add_reaction"],
    api_docs="https://docs.slack.dev/reference/web-api/reactions/add",
    provider="slack",
)
async def slack_add_reaction(
    params: AddReactionParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> AddReactionResult:
    """Add an emoji reaction to a Slack message."""
    normalized = params.reaction_name.strip().strip(":")
    if not normalized:
        return AddReactionResult(success=False, error="reaction_name must not be empty.")
    if not _REACTION_NAME_PATTERN.fullmatch(normalized):
        return AddReactionResult(success=False, error="reaction_name contains invalid characters.")

    client = _client(token, base_url)
    try:
        await client.reactions_add(
            channel=params.channel_id,
            timestamp=params.timestamp,
            name=normalized,
        )
        return AddReactionResult(
            success=True,
            reaction_name=normalized,
            channel_id=params.channel_id,
            timestamp=params.timestamp,
        )
    except SlackApiError as exc:
        return AddReactionResult(success=False, error=exc.response.get("error", str(exc)))
