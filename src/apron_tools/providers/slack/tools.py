"""Slack tool functions for interacting with the Slack Web API."""

from __future__ import annotations

import base64
import contextlib
import re
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from apron_tools._utils import parse_csv_ids
from apron_tools.providers.slack.types import (
    AddReactionItem,
    AddReactionsParams,
    AddReactionsResult,
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
    ListMyConversationsParams,
    ListMyConversationsResult,
    ReadChannelMessagesParams,
    ReadChannelMessagesResult,
    ReadThreadParams,
    ReadThreadResult,
    SaveFileForUploadParams,
    SaveFileForUploadResult,
    SendChannelMessageParams,
    SendChannelMessageResult,
    SendUserMessageParams,
    SendUserMessageResult,
    SlackChannel,
    SlackConversation,
    SlackFile,
    SlackMessage,
    SlackReaction,
    SlackUser,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://slack.com/api/"

_REACTION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_+-]+(?:::[A-Za-z0-9_+-]+)*$")

# Slack channel/conversation IDs start with C (public channel), G (private
# channel/group), or D (direct message), followed by 8+ uppercase alphanumerics.
# Real Slack IDs are 9-11 characters total. Channel names are lowercase with
# hyphens/underscores/periods/digits and so can never match — that's what lets
# us distinguish a name like ``any-forge-test`` from an ID like ``C01234ABCD``.
_SLACK_CHANNEL_ID_PATTERN = re.compile(r"^[CGD][A-Z0-9]{8,}$")

# Slack API error codes that are NOT permissions/scope failures. Returning them
# via the bare error code caused agents to misdiagnose them as missing-scope
# problems and loop into an OAuth re-consent flow. The error formatter below
# appends an explicit "NOT a permissions error" disclaimer for these codes so
# the agent stops re-consenting and corrects its inputs instead.
_SLACK_NON_PERMISSION_ERRORS = frozenset(
    {
        "channel_not_found",
        "not_in_channel",
        "is_archived",
        "user_not_found",
        "user_not_visible",
        "message_not_found",
        "thread_not_found",
        "file_not_found",
        "invalid_channel",
        "invalid_arguments",
        "invalid_arg_name",
    }
)

# Typed Slack text nodes whose ``text`` field is the final string to surface;
# anything else is treated as a container and walked recursively.
_TEXT_NODE_TYPES = frozenset({"mrkdwn", "plain_text", "text"})

# Keys on legacy Slack attachment dicts that carry raw human-readable strings,
# listed in the order Slack renders them so the extracted text preserves the
# author's intended reading order: ``pretext`` sits above the attachment body,
# the attachment ``title`` sits above ``text`` (body), ``value`` pairs with
# each field's ``title`` inside ``fields`` children, and ``fallback`` is the
# last-resort alternative for clients that can't render attachments.
_RAW_TEXT_KEYS = ("pretext", "title", "text", "value", "fallback")

_USERS_CONVERSATIONS_ALLOWED_TYPES = frozenset({"im", "mpim", "public_channel", "private_channel"})


def _validate_slack_channel_id(channel_id: str) -> str | None:
    """Return an error string if *channel_id* is not a valid Slack ID.

    Slack's ``chat.postMessage`` and related endpoints require a real
    channel ID (e.g. ``C01234ABCD``) — not the human-readable name
    (e.g. ``any-forge-test``). When passed a name they return
    ``channel_not_found``, which is easily misread as a permissions
    failure and triggers an OAuth re-consent loop. Catch the mistake at
    the tool boundary with an actionable message that points the agent
    at ``slack_explore_workspace`` to look the ID up. Returns ``None``
    when the value looks like a valid ID.
    """
    if not isinstance(channel_id, str) or not channel_id:
        return "Error: channel_id must be a non-empty Slack channel ID."
    if _SLACK_CHANNEL_ID_PATTERN.fullmatch(channel_id):
        return None
    # Pick the most actionable hint based on what the input looks like. The
    # order matters: a lowercased real-looking ID (e.g. ``c01234abcd``) is a
    # case mistake, not a name lookup.
    upper = channel_id.upper()
    if _SLACK_CHANNEL_ID_PATTERN.fullmatch(upper):
        lookup_clause = f"Slack channel IDs are case-sensitive — retry with {upper!r}. "
    elif (
        channel_id.startswith("#")
        or "-" in channel_id
        or all(c.isalpha() and c.islower() for c in channel_id)
        or channel_id.replace("-", "").replace("_", "").replace(".", "").islower()
    ):
        # Input plausibly IS a channel name — suggest looking up the ID.
        name_hint = channel_id.removeprefix("#")
        lookup_clause = (
            f"Call slack_explore_workspace to look up the ID for #{name_hint}, then retry with the resolved ID. "
        )
    else:
        # Malformed in some other way (wrong prefix letter, too short, etc).
        lookup_clause = "Use slack_explore_workspace to find the correct channel ID and retry. "
    return (
        f"Error: {channel_id!r} is not a valid Slack channel ID. "
        "Slack channel IDs start with C, G, or D followed by uppercase "
        "alphanumerics (e.g. 'C01234ABCD'), not the channel name. "  # pragma: allowlist secret
        + lookup_clause
        + "This is NOT a permissions error — do not call request_app_connection."
    )


def _format_slack_error(verb: str, subject: str | None, error_code: str) -> str:
    """Format a Slack API error for return to the agent.

    For known non-permissions errors (channel/user/message/file not found,
    not in channel, malformed args), append an explicit disclaimer plus a
    pointer at ``slack_explore_workspace`` so the agent does not loop into
    ``request_app_connection``. For everything else, fall back to the bare
    error code so genuine 401/403/scope errors still flow through the
    existing missing-scope path.
    """
    if error_code in _SLACK_NON_PERMISSION_ERRORS:
        target = f"{subject} " if subject else ""
        return (
            f"Failed to {verb}: {error_code} ({target}not found, not visible, "
            "or input is malformed). Verify the IDs you passed with "
            "slack_explore_workspace and retry. "
            "This is NOT a permissions error — do not call request_app_connection."
        )
    return error_code


def _collect_text(obj: object) -> list[str]:
    """Recursively collect human-readable text from a Slack structure.

    Handles both Block Kit — which uses typed ``mrkdwn``/``plain_text``/``text``
    nodes — and legacy attachments, which are flat dicts of raw strings.

    On a typed text node the walker takes ``text`` and stops recursing to
    avoid duplicate fragments. On untyped dicts it first pulls raw strings
    from the known attachment keys, then recurses into remaining values so
    unfamiliar containers are still traversed transparently.
    """
    parts: list[str] = []

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            # Slack JSON decodes to untyped mapping. The ``object`` parameter
            # narrows to bare ``dict`` under isinstance, which the type
            # checker treats as ``dict[Never, Never]``; cast so arbitrary
            # string lookups are accepted.
            typed = cast(dict[str, Any], node)
            if typed.get("type") in _TEXT_NODE_TYPES:
                t = typed.get("text")
                if isinstance(t, str) and t:
                    parts.append(t)
                return

            for key in _RAW_TEXT_KEYS:
                val = typed.get(key)
                if isinstance(val, str) and val:
                    parts.append(val)

            for v in typed.values():
                _walk(v)

        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(obj)
    return parts


def _get_message_text(msg: dict) -> str:
    """Return the best available text for a Slack message.

    Slack's top-level ``text`` is just a short notification fallback when
    the message uses Block Kit or legacy attachments, so agents that only
    read it miss the real content. Priority: blocks, then attachments,
    then the plain ``text`` field.
    """
    for key in ("blocks", "attachments"):
        rich = msg.get(key)
        if rich:
            text = "\n".join(_collect_text(rich))
            if text.strip():
                return text

    # Slack occasionally returns ``text=None`` or omits it entirely for
    # blocks-only messages, which would propagate into ``SlackMessage.text``
    # (declared as ``str``) and fail validation. Coerce non-string fallbacks
    # to the empty string instead.
    fallback_text = msg.get("text")
    return fallback_text if isinstance(fallback_text, str) else ""


def _normalize_users_conversation_types(raw_types: str) -> tuple[str | None, str | None]:
    """Normalize and validate ``users.conversations`` ``types`` CSV input."""
    parsed = parse_csv_ids(raw_types)
    if not parsed:
        return None, "types must include at least one value."

    invalid = sorted({t for t in parsed if t not in _USERS_CONVERSATIONS_ALLOWED_TYPES})
    if invalid:
        allowed = ", ".join(sorted(_USERS_CONVERSATIONS_ALLOWED_TYPES))
        bad = ", ".join(invalid)
        return None, f"Unsupported conversation type(s): {bad}. Allowed values: {allowed}."

    deduped = list(dict.fromkeys(parsed))
    return ",".join(deduped), None


# Allowed base domains for Slack private file download URLs (SSRF prevention).
# Slack serves private files from subdomains of these three domains.
_ALLOWED_SLACK_FILE_DOMAINS = ("slack.com", "slack-files.com", "slack-edge.com")


def _validate_slack_file_url(url: str) -> str | None:
    """Validate that *url* is a legitimate Slack file URL.

    Returns ``None`` if the URL is valid, or an error string if it should be
    rejected.  This prevents SSRF: without this check, an attacker who can
    inject content into a Slack channel could supply an arbitrary URL and
    cause the agent to make authenticated HTTP requests (with the user's Slack
    OAuth token) to internal cloud metadata services or other private hosts.

    Only ``https://`` URLs whose hostname is exactly one of the allowed base
    domains, or a subdomain thereof, are accepted.  The subdomain check uses
    a dot-prefix (``hostname.endswith("." + domain)``) to prevent
    ``evil-slack.com`` from matching ``slack.com``.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return "Invalid URL."

    if parsed.scheme != "https":
        return "Only HTTPS Slack file URLs are supported."

    hostname = (parsed.hostname or "").lower()
    if not any(hostname == domain or hostname.endswith("." + domain) for domain in _ALLOWED_SLACK_FILE_DOMAINS):
        return (
            "URL is not a recognised Slack file host. "
            "Only slack.com, slack-files.com, and slack-edge.com URLs are supported."
        )

    return None


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

    # Slack's conversations.list checks scopes against the union of types in
    # the request: ``public_channel`` requires ``channels:read`` and
    # ``private_channel`` requires ``groups:read``. Combining both in one
    # request means the call 403s with ``missing_scope`` if EITHER scope is
    # absent — so a user with only ``channels:read`` would get zero channels
    # and the agent would loop into request_app_connection. Fetch the two
    # sides separately so a missing scope on one side only loses that side's
    # channels — the agent still gets a usable listing of the other side.
    async def _list_channels_of_type(channel_type: str) -> None:
        cursor: str | None = None
        while True:
            kwargs: dict = {"types": channel_type, "limit": 1000}
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
                return

    with contextlib.suppress(SlackApiError):
        await _list_channels_of_type("public_channel")
    with contextlib.suppress(SlackApiError):
        await _list_channels_of_type("private_channel")

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
    scopes=SCOPES["slack_list_my_conversations"],
    api_docs="https://docs.slack.dev/reference/web-api/users/conversations",
    provider="slack",
)
async def slack_list_my_conversations(
    params: ListMyConversationsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ListMyConversationsResult:
    """List conversations the calling user is a member of."""
    types, type_error = _normalize_users_conversation_types(params.types)
    if type_error:
        return ListMyConversationsResult(success=False, error=type_error)

    client = _client(token, base_url)
    try:
        resp = await client.users_conversations(
            types=types,
            exclude_archived=params.exclude_archived,
            limit=min(params.limit, 1000),
        )
        conversations = [
            SlackConversation(
                id=conversation.get("id", ""),
                name=conversation.get("name", ""),
                is_im=conversation.get("is_im", False),
                is_mpim=conversation.get("is_mpim", False),
                is_private=conversation.get("is_private", False),
                user=conversation.get("user"),
                updated=conversation.get("updated", 0),
            )
            for conversation in resp.get("channels", [])
        ]
        return ListMyConversationsResult(success=True, conversations=conversations)
    except SlackApiError as exc:
        code = exc.response.get("error", str(exc))
        return ListMyConversationsResult(
            success=False,
            error=_format_slack_error("list conversations", None, code),
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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return SendChannelMessageResult(success=False, error=id_error)
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
        code = exc.response.get("error", str(exc))
        return SendChannelMessageResult(
            success=False,
            error=_format_slack_error("send message", f"channel {params.channel_id}", code),
        )


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
        code = exc.response.get("error", str(exc))
        return SendUserMessageResult(
            success=False,
            error=_format_slack_error("send message", f"user {params.user_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return ReadChannelMessagesResult(success=False, error=id_error)
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
                text=_get_message_text(m),
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
        code = exc.response.get("error", str(exc))
        return ReadChannelMessagesResult(
            success=False,
            error=_format_slack_error("read messages", f"channel {params.channel_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return GetChannelInfoResult(success=False, error=id_error)
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
        code = exc.response.get("error", str(exc))
        return GetChannelInfoResult(
            success=False,
            error=_format_slack_error("get channel info", f"channel {params.channel_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return ReadThreadResult(success=False, error=id_error)
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
                text=_get_message_text(m),
                ts=m.get("ts", ""),
                files=m.get("files"),
            )
            for m in raw_messages
        ]

        return ReadThreadResult(success=True, messages=messages, user_map=user_map)
    except SlackApiError as exc:
        code = exc.response.get("error", str(exc))
        return ReadThreadResult(
            success=False,
            error=_format_slack_error("read thread", f"channel {params.channel_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return JoinChannelResult(success=False, error=id_error)
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
        code = exc.response.get("error", str(exc))
        return JoinChannelResult(
            success=False,
            error=_format_slack_error("join channel", f"channel {params.channel_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return EditMessageResult(success=False, error=id_error)
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
        code = exc.response.get("error", str(exc))
        return EditMessageResult(
            success=False,
            error=_format_slack_error("edit message", f"channel {params.channel_id}", code),
        )


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
    if id_error := _validate_slack_channel_id(params.channel_id):
        return GetPermalinkResult(success=False, error=id_error)
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
        code = exc.response.get("error", str(exc))
        return GetPermalinkResult(
            success=False,
            error=_format_slack_error("get permalink", f"channel {params.channel_id}", code),
        )


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
        code = exc.response.get("error", str(exc))
        return GetFileInfoResult(
            success=False,
            error=_format_slack_error("get file info", f"file {params.file_id}", code),
        )


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
    url_error = _validate_slack_file_url(params.url)
    if url_error:
        return DownloadFileResult(success=False, error=f"Failed to download file: {url_error}")

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
    scopes=SCOPES["slack_save_file_for_upload"],
    api_docs="https://docs.slack.dev/reference/web-api/files/info",
    provider="slack",
)
async def slack_save_file_for_upload(
    params: SaveFileForUploadParams,
    *,
    token: str,
    base_url: str = _BASE_URL,  # noqa: ARG001
) -> SaveFileForUploadResult:
    """Download a Slack file and return it as raw bytes for cross-tool upload."""
    from urllib.parse import unquote, urlparse

    url_error = _validate_slack_file_url(params.url)
    if url_error:
        return SaveFileForUploadResult(success=False, error=f"Failed to save file: {url_error}")

    max_bytes = params.max_size_mb * 1024 * 1024
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            head_resp = await client.head(params.url, headers=headers)
            if not head_resp.is_success:
                return SaveFileForUploadResult(
                    success=False,
                    error=f"HEAD request failed with status {head_resp.status_code}",
                )

            content_length_header = head_resp.headers.get("content-length")
            content_length: int | None = None
            if content_length_header is not None:
                try:
                    content_length = int(content_length_header)
                except ValueError:
                    content_length = None

            if content_length is not None and content_length > max_bytes:
                size_mb = content_length / (1024 * 1024)
                return SaveFileForUploadResult(
                    success=False,
                    error=f"File too large: {size_mb:.1f} MB (max {params.max_size_mb} MB).",
                )

            response = await client.get(params.url, headers=headers)
    except httpx.TimeoutException:
        return SaveFileForUploadResult(success=False, error="Request timed out.")
    except httpx.HTTPError as exc:
        return SaveFileForUploadResult(success=False, error=str(exc))

    if not response.is_success:
        return SaveFileForUploadResult(success=False, error=f"HTTP {response.status_code}")

    if len(response.content) > max_bytes:
        size_mb = len(response.content) / (1024 * 1024)
        return SaveFileForUploadResult(
            success=False,
            error=f"File too large: {size_mb:.1f} MB (max {params.max_size_mb} MB).",
        )

    content_type = response.headers.get("content-type", "application/octet-stream")
    mime_type = content_type.split(";")[0].strip()
    filename = unquote(urlparse(params.url).path.rsplit("/", 1)[-1]) or "download"

    return SaveFileForUploadResult(
        success=True,
        data=base64.b64encode(response.content),
        filename=filename,
        mime_type=mime_type,
        size=len(response.content),
    )


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
    if params.channel_id and params.timestamp and (id_error := _validate_slack_channel_id(params.channel_id)):
        return GetReactionsResult(success=False, error=id_error)

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
        code = exc.response.get("error", str(exc))
        subject = f"channel {params.channel_id}" if params.channel_id else None
        return GetReactionsResult(
            success=False,
            error=_format_slack_error("get reactions", subject, code),
        )


@tool(
    scopes=SCOPES["slack_add_reactions"],
    api_docs="https://docs.slack.dev/reference/web-api/reactions/add",
    provider="slack",
)
async def slack_add_reactions(
    params: AddReactionsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> AddReactionsResult:
    """Add the same emoji reaction to one or more Slack messages."""
    if id_error := _validate_slack_channel_id(params.channel_id):
        return AddReactionsResult(success=False, error=id_error)
    normalized = params.reaction_name.strip().strip(":")
    if not normalized:
        return AddReactionsResult(success=False, error="reaction_name must not be empty.")
    if not _REACTION_NAME_PATTERN.fullmatch(normalized):
        return AddReactionsResult(success=False, error="reaction_name contains invalid characters.")

    timestamps = parse_csv_ids(params.timestamps)
    if not timestamps:
        return AddReactionsResult(success=False, error="No timestamps provided.")

    client = _client(token, base_url)
    items: list[AddReactionItem] = []
    for ts in timestamps:
        try:
            await client.reactions_add(
                channel=params.channel_id,
                timestamp=ts,
                name=normalized,
            )
            items.append(AddReactionItem(timestamp=ts, success=True))
        except SlackApiError as exc:
            code = exc.response.get("error", str(exc))
            items.append(
                AddReactionItem(
                    timestamp=ts,
                    success=False,
                    error=_format_slack_error("add reaction", f"channel {params.channel_id}", code),
                )
            )

    return AddReactionsResult(
        success=True,
        reaction_name=normalized,
        channel_id=params.channel_id,
        items=items,
    )
