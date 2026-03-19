"""Microsoft Teams tool functions for interacting with the Microsoft Graph API."""

from __future__ import annotations

import httpx

from any_tool.providers.microsoft.teams.types import (
    ChannelInfo,
    ChatInfo,
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetChannelInfoParams,
    GetChannelInfoResult,
    ListChatsParams,
    ListChatsResult,
    MemberInfo,
    MessageInfo,
    ReadChannelMessagesParams,
    ReadChannelMessagesResult,
    ReadChatMessagesParams,
    ReadChatMessagesResult,
    ReadMessageRepliesParams,
    ReadMessageRepliesResult,
    SendChannelMessageParams,
    SendChannelMessageResult,
    SendChatMessageParams,
    SendChatMessageResult,
    TeamInfo,
    TeamWorkspaceEntry,
)
from any_tool.tool import tool

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


@tool(
    scopes=SCOPES["microsoft_teams_explore_workspace"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/user-list-joinedteams",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_explore_workspace(
    params: ExploreWorkspaceParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ExploreWorkspaceResult:
    """Explore the Microsoft Teams workspace structure including teams, channels, and members."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/joinedTeams",
                headers=_headers(token),
            )
            if not resp.is_success:
                return ExploreWorkspaceResult(
                    success=False,
                    error=f"Graph API error {resp.status_code}: {resp.text}",
                )

            teams_data = resp.json().get("value", [])
            entries: list[TeamWorkspaceEntry] = []

            for team_raw in teams_data:
                team = TeamInfo.model_validate(team_raw)

                # Fetch channels for the team.
                ch_resp = await client.get(
                    f"{base_url}/teams/{team.id}/channels",
                    headers=_headers(token),
                )
                channels: list[ChannelInfo] = []
                if ch_resp.is_success:
                    channels = [ChannelInfo.model_validate(c) for c in ch_resp.json().get("value", [])]

                # Fetch members for the team.
                mem_resp = await client.get(
                    f"{base_url}/teams/{team.id}/members",
                    headers=_headers(token),
                )
                members: list[MemberInfo] = []
                if mem_resp.is_success:
                    members = [MemberInfo.model_validate(m) for m in mem_resp.json().get("value", [])]

                entries.append(
                    TeamWorkspaceEntry(
                        team=team,
                        channels=channels,
                        members=members,
                    )
                )

    except httpx.HTTPError as exc:
        return ExploreWorkspaceResult(success=False, error=str(exc))

    return ExploreWorkspaceResult(success=True, teams=entries)


@tool(
    scopes=SCOPES["microsoft_teams_get_channel_info"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/channel-get",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_get_channel_info(
    params: GetChannelInfoParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> GetChannelInfoResult:
    """Get information about a specific Microsoft Teams channel."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/teams/{params.team_id}/channels/{params.channel_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetChannelInfoResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetChannelInfoResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    channel = ChannelInfo.model_validate(resp.json())
    return GetChannelInfoResult(success=True, channel=channel)


@tool(
    scopes=SCOPES["microsoft_teams_list_chats"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/chat-list",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_list_chats(
    params: ListChatsParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListChatsResult:
    """List all chats the authenticated user is part of."""
    limit = min(params.limit, 50)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/chats",
                headers=_headers(token),
                params={"$top": limit},
            )
    except httpx.HTTPError as exc:
        return ListChatsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListChatsResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    chats = [ChatInfo.model_validate(c) for c in resp.json().get("value", [])]
    return ListChatsResult(success=True, chats=chats)


@tool(
    scopes=SCOPES["microsoft_teams_read_chat_messages"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/chat-list-messages",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_read_chat_messages(
    params: ReadChatMessagesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadChatMessagesResult:
    """Read messages from a 1:1 or group chat."""
    limit = min(params.limit, 50)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/chats/{params.chat_id}/messages",
                headers=_headers(token),
                params={"$top": limit},
            )
    except httpx.HTTPError as exc:
        return ReadChatMessagesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadChatMessagesResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    messages = [MessageInfo.model_validate(m) for m in resp.json().get("value", [])]
    return ReadChatMessagesResult(success=True, messages=messages)


@tool(
    scopes=SCOPES["microsoft_teams_read_channel_messages"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/channel-list-messages",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_read_channel_messages(
    params: ReadChannelMessagesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadChannelMessagesResult:
    """Read recent messages from a Microsoft Teams channel."""
    limit = min(params.limit, 50)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/teams/{params.team_id}/channels/{params.channel_id}/messages",
                headers=_headers(token),
                params={"$top": limit},
            )
    except httpx.HTTPError as exc:
        return ReadChannelMessagesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadChannelMessagesResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    messages = [MessageInfo.model_validate(m) for m in resp.json().get("value", [])]
    return ReadChannelMessagesResult(success=True, messages=messages)


@tool(
    scopes=SCOPES["microsoft_teams_read_message_replies"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/chatmessage-list-replies",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_read_message_replies(
    params: ReadMessageRepliesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadMessageRepliesResult:
    """Read replies to a channel message thread."""
    base_path = f"{base_url}/teams/{params.team_id}/channels/{params.channel_id}/messages/{params.message_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the parent message.
            parent_resp = await client.get(
                base_path,
                headers=_headers(token),
            )
            if not parent_resp.is_success:
                return ReadMessageRepliesResult(
                    success=False,
                    error=f"Graph API error {parent_resp.status_code}: {parent_resp.text}",
                )

            parent = MessageInfo.model_validate(parent_resp.json())

            # Fetch the replies.
            replies_resp = await client.get(
                f"{base_path}/replies",
                headers=_headers(token),
            )
            if not replies_resp.is_success:
                return ReadMessageRepliesResult(
                    success=False,
                    error=f"Graph API error {replies_resp.status_code}: {replies_resp.text}",
                )

            replies = [MessageInfo.model_validate(r) for r in replies_resp.json().get("value", [])]

    except httpx.HTTPError as exc:
        return ReadMessageRepliesResult(success=False, error=str(exc))

    return ReadMessageRepliesResult(success=True, parent=parent, replies=replies)


@tool(
    scopes=SCOPES["microsoft_teams_send_chat_message"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/chat-post-messages",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_send_chat_message(
    params: SendChatMessageParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SendChatMessageResult:
    """Send a message in a 1:1 or group chat."""
    body = {"body": {"content": params.message}}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/me/chats/{params.chat_id}/messages",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return SendChatMessageResult(success=False, error=str(exc))

    if not resp.is_success:
        return SendChatMessageResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return SendChatMessageResult(success=True, message_id=data.get("id", ""))


@tool(
    scopes=SCOPES["microsoft_teams_send_channel_message"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/channel-post-messages",
    provider="microsoft",
    service="microsoft_teams",
)
async def microsoft_teams_send_channel_message(
    params: SendChannelMessageParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SendChannelMessageResult:
    """Send a message to a Microsoft Teams channel."""
    body = {"body": {"content": params.message}}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/teams/{params.team_id}/channels/{params.channel_id}/messages",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return SendChannelMessageResult(success=False, error=str(exc))

    if not resp.is_success:
        return SendChannelMessageResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return SendChannelMessageResult(success=True, message_id=data.get("id", ""))
