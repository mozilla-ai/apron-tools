"""Tests for Microsoft Teams tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.teams.tools import (
    microsoft_teams_explore_workspace,
    microsoft_teams_get_channel_info,
    microsoft_teams_list_chats,
    microsoft_teams_read_channel_messages,
    microsoft_teams_read_chat_messages,
    microsoft_teams_read_message_replies,
    microsoft_teams_send_channel_message,
    microsoft_teams_send_chat_message,
)
from apron_tools.providers.microsoft.teams.types import (
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetChannelInfoParams,
    GetChannelInfoResult,
    ListChatsParams,
    ListChatsResult,
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
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TEAM_ID = "team-001"
_CHANNEL_ID = "channel-001"
_CHAT_ID = "chat-001"
_MESSAGE_ID = "msg-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# explore_workspace
# ---------------------------------------------------------------------------


class TestExploreWorkspace:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/joinedTeams",
            json=_load_json("joined_teams.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/team-001/channels",
            json=_load_json("channels.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/team-001/members",
            json=_load_json("members.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/team-002/channels",
            json={"value": []},
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/team-002/members",
            json={"value": []},
        )

        result = await microsoft_teams_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN)

        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True
        assert len(result.teams) == 2
        assert result.teams[0].team.display_name == "Engineering"
        assert len(result.teams[0].channels) == 2
        assert len(result.teams[0].members) == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await microsoft_teams_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN)

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_explore_workspace._tool_definition
        assert defn.name == "microsoft_teams_explore_workspace"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "Team.ReadBasic.All" in defn.scopes


# ---------------------------------------------------------------------------
# get_channel_info
# ---------------------------------------------------------------------------


class TestGetChannelInfo:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}",
            json=_load_json("get_channel.json"),
        )

        result = await microsoft_teams_get_channel_info(
            GetChannelInfoParams(team_id=_TEAM_ID, channel_id=_CHANNEL_ID),
            token=_TOKEN,
        )

        assert isinstance(result, GetChannelInfoResult)
        assert result.success is True
        assert result.channel is not None
        assert result.channel.display_name == "General"
        assert result.channel.membership_type == "standard"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_teams_get_channel_info(
            GetChannelInfoParams(team_id="bad-id", channel_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_get_channel_info._tool_definition
        assert defn.name == "microsoft_teams_get_channel_info"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "Channel.ReadBasic.All" in defn.scopes


# ---------------------------------------------------------------------------
# list_chats
# ---------------------------------------------------------------------------


class TestListChats:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/chats?%24top=25",
            json=_load_json("list_chats.json"),
        )

        result = await microsoft_teams_list_chats(ListChatsParams(), token=_TOKEN)

        assert isinstance(result, ListChatsResult)
        assert result.success is True
        assert len(result.chats) == 2
        assert result.chats[0].chat_type == "oneOnOne"
        assert result.chats[1].topic == "Project Planning"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await microsoft_teams_list_chats(ListChatsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_list_chats._tool_definition
        assert defn.name == "microsoft_teams_list_chats"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "Chat.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_chat_messages
# ---------------------------------------------------------------------------


class TestReadChatMessages:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/chats/{_CHAT_ID}/messages?%24top=20",
            json=_load_json("chat_messages.json"),
        )

        result = await microsoft_teams_read_chat_messages(
            ReadChatMessagesParams(chat_id=_CHAT_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadChatMessagesResult)
        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[0].body.content == "Hello team, any updates on the sprint?"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_teams_read_chat_messages(
            ReadChatMessagesParams(chat_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_read_chat_messages._tool_definition
        assert defn.name == "microsoft_teams_read_chat_messages"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "Chat.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_channel_messages
# ---------------------------------------------------------------------------


class TestReadChannelMessages:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages?%24top=20",
            json=_load_json("channel_messages.json"),
        )

        result = await microsoft_teams_read_channel_messages(
            ReadChannelMessagesParams(team_id=_TEAM_ID, channel_id=_CHANNEL_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadChannelMessagesResult)
        assert result.success is True
        assert len(result.messages) == 2
        assert result.messages[1].from_ is not None
        assert result.messages[1].from_.user is not None
        assert result.messages[1].from_.user.display_name == "Bob Jones"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await microsoft_teams_read_channel_messages(
            ReadChannelMessagesParams(team_id="bad-id", channel_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_read_channel_messages._tool_definition
        assert defn.name == "microsoft_teams_read_channel_messages"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "ChannelMessage.Read.All" in defn.scopes


# ---------------------------------------------------------------------------
# read_message_replies
# ---------------------------------------------------------------------------


class TestReadMessageReplies:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages/{_MESSAGE_ID}",
            json=_load_json("parent_message.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages/{_MESSAGE_ID}/replies",
            json=_load_json("message_replies.json"),
        )

        result = await microsoft_teams_read_message_replies(
            ReadMessageRepliesParams(
                team_id=_TEAM_ID,
                channel_id=_CHANNEL_ID,
                message_id=_MESSAGE_ID,
            ),
            token=_TOKEN,
        )

        assert isinstance(result, ReadMessageRepliesResult)
        assert result.success is True
        assert result.parent is not None
        assert result.parent.id == "msg-001"
        assert len(result.replies) == 2
        assert result.replies[0].from_ is not None
        assert result.replies[0].from_.user is not None
        assert result.replies[0].from_.user.display_name == "Bob Jones"

    async def test_parent_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_teams_read_message_replies(
            ReadMessageRepliesParams(
                team_id="bad-id",
                channel_id="bad-id",
                message_id="bad-id",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_replies_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages/{_MESSAGE_ID}",
            json=_load_json("parent_message.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages/{_MESSAGE_ID}/replies",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_teams_read_message_replies(
            ReadMessageRepliesParams(
                team_id=_TEAM_ID,
                channel_id=_CHANNEL_ID,
                message_id=_MESSAGE_ID,
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_read_message_replies._tool_definition
        assert defn.name == "microsoft_teams_read_message_replies"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "ChannelMessage.Read.All" in defn.scopes


# ---------------------------------------------------------------------------
# send_chat_message
# ---------------------------------------------------------------------------


class TestSendChatMessage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/chats/{_CHAT_ID}/messages",
            json=_load_json("send_message.json"),
        )

        result = await microsoft_teams_send_chat_message(
            SendChatMessageParams(chat_id=_CHAT_ID, message="Hello everyone!"),
            token=_TOKEN,
        )

        assert isinstance(result, SendChatMessageResult)
        assert result.success is True
        assert result.message_id == "msg-003"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await microsoft_teams_send_chat_message(
            SendChatMessageParams(chat_id="bad-id", message="Hello"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_send_chat_message._tool_definition
        assert defn.name == "microsoft_teams_send_chat_message"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "Chat.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# send_channel_message
# ---------------------------------------------------------------------------


class TestSendChannelMessage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/teams/{_TEAM_ID}/channels/{_CHANNEL_ID}/messages",
            json=_load_json("send_message.json"),
        )

        result = await microsoft_teams_send_channel_message(
            SendChannelMessageParams(
                team_id=_TEAM_ID,
                channel_id=_CHANNEL_ID,
                message="Hello everyone!",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, SendChannelMessageResult)
        assert result.success is True
        assert result.message_id == "msg-003"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await microsoft_teams_send_channel_message(
            SendChannelMessageParams(
                team_id="bad-id",
                channel_id="bad-id",
                message="Hello",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_teams_send_channel_message._tool_definition
        assert defn.name == "microsoft_teams_send_channel_message"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_teams"
        assert "ChannelMessage.Send" in defn.scopes
