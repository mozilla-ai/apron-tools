"""Tests for Slack provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

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

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreWorkspaceParams:
    def test_no_params(self):
        params = ExploreWorkspaceParams()
        assert params is not None


class TestSendChannelMessageParams:
    def test_required_fields(self):
        params = SendChannelMessageParams(channel_id="C012AB3CD", message="hello")
        assert params.channel_id == "C012AB3CD"
        assert params.message == "hello"
        assert params.thread_ts is None

    def test_with_thread(self):
        params = SendChannelMessageParams(channel_id="C012AB3CD", message="reply", thread_ts="1503435956.000247")
        assert params.thread_ts == "1503435956.000247"


class TestSendUserMessageParams:
    def test_required_fields(self):
        params = SendUserMessageParams(user_id="U012A3CDE", message="hi there")
        assert params.user_id == "U012A3CDE"
        assert params.message == "hi there"


class TestReadChannelMessagesParams:
    def test_defaults(self):
        params = ReadChannelMessagesParams(channel_id="C012AB3CD")
        assert params.channel_id == "C012AB3CD"
        assert params.limit == 20
        assert params.oldest is None
        assert params.latest is None

    def test_custom_values(self):
        params = ReadChannelMessagesParams(channel_id="C012AB3CD", limit=50, oldest="1512085950.000100")
        assert params.limit == 50
        assert params.oldest == "1512085950.000100"


class TestGetChannelInfoParams:
    def test_required_field(self):
        params = GetChannelInfoParams(channel_id="C012AB3CD")
        assert params.channel_id == "C012AB3CD"


class TestReadThreadParams:
    def test_required_fields(self):
        params = ReadThreadParams(channel_id="C012AB3CD", thread_ts="1512085950.000216")
        assert params.channel_id == "C012AB3CD"
        assert params.thread_ts == "1512085950.000216"


class TestJoinChannelParams:
    def test_required_field(self):
        params = JoinChannelParams(channel_id="C012AB3CD")
        assert params.channel_id == "C012AB3CD"


class TestEditMessageParams:
    def test_required_fields(self):
        params = EditMessageParams(channel_id="C012AB3CD", message_ts="1503435956.000247", new_text="updated")
        assert params.channel_id == "C012AB3CD"
        assert params.message_ts == "1503435956.000247"
        assert params.new_text == "updated"


class TestGetPermalinkParams:
    def test_required_fields(self):
        params = GetPermalinkParams(channel_id="C012AB3CD", message_ts="1503435956.000247")
        assert params.channel_id == "C012AB3CD"
        assert params.message_ts == "1503435956.000247"


class TestGetFileInfoParams:
    def test_required_field(self):
        params = GetFileInfoParams(file_id="F0S43PZDF")
        assert params.file_id == "F0S43PZDF"


class TestDownloadFileParams:
    def test_defaults(self):
        params = DownloadFileParams(url="https://files.slack.com/example")
        assert params.url == "https://files.slack.com/example"
        assert params.max_size_mb == 10


class TestGetReactionsParams:
    def test_message_params(self):
        params = GetReactionsParams(channel_id="C012AB3CD", timestamp="1512085950.000216")
        assert params.channel_id == "C012AB3CD"
        assert params.timestamp == "1512085950.000216"
        assert params.full is False

    def test_file_params(self):
        params = GetReactionsParams(file_id="F0S43PZDF")
        assert params.file_id == "F0S43PZDF"


class TestAddReactionsParams:
    def test_required_fields(self):
        params = AddReactionsParams(
            channel_id="C012AB3CD",
            timestamps="1512085950.000216",
            reaction_name="thumbsup",
        )
        assert params.channel_id == "C012AB3CD"
        assert params.reaction_name == "thumbsup"
        assert params.timestamps == "1512085950.000216"

    def test_csv_input(self):
        params = AddReactionsParams(
            channel_id="C012AB3CD",
            timestamps="1512085950.000216,1512085951.000217",
            reaction_name="thumbsup",
        )
        assert params.timestamps == "1512085950.000216,1512085951.000217"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestSlackChannel:
    def test_parse_from_api_data(self):
        data = _load_json("conversations_list.json")
        ch_data = data["channels"][0]
        channel = SlackChannel.model_validate(ch_data)
        assert channel.id == "C012AB3CD"
        assert channel.name == "general"
        assert channel.is_private is False
        assert channel.num_members == 4

    def test_extra_fields_ignored(self):
        data = _load_json("conversations_list.json")
        ch_data = data["channels"][0]
        channel = SlackChannel.model_validate(ch_data)
        assert not hasattr(channel, "is_channel")


class TestSlackUser:
    def test_parse_from_api_data(self):
        data = _load_json("users_list.json")
        u_data = data["members"][0]
        user = SlackUser.model_validate(u_data)
        assert user.id == "W012A3CDE"
        assert user.name == "spengler"
        assert user.deleted is False

    def test_extra_fields_ignored(self):
        data = _load_json("users_list.json")
        u_data = data["members"][0]
        user = SlackUser.model_validate(u_data)
        assert not hasattr(user, "is_admin")


class TestSlackMessage:
    def test_parse_from_api_data(self):
        data = _load_json("conversations_history.json")
        m_data = data["messages"][0]
        msg = SlackMessage.model_validate(m_data)
        assert msg.user == "W012A3CDE"
        assert msg.ts == "1512085950.000216"
        assert msg.reply_count == 2

    def test_message_without_reply_count(self):
        data = _load_json("conversations_history.json")
        m_data = data["messages"][1]
        msg = SlackMessage.model_validate(m_data)
        assert msg.reply_count is None


class TestSlackReaction:
    def test_parse_from_api_data(self):
        data = _load_json("reactions_get.json")
        r_data = data["message"]["reactions"][0]
        reaction = SlackReaction.model_validate(r_data)
        assert reaction.name == "laughing"
        assert reaction.count == 2
        assert reaction.users == ["W012A3CDE", "W07QCRPA4"]


class TestSlackFile:
    def test_parse_from_api_data(self):
        data = _load_json("files_info.json")
        f_data = data["file"]
        slack_file = SlackFile.model_validate(f_data)
        assert slack_file.id == "F0S43PZDF"
        assert slack_file.name == "tedair.gif"
        assert slack_file.mimetype == "image/gif"
        assert slack_file.size == 137531
        assert slack_file.pretty_type == "GIF"
        assert "download" in slack_file.url_private_download


# ---------------------------------------------------------------------------
# ExploreWorkspaceResult
# ---------------------------------------------------------------------------


class TestExploreWorkspaceResult:
    def test_str_output(self):
        result = ExploreWorkspaceResult(
            success=True,
            workspace_name="My Team",
            channels=[
                SlackChannel(id="C012AB3CD", name="general", num_members=4),
                SlackChannel(id="C061EG9T2", name="random", num_members=4),
            ],
            users=[
                SlackUser(id="W012A3CDE", name="spengler", real_name="Egon Spengler"),
                SlackUser(id="W07QCRPA4", name="glinda", real_name="Glinda Southgood"),
            ],
        )
        text = str(result)
        assert "# My Team" in text
        assert "general (C012AB3CD)" in text
        assert "random (C061EG9T2)" in text
        assert "Egon Spengler (W012A3CDE)" in text
        assert "Glinda Southgood (W07QCRPA4)" in text

    def test_str_on_error(self):
        result = ExploreWorkspaceResult(success=False, error="invalid_auth")
        assert str(result) == "Error: invalid_auth"

    def test_deleted_users_excluded_from_str(self):
        result = ExploreWorkspaceResult(
            success=True,
            workspace_name="Test",
            users=[
                SlackUser(id="U1", name="active", real_name="Active User"),
                SlackUser(id="U2", name="deleted", real_name="Deleted User", deleted=True),
            ],
        )
        text = str(result)
        assert "Active User" in text
        assert "Deleted User" not in text


# ---------------------------------------------------------------------------
# SendChannelMessageResult
# ---------------------------------------------------------------------------


class TestSendChannelMessageResult:
    def test_parse_api_response(self):
        data = _load_json("chat_post_message.json")
        result = SendChannelMessageResult.model_validate(data)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.ts == "1503435956.000247"

    def test_str_output(self):
        data = _load_json("chat_post_message.json")
        result = SendChannelMessageResult.model_validate(data)
        text = str(result)
        assert "C012AB3CD" in text
        assert "1503435956.000247" in text

    def test_str_on_error(self):
        result = SendChannelMessageResult(success=False, error="channel_not_found")
        assert str(result) == "Error: channel_not_found"


# ---------------------------------------------------------------------------
# SendUserMessageResult
# ---------------------------------------------------------------------------


class TestSendUserMessageResult:
    def test_parse_api_response(self):
        data = _load_json("chat_post_message.json")
        result = SendUserMessageResult.model_validate(data)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.ts == "1503435956.000247"

    def test_str_on_error(self):
        result = SendUserMessageResult(success=False, error="user_not_found")
        assert str(result) == "Error: user_not_found"


# ---------------------------------------------------------------------------
# ReadChannelMessagesResult
# ---------------------------------------------------------------------------


class TestReadChannelMessagesResult:
    def test_str_output(self):
        messages = [
            SlackMessage(user="W012A3CDE", text="Hello", ts="1512085950.000100"),
            SlackMessage(user="W07QCRPA4", text="Hi!", ts="1512085950.000200", reply_count=3),
        ]
        result = ReadChannelMessagesResult(
            success=True,
            messages=messages,
            user_map={"W012A3CDE": "spengler", "W07QCRPA4": "Glinda"},
        )
        text = str(result)
        assert "spengler: Hello" in text
        assert "[3 replies]" in text
        assert "ts:1512085950.000100" in text

    def test_str_empty(self):
        result = ReadChannelMessagesResult(success=True, messages=[])
        assert str(result) == "No messages found."

    def test_str_on_error(self):
        result = ReadChannelMessagesResult(success=False, error="channel_not_found")
        assert str(result) == "Error: channel_not_found"

    def test_str_with_files(self):
        messages = [
            SlackMessage(
                user="U1",
                text="See attached",
                ts="123.456",
                files=[{"id": "F123", "name": "doc.pdf"}],
            ),
        ]
        result = ReadChannelMessagesResult(success=True, messages=messages, user_map={})
        text = str(result)
        assert '[Files: F123 "doc.pdf"]' in text


# ---------------------------------------------------------------------------
# GetChannelInfoResult
# ---------------------------------------------------------------------------


class TestGetChannelInfoResult:
    def test_str_output(self):
        result = GetChannelInfoResult(
            success=True,
            channel=SlackChannel(id="C012AB3CD", name="general", num_members=4),
            topic="Company-wide announcements",
            purpose="Team communication",
        )
        text = str(result)
        assert "Name: general" in text
        assert "Type: Public" in text
        assert "Members: 4" in text
        assert "Topic: Company-wide announcements" in text
        assert "Purpose: Team communication" in text

    def test_str_private_channel(self):
        result = GetChannelInfoResult(
            success=True,
            channel=SlackChannel(id="G012AB3CD", name="secret", is_private=True, num_members=2),
        )
        text = str(result)
        assert "Type: Private" in text

    def test_str_on_error(self):
        result = GetChannelInfoResult(success=False, error="channel_not_found")
        assert str(result) == "Error: channel_not_found"


# ---------------------------------------------------------------------------
# ReadThreadResult
# ---------------------------------------------------------------------------


class TestReadThreadResult:
    def test_str_output(self):
        messages = [
            SlackMessage(user="W012A3CDE", text="Parent message", ts="1512085950.000216"),
            SlackMessage(user="W07QCRPA4", text="Reply here", ts="1512085950.000300"),
        ]
        result = ReadThreadResult(
            success=True,
            messages=messages,
            user_map={"W012A3CDE": "spengler", "W07QCRPA4": "Glinda"},
        )
        text = str(result)
        assert "[Parent] spengler: Parent message" in text
        assert "[Reply] Glinda: Reply here" in text

    def test_str_empty(self):
        result = ReadThreadResult(success=True, messages=[])
        assert str(result) == "No messages found in thread."

    def test_str_on_error(self):
        result = ReadThreadResult(success=False, error="thread_not_found")
        assert str(result) == "Error: thread_not_found"


# ---------------------------------------------------------------------------
# JoinChannelResult
# ---------------------------------------------------------------------------


class TestJoinChannelResult:
    def test_str_output(self):
        result = JoinChannelResult(success=True, channel_id="C012AB3CD", channel_name="general")
        text = str(result)
        assert "#general" in text
        assert "C012AB3CD" in text

    def test_str_on_error(self):
        result = JoinChannelResult(success=False, error="is_archived")
        assert str(result) == "Error: is_archived"


# ---------------------------------------------------------------------------
# EditMessageResult
# ---------------------------------------------------------------------------


class TestEditMessageResult:
    def test_parse_api_response(self):
        data = _load_json("chat_update.json")
        result = EditMessageResult.model_validate(data)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.ts == "1503435956.000247"

    def test_str_output(self):
        data = _load_json("chat_update.json")
        result = EditMessageResult.model_validate(data)
        text = str(result)
        assert "edited successfully" in text
        assert "C012AB3CD" in text

    def test_str_on_error(self):
        result = EditMessageResult(success=False, error="cant_update_message")
        assert str(result) == "Error: cant_update_message"


# ---------------------------------------------------------------------------
# GetPermalinkResult
# ---------------------------------------------------------------------------


class TestGetPermalinkResult:
    def test_parse_api_response(self):
        data = _load_json("chat_get_permalink.json")
        result = GetPermalinkResult.model_validate(data)
        assert result.success is True
        assert "ghostbusters.slack.com" in result.permalink

    def test_str_output(self):
        data = _load_json("chat_get_permalink.json")
        result = GetPermalinkResult.model_validate(data)
        text = str(result)
        assert "https://ghostbusters.slack.com/" in text

    def test_str_on_error(self):
        result = GetPermalinkResult(success=False, error="message_not_found")
        assert str(result) == "Error: message_not_found"


# ---------------------------------------------------------------------------
# GetFileInfoResult
# ---------------------------------------------------------------------------


class TestGetFileInfoResult:
    def test_str_output(self):
        data = _load_json("files_info.json")
        f = data["file"]
        from apron_tools.providers.slack.types import SlackFile

        result = GetFileInfoResult(
            success=True,
            file=SlackFile.model_validate(f),
        )
        text = str(result)
        assert "F0S43PZDF" in text
        assert "tedair.gif" in text
        assert "image/gif" in text
        assert "137531" in text

    def test_str_on_error(self):
        result = GetFileInfoResult(success=False, error="file_not_found")
        assert str(result) == "Error: file_not_found"


# ---------------------------------------------------------------------------
# DownloadFileResult
# ---------------------------------------------------------------------------


class TestDownloadFileResult:
    def test_str_text_content(self):
        result = DownloadFileResult(success=True, content="Hello, world!", mime_type="text/plain")
        assert str(result) == "Hello, world!"

    def test_str_binary_content(self):
        result = DownloadFileResult(success=True, content="dGVzdA==", mime_type="image/png")
        text = str(result)
        assert "Content-Type: image/png" in text
        assert "base64" in text
        assert "dGVzdA==" in text

    def test_str_on_error(self):
        result = DownloadFileResult(success=False, error="Request timed out.")
        assert str(result) == "Error: Request timed out."


# ---------------------------------------------------------------------------
# GetReactionsResult
# ---------------------------------------------------------------------------


class TestGetReactionsResult:
    def test_str_output(self):
        reactions = [
            SlackReaction(name="laughing", count=2, users=["W012A3CDE", "W07QCRPA4"]),
            SlackReaction(name="+1", count=1, users=["W07QCRPA4"]),
        ]
        result = GetReactionsResult(success=True, reactions=reactions, item_type="message")
        text = str(result)
        assert ":laughing: 2" in text
        assert "W012A3CDE" in text
        assert ":+1: 1" in text

    def test_str_no_reactions(self):
        result = GetReactionsResult(success=True, reactions=[])
        assert str(result) == "No reactions found."

    def test_str_on_error(self):
        result = GetReactionsResult(success=False, error="no_item_specified")
        assert str(result) == "Error: no_item_specified"


# ---------------------------------------------------------------------------
# AddReactionsResult
# ---------------------------------------------------------------------------


class TestAddReactionsResult:
    def test_str_lists_per_message_outcomes(self):
        result = AddReactionsResult(
            success=True,
            reaction_name="thumbsup",
            channel_id="C012AB3CD",
            items=[
                AddReactionItem(timestamp="1512085950.000216", success=True),
                AddReactionItem(timestamp="1512085951.000217", success=True),
            ],
        )
        text = str(result)
        assert ":thumbsup:" in text
        assert "C012AB3CD" in text
        assert "1512085950.000216" in text
        assert "1512085951.000217" in text

    def test_str_marks_per_message_failures(self):
        result = AddReactionsResult(
            success=True,
            reaction_name="thumbsup",
            channel_id="C012AB3CD",
            items=[
                AddReactionItem(timestamp="1512085950.000216", success=True),
                AddReactionItem(timestamp="bad-ts", success=False, error="already_reacted"),
            ],
        )
        text = str(result)
        assert "bad-ts" in text
        assert "already_reacted" in text

    def test_str_on_top_level_error(self):
        result = AddReactionsResult(success=False, error="already_reacted")
        assert str(result) == "Error: already_reacted"

    def test_str_with_no_items(self):
        result = AddReactionsResult(success=True, reaction_name="thumbsup", items=[])
        assert str(result) == "No messages processed."
