"""Tests for Microsoft Teams provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

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

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreWorkspaceParams:
    def test_defaults(self):
        params = ExploreWorkspaceParams()
        assert params is not None


class TestGetChannelInfoParams:
    def test_required(self):
        params = GetChannelInfoParams(team_id="team-001", channel_id="channel-001")
        assert params.team_id == "team-001"
        assert params.channel_id == "channel-001"


class TestListChatsParams:
    def test_defaults(self):
        params = ListChatsParams()
        assert params.limit == 25

    def test_custom(self):
        params = ListChatsParams(limit=10)
        assert params.limit == 10


class TestReadChatMessagesParams:
    def test_required(self):
        params = ReadChatMessagesParams(chat_id="chat-001")
        assert params.chat_id == "chat-001"
        assert params.limit == 20

    def test_custom(self):
        params = ReadChatMessagesParams(chat_id="chat-001", limit=5)
        assert params.limit == 5


class TestReadChannelMessagesParams:
    def test_required(self):
        params = ReadChannelMessagesParams(team_id="team-001", channel_id="channel-001")
        assert params.team_id == "team-001"
        assert params.channel_id == "channel-001"
        assert params.limit == 20


class TestReadMessageRepliesParams:
    def test_required(self):
        params = ReadMessageRepliesParams(
            team_id="team-001",
            channel_id="channel-001",
            message_id="msg-001",
        )
        assert params.team_id == "team-001"
        assert params.channel_id == "channel-001"
        assert params.message_id == "msg-001"


class TestSendChatMessageParams:
    def test_required(self):
        params = SendChatMessageParams(chat_id="chat-001", message="Hello!")
        assert params.chat_id == "chat-001"
        assert params.message == "Hello!"


class TestSendChannelMessageParams:
    def test_required(self):
        params = SendChannelMessageParams(
            team_id="team-001",
            channel_id="channel-001",
            message="Hello!",
        )
        assert params.team_id == "team-001"
        assert params.channel_id == "channel-001"
        assert params.message == "Hello!"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestTeamInfo:
    def test_parse_from_api(self):
        data = _load_json("joined_teams.json")
        team = TeamInfo.model_validate(data["value"][0])
        assert team.id == "team-001"
        assert team.display_name == "Engineering"
        assert team.description == "Engineering team for product development"
        assert team.is_archived is False


class TestChannelInfo:
    def test_parse_from_api(self):
        data = _load_json("channels.json")
        channel = ChannelInfo.model_validate(data["value"][0])
        assert channel.id == "channel-001"
        assert channel.display_name == "General"
        assert channel.membership_type == "standard"


class TestMemberInfo:
    def test_parse_from_api(self):
        data = _load_json("members.json")
        member = MemberInfo.model_validate(data["value"][0])
        assert member.id == "member-001"
        assert member.display_name == "Alice Smith"
        assert member.user_id == "user-001"
        assert member.email == "alice@example.com"
        assert member.roles == ["owner"]


class TestChatInfo:
    def test_parse_from_api(self):
        data = _load_json("list_chats.json")
        chat = ChatInfo.model_validate(data["value"][0])
        assert chat.id == "chat-001"
        assert chat.chat_type == "oneOnOne"
        assert chat.topic is None

    def test_group_chat(self):
        data = _load_json("list_chats.json")
        chat = ChatInfo.model_validate(data["value"][1])
        assert chat.id == "chat-002"
        assert chat.chat_type == "group"
        assert chat.topic == "Project Planning"


class TestMessageInfo:
    def test_parse_from_api(self):
        data = _load_json("chat_messages.json")
        msg = MessageInfo.model_validate(data["value"][0])
        assert msg.id == "msg-001"
        assert msg.body.content == "Hello team, any updates on the sprint?"
        assert msg.from_ is not None
        assert msg.from_.user is not None
        assert msg.from_.user.display_name == "Alice Smith"
        assert msg.importance == "normal"


# ---------------------------------------------------------------------------
# ExploreWorkspaceResult
# ---------------------------------------------------------------------------


class TestExploreWorkspaceResult:
    def test_success(self):
        teams_data = _load_json("joined_teams.json")
        channels_data = _load_json("channels.json")
        members_data = _load_json("members.json")

        team = TeamInfo.model_validate(teams_data["value"][0])
        channels = [ChannelInfo.model_validate(c) for c in channels_data["value"]]
        members = [MemberInfo.model_validate(m) for m in members_data["value"]]

        result = ExploreWorkspaceResult(
            success=True,
            teams=[TeamWorkspaceEntry(team=team, channels=channels, members=members)],
        )
        assert result.success is True
        assert len(result.teams) == 1
        assert result.teams[0].team.display_name == "Engineering"

    def test_str_output(self):
        team = TeamInfo(id="team-001", display_name="Engineering")
        channel = ChannelInfo(id="channel-001", display_name="General")
        member = MemberInfo(id="member-001", display_name="Alice Smith")

        result = ExploreWorkspaceResult(
            success=True,
            teams=[TeamWorkspaceEntry(team=team, channels=[channel], members=[member])],
        )
        text = str(result)
        assert "1 team(s)" in text
        assert "Engineering" in text
        assert "#General" in text
        assert "@Alice Smith" in text

    def test_str_empty(self):
        result = ExploreWorkspaceResult(success=True, teams=[])
        assert str(result) == "No teams found."

    def test_str_on_error(self):
        result = ExploreWorkspaceResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


# ---------------------------------------------------------------------------
# GetChannelInfoResult
# ---------------------------------------------------------------------------


class TestGetChannelInfoResult:
    def test_success(self):
        data = _load_json("get_channel.json")
        channel = ChannelInfo.model_validate(data)
        result = GetChannelInfoResult(success=True, channel=channel)
        assert result.success is True
        assert result.channel is not None
        assert result.channel.display_name == "General"

    def test_str_output(self):
        channel = ChannelInfo(
            id="channel-001",
            display_name="General",
            description="General discussion channel",
            membership_type="standard",
        )
        result = GetChannelInfoResult(success=True, channel=channel)
        text = str(result)
        assert "General" in text
        assert "General discussion channel" in text
        assert "standard" in text

    def test_str_on_error(self):
        result = GetChannelInfoResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_no_channel(self):
        result = GetChannelInfoResult(success=True, channel=None)
        assert str(result) == "No channel information."


# ---------------------------------------------------------------------------
# ListChatsResult
# ---------------------------------------------------------------------------


class TestListChatsResult:
    def test_parse(self):
        data = _load_json("list_chats.json")
        chats = [ChatInfo.model_validate(c) for c in data["value"]]
        result = ListChatsResult(success=True, chats=chats)
        assert result.success is True
        assert len(result.chats) == 2

    def test_str_output(self):
        data = _load_json("list_chats.json")
        chats = [ChatInfo.model_validate(c) for c in data["value"]]
        result = ListChatsResult(success=True, chats=chats)
        text = str(result)
        assert "2 chat(s)" in text
        assert "Project Planning" in text

    def test_str_empty(self):
        result = ListChatsResult(success=True, chats=[])
        assert str(result) == "No chats found."

    def test_str_on_error(self):
        result = ListChatsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# ReadChatMessagesResult
# ---------------------------------------------------------------------------


class TestReadChatMessagesResult:
    def test_parse(self):
        data = _load_json("chat_messages.json")
        messages = [MessageInfo.model_validate(m) for m in data["value"]]
        result = ReadChatMessagesResult(success=True, messages=messages)
        assert result.success is True
        assert len(result.messages) == 2

    def test_str_output(self):
        data = _load_json("chat_messages.json")
        messages = [MessageInfo.model_validate(m) for m in data["value"]]
        result = ReadChatMessagesResult(success=True, messages=messages)
        text = str(result)
        assert "2 message(s)" in text
        assert "Alice Smith" in text

    def test_str_empty(self):
        result = ReadChatMessagesResult(success=True, messages=[])
        assert str(result) == "No messages found."

    def test_str_on_error(self):
        result = ReadChatMessagesResult(success=False, error="Bad request")
        assert str(result) == "Error: Bad request"


# ---------------------------------------------------------------------------
# ReadChannelMessagesResult
# ---------------------------------------------------------------------------


class TestReadChannelMessagesResult:
    def test_parse(self):
        data = _load_json("channel_messages.json")
        messages = [MessageInfo.model_validate(m) for m in data["value"]]
        result = ReadChannelMessagesResult(success=True, messages=messages)
        assert result.success is True
        assert len(result.messages) == 2

    def test_str_output(self):
        data = _load_json("channel_messages.json")
        messages = [MessageInfo.model_validate(m) for m in data["value"]]
        result = ReadChannelMessagesResult(success=True, messages=messages)
        text = str(result)
        assert "2 message(s)" in text
        assert "Bob Jones" in text

    def test_str_empty(self):
        result = ReadChannelMessagesResult(success=True, messages=[])
        assert str(result) == "No messages found."

    def test_str_on_error(self):
        result = ReadChannelMessagesResult(success=False, error="Timeout")
        assert str(result) == "Error: Timeout"


# ---------------------------------------------------------------------------
# ReadMessageRepliesResult
# ---------------------------------------------------------------------------


class TestReadMessageRepliesResult:
    def test_parse(self):
        parent_data = _load_json("parent_message.json")
        replies_data = _load_json("message_replies.json")
        parent = MessageInfo.model_validate(parent_data)
        replies = [MessageInfo.model_validate(r) for r in replies_data["value"]]

        result = ReadMessageRepliesResult(success=True, parent=parent, replies=replies)
        assert result.success is True
        assert result.parent is not None
        assert len(result.replies) == 2

    def test_str_output(self):
        parent_data = _load_json("parent_message.json")
        replies_data = _load_json("message_replies.json")
        parent = MessageInfo.model_validate(parent_data)
        replies = [MessageInfo.model_validate(r) for r in replies_data["value"]]

        result = ReadMessageRepliesResult(success=True, parent=parent, replies=replies)
        text = str(result)
        assert "Alice Smith" in text
        assert "2 reply/replies" in text
        assert "Bob Jones" in text

    def test_str_no_replies(self):
        parent_data = _load_json("parent_message.json")
        parent = MessageInfo.model_validate(parent_data)
        result = ReadMessageRepliesResult(success=True, parent=parent, replies=[])
        text = str(result)
        assert "No replies found." in text

    def test_str_on_error(self):
        result = ReadMessageRepliesResult(success=False, error="API error")
        assert str(result) == "Error: API error"


# ---------------------------------------------------------------------------
# SendChatMessageResult
# ---------------------------------------------------------------------------


class TestSendChatMessageResult:
    def test_success(self):
        result = SendChatMessageResult(success=True, message_id="msg-003")
        assert result.success is True
        assert result.message_id == "msg-003"

    def test_str_output(self):
        result = SendChatMessageResult(success=True, message_id="msg-003")
        text = str(result)
        assert "msg-003" in text
        assert "sent successfully" in text

    def test_str_on_error(self):
        result = SendChatMessageResult(success=False, error="Rate limited")
        assert str(result) == "Error: Rate limited"


# ---------------------------------------------------------------------------
# SendChannelMessageResult
# ---------------------------------------------------------------------------


class TestSendChannelMessageResult:
    def test_success(self):
        result = SendChannelMessageResult(success=True, message_id="msg-003")
        assert result.success is True
        assert result.message_id == "msg-003"

    def test_str_output(self):
        result = SendChannelMessageResult(success=True, message_id="msg-003")
        text = str(result)
        assert "msg-003" in text
        assert "sent to channel" in text

    def test_str_on_error(self):
        result = SendChannelMessageResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"
