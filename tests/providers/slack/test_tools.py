"""Tests for Slack tool functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_httpx import HTTPXMock
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from apron_tools.providers.slack import tools as slack_tools
from apron_tools.providers.slack.tools import (
    slack_add_reaction,
    slack_download_file,
    slack_edit_message,
    slack_explore_workspace,
    slack_get_channel_info,
    slack_get_file_info,
    slack_get_permalink,
    slack_get_reactions,
    slack_join_channel,
    slack_read_channel_messages,
    slack_read_thread,
    slack_save_file_for_upload,
    slack_send_channel_message,
    slack_send_user_message,
)
from apron_tools.providers.slack.types import (
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
    SaveFileForUploadParams,
    SaveFileForUploadResult,
    SendChannelMessageParams,
    SendChannelMessageResult,
    SendUserMessageParams,
    SendUserMessageResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "xoxb-test-token-abc123"
_BASE_URL = "https://slack.com/api/"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


def _mock_response(data: dict) -> AsyncSlackResponse:
    """Build a mock AsyncSlackResponse from a dict."""
    return AsyncSlackResponse(
        client=None,
        http_verb="POST",
        api_url="https://slack.com/api/test",
        req_args={},
        data=data,
        headers={},
        status_code=200,
    )


def _slack_api_error(error: str) -> SlackApiError:
    """Build a SlackApiError with the given error string."""
    resp = _mock_response({"ok": False, "error": error})
    return SlackApiError(message=error, response=resp)


# ---------------------------------------------------------------------------
# slack_explore_workspace
# ---------------------------------------------------------------------------


class TestSlackExploreWorkspace:
    """slack_explore_workspace fetches public and private channels in
    separate conversations.list calls. This is load-bearing: a single
    combined call (types=public_channel,private_channel) 403s with
    missing_scope if EITHER channels:read or groups:read is absent, which
    previously caused an OAuth re-consent loop because the agent had no
    usable channel listing to work from.
    """

    _EMPTY_PRIVATE = {"ok": True, "channels": [], "response_metadata": {"next_cursor": ""}}

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.return_value = _mock_response(_load_json("team_info.json"))
        # Split call: public_channel then private_channel.
        client.conversations_list.side_effect = [
            _mock_response(_load_json("conversations_list.json")),
            _mock_response(self._EMPTY_PRIVATE),
        ]
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True
        assert result.workspace_name == "My Team"
        assert len(result.channels) == 2
        assert result.channels[0].name == "general"
        assert len(result.users) == 2
        assert result.users[0].name == "spengler"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_team_info_error_still_succeeds(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.side_effect = _slack_api_error("missing_scope")
        client.conversations_list.side_effect = [
            _mock_response(_load_json("conversations_list.json")),
            _mock_response(self._EMPTY_PRIVATE),
        ]
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        assert result.success is True
        assert result.workspace_name == "Slack Workspace"
        assert len(result.channels) == 2

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_fetches_public_and_private_channels_separately(self, mock_cls: AsyncMock) -> None:
        """Two separate conversations.list calls — one per channel type —
        so a missing scope on one side does not block the other side."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.return_value = _mock_response(_load_json("team_info.json"))
        client.conversations_list.side_effect = [
            _mock_response(_load_json("conversations_list.json")),
            _mock_response(self._EMPTY_PRIVATE),
        ]
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        assert client.conversations_list.call_count == 2
        call_types = [call.kwargs.get("types") for call in client.conversations_list.call_args_list]
        assert call_types == ["public_channel", "private_channel"]

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_missing_groups_read_still_lists_public_channels(self, mock_cls: AsyncMock) -> None:
        """The OAuth re-consent loop bug: a user with channels:read but NOT
        groups:read previously got an empty channel listing because the
        single combined conversations.list call 403'd with missing_scope.
        After the fix, public channels are fetched separately and the
        missing groups:read scope doesn't block the public listing."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.return_value = _mock_response(_load_json("team_info.json"))
        client.conversations_list.side_effect = [
            _mock_response(_load_json("conversations_list.json")),
            _slack_api_error("missing_scope"),
        ]
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        # Public channels still make it through despite the private-side failure.
        assert result.success is True
        assert len(result.channels) == 2
        assert any(c.name == "general" for c in result.channels)

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_missing_channels_read_still_lists_private_channels(self, mock_cls: AsyncMock) -> None:
        """Symmetric case: a user with groups:read but NOT channels:read
        still gets the private channel listing."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.return_value = _mock_response(_load_json("team_info.json"))
        private_response = {
            "ok": True,
            "channels": [
                {
                    "id": "G0AKFJBEU",
                    "name": "secret-project",
                    "is_private": True,
                    "num_members": 3,
                }
            ],
            "response_metadata": {"next_cursor": ""},
        }
        client.conversations_list.side_effect = [
            _slack_api_error("missing_scope"),
            _mock_response(private_response),
        ]
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        assert result.success is True
        assert len(result.channels) == 1
        assert result.channels[0].name == "secret-project"
        assert result.channels[0].is_private is True

    async def test_has_tool_definition(self) -> None:
        defn = slack_explore_workspace._tool_definition
        assert defn.name == "slack_explore_workspace"
        assert defn.provider == "slack"
        assert "team:read" in defn.scopes
        # groups:read must be listed so the missing-scope modal recommends
        # it — without this, a user missing only groups:read re-consents to
        # nothing new and loops back into the same missing_scope error.
        assert "groups:read" in defn.scopes
        assert "channels:read" in defn.scopes
        assert "users:read" in defn.scopes


# ---------------------------------------------------------------------------
# slack_send_channel_message
# ---------------------------------------------------------------------------


class TestSlackSendChannelMessage:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_postMessage.return_value = _mock_response(_load_json("chat_post_message.json"))

        result = await slack_send_channel_message(
            SendChannelMessageParams(channel_id="C012AB3CD", message="Hello"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, SendChannelMessageResult)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.ts == "1503435956.000247"
        client.chat_postMessage.assert_called_once_with(channel="C012AB3CD", text="Hello")

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_with_thread(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_postMessage.return_value = _mock_response(_load_json("chat_post_message.json"))

        await slack_send_channel_message(
            SendChannelMessageParams(channel_id="C012AB3CD", message="Reply", thread_ts="1503435956.000247"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.chat_postMessage.assert_called_once_with(
            channel="C012AB3CD", text="Reply", thread_ts="1503435956.000247"
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_postMessage.side_effect = _slack_api_error("channel_not_found")

        result = await slack_send_channel_message(
            SendChannelMessageParams(channel_id="C01234ABCD", message="test"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        # channel_not_found is a non-permissions error: the formatter wraps
        # it with an explicit disclaimer so the agent does not loop into
        # request_app_connection.
        assert "channel_not_found" in result.error
        assert "NOT a permissions error" in result.error
        assert "channel C01234ABCD" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_send_channel_message._tool_definition
        assert defn.name == "slack_send_channel_message"
        assert defn.provider == "slack"
        assert defn.scopes == ["chat:write"]
        # channels:join is a Slack bot-only scope and must not be listed on
        # this tool — listing it caused the agent to loop into
        # request_app_connection on unrelated failures because the
        # missing-scope modal recommended a scope the user cannot grant.
        assert "channels:join" not in defn.scopes


# ---------------------------------------------------------------------------
# slack_send_user_message
# ---------------------------------------------------------------------------


class TestSlackSendUserMessage:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_open.return_value = _mock_response(_load_json("conversations_open.json"))
        client.chat_postMessage.return_value = _mock_response(_load_json("chat_post_message.json"))

        result = await slack_send_user_message(
            SendUserMessageParams(user_id="U012A3CDE", message="Hi!"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, SendUserMessageResult)
        assert result.success is True
        client.conversations_open.assert_called_once_with(users="U012A3CDE")

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_open_conversation_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_open.side_effect = _slack_api_error("user_not_found")

        result = await slack_send_user_message(
            SendUserMessageParams(user_id="UBAD", message="test"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "user_not_found" in result.error
        assert "NOT a permissions error" in result.error
        assert "user UBAD" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_send_user_message._tool_definition
        assert defn.name == "slack_send_user_message"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_read_channel_messages
# ---------------------------------------------------------------------------


class TestSlackReadChannelMessages:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, ReadChannelMessagesResult)
        assert result.success is True
        assert len(result.messages) == 2
        assert result.has_more is True
        assert "W012A3CDE" in result.user_map

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_messages_reversed(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.messages[0].ts == "1512085950.000100"
        assert result.messages[1].ts == "1512085950.000216"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_limit_capped(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD", limit=999),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        call_kwargs = client.conversations_history.call_args[1]
        assert call_kwargs["limit"] == 100

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.side_effect = _slack_api_error("channel_not_found")

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C01234ABCD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "channel_not_found" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_read_channel_messages._tool_definition
        assert defn.name == "slack_read_channel_messages"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_get_channel_info
# ---------------------------------------------------------------------------


class TestSlackGetChannelInfo:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_info.return_value = _mock_response(_load_json("conversations_info.json"))

        result = await slack_get_channel_info(
            GetChannelInfoParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, GetChannelInfoResult)
        assert result.success is True
        assert result.channel is not None
        assert result.channel.name == "general"
        assert result.channel.num_members == 4
        assert result.topic == "Company-wide announcements and work-based matters"
        assert "team-wide communication" in result.purpose

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_info.side_effect = _slack_api_error("channel_not_found")

        result = await slack_get_channel_info(
            GetChannelInfoParams(channel_id="C01234ABCD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "channel_not_found" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_get_channel_info._tool_definition
        assert defn.name == "slack_get_channel_info"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_read_thread
# ---------------------------------------------------------------------------


class TestSlackReadThread:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_replies.return_value = _mock_response(_load_json("conversations_replies.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_thread(
            ReadThreadParams(channel_id="C012AB3CD", thread_ts="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, ReadThreadResult)
        assert result.success is True
        assert len(result.messages) == 3
        assert result.messages[0].text == "I find you punny and would like to smell your daisy."
        assert result.messages[1].text == "Haha that's a good one!"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_replies.side_effect = _slack_api_error("thread_not_found")

        result = await slack_read_thread(
            ReadThreadParams(channel_id="C012AB3CD", thread_ts="000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "thread_not_found" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_read_thread._tool_definition
        assert defn.name == "slack_read_thread"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_join_channel
# ---------------------------------------------------------------------------


class TestSlackJoinChannel:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_join.return_value = _mock_response(_load_json("conversations_join.json"))

        result = await slack_join_channel(
            JoinChannelParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, JoinChannelResult)
        assert result.success is True
        assert result.channel_name == "general"
        assert result.channel_id == "C012AB3CD"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_join.side_effect = _slack_api_error("is_archived")

        result = await slack_join_channel(
            JoinChannelParams(channel_id="C01234ABCD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "is_archived" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_join_channel._tool_definition
        assert defn.name == "slack_join_channel"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_edit_message
# ---------------------------------------------------------------------------


class TestSlackEditMessage:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_update.return_value = _mock_response(_load_json("chat_update.json"))

        result = await slack_edit_message(
            EditMessageParams(channel_id="C012AB3CD", message_ts="1503435956.000247", new_text="Updated text"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, EditMessageResult)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.ts == "1503435956.000247"
        client.chat_update.assert_called_once_with(channel="C012AB3CD", ts="1503435956.000247", text="Updated text")

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_update.side_effect = _slack_api_error("cant_update_message")

        result = await slack_edit_message(
            EditMessageParams(channel_id="C01234ABCD", message_ts="000", new_text="x"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        # cant_update_message is not in the non-permissions frozenset, so
        # the formatter falls back to the bare code — the existing
        # missing-scope recovery path handles this unchanged.
        assert result.error == "cant_update_message"

    async def test_has_tool_definition(self) -> None:
        defn = slack_edit_message._tool_definition
        assert defn.name == "slack_edit_message"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_get_permalink
# ---------------------------------------------------------------------------


class TestSlackGetPermalink:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_getPermalink.return_value = _mock_response(_load_json("chat_get_permalink.json"))

        result = await slack_get_permalink(
            GetPermalinkParams(channel_id="C012AB3CD", message_ts="1503435956.000247"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, GetPermalinkResult)
        assert result.success is True
        assert "ghostbusters.slack.com" in result.permalink

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.chat_getPermalink.side_effect = _slack_api_error("message_not_found")

        result = await slack_get_permalink(
            GetPermalinkParams(channel_id="C01234ABCD", message_ts="000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "message_not_found" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_get_permalink._tool_definition
        assert defn.name == "slack_get_permalink"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_get_file_info
# ---------------------------------------------------------------------------


class TestSlackGetFileInfo:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.files_info.return_value = _mock_response(_load_json("files_info.json"))

        result = await slack_get_file_info(
            GetFileInfoParams(file_id="F0S43PZDF"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, GetFileInfoResult)
        assert result.success is True
        assert result.file is not None
        assert result.file.id == "F0S43PZDF"
        assert result.file.name == "tedair.gif"
        assert result.file.mimetype == "image/gif"
        assert result.file.size == 137531

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.files_info.side_effect = _slack_api_error("file_not_found")

        result = await slack_get_file_info(
            GetFileInfoParams(file_id="FBAD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "file_not_found" in result.error
        assert "NOT a permissions error" in result.error
        assert "file FBAD" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_get_file_info._tool_definition
        assert defn.name == "slack_get_file_info"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_download_file
# ---------------------------------------------------------------------------


class TestSlackDownloadFile:
    @patch("apron_tools.providers.slack.tools.httpx.AsyncClient")
    async def test_text_file(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain; charset=utf-8"}
        mock_response.content = b"Hello, world!"
        mock_response.text = "Hello, world!"
        mock_client.get.return_value = mock_response

        result = await slack_download_file(
            DownloadFileParams(url="https://files.slack.com/test.txt"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, DownloadFileResult)
        assert result.success is True
        assert result.content == "Hello, world!"
        assert result.mime_type == "text/plain"

    @patch("apron_tools.providers.slack.tools.httpx.AsyncClient")
    async def test_binary_file(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"\x89PNG"
        mock_client.get.return_value = mock_response

        result = await slack_download_file(
            DownloadFileParams(url="https://files.slack.com/test.png"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.mime_type == "image/png"
        assert len(result.content) > 0

    @patch("apron_tools.providers.slack.tools.httpx.AsyncClient")
    async def test_file_too_large(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": str(20 * 1024 * 1024), "content-type": "application/octet-stream"}
        mock_response.content = b"x"
        mock_client.get.return_value = mock_response

        result = await slack_download_file(
            DownloadFileParams(url="https://files.slack.com/big.bin", max_size_mb=10),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "too large" in result.error

    @patch("apron_tools.providers.slack.tools.httpx.AsyncClient")
    async def test_http_error(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        result = await slack_download_file(
            DownloadFileParams(url="https://files.slack.com/forbidden.txt"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_download_file._tool_definition
        assert defn.name == "slack_download_file"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_get_reactions
# ---------------------------------------------------------------------------


class TestSlackGetReactions:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success_message(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_get.return_value = _mock_response(_load_json("reactions_get.json"))

        result = await slack_get_reactions(
            GetReactionsParams(channel_id="C012AB3CD", timestamp="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, GetReactionsResult)
        assert result.success is True
        assert len(result.reactions) == 2
        assert result.reactions[0].name == "laughing"
        assert result.reactions[0].count == 2
        assert result.item_type == "message"

    async def test_missing_params(self) -> None:
        result = await slack_get_reactions(
            GetReactionsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "Must provide" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_get.side_effect = _slack_api_error("no_item_specified")

        result = await slack_get_reactions(
            GetReactionsParams(channel_id="C012AB3CD", timestamp="000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "no_item_specified"

    async def test_has_tool_definition(self) -> None:
        defn = slack_get_reactions._tool_definition
        assert defn.name == "slack_get_reactions"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# slack_add_reaction
# ---------------------------------------------------------------------------


class TestSlackAddReaction:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.return_value = _mock_response(_load_json("reactions_add.json"))

        result = await slack_add_reaction(
            AddReactionParams(channel_id="C012AB3CD", timestamp="1512085950.000216", reaction_name="thumbsup"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, AddReactionResult)
        assert result.success is True
        assert result.reaction_name == "thumbsup"
        client.reactions_add.assert_called_once_with(
            channel="C012AB3CD", timestamp="1512085950.000216", name="thumbsup"
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_strips_colons(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.return_value = _mock_response(_load_json("reactions_add.json"))

        result = await slack_add_reaction(
            AddReactionParams(channel_id="C012AB3CD", timestamp="1512085950.000216", reaction_name=":thumbsup:"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.reaction_name == "thumbsup"

    async def test_empty_reaction_name(self) -> None:
        result = await slack_add_reaction(
            AddReactionParams(channel_id="C012AB3CD", timestamp="000", reaction_name="::"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "empty" in result.error

    async def test_invalid_reaction_name(self) -> None:
        result = await slack_add_reaction(
            AddReactionParams(channel_id="C012AB3CD", timestamp="000", reaction_name="bad emoji!"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "invalid" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.side_effect = _slack_api_error("already_reacted")

        result = await slack_add_reaction(
            AddReactionParams(channel_id="C012AB3CD", timestamp="1512085950.000216", reaction_name="thumbsup"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "already_reacted"

    async def test_has_tool_definition(self) -> None:
        defn = slack_add_reaction._tool_definition
        assert defn.name == "slack_add_reaction"
        assert defn.provider == "slack"


# ---------------------------------------------------------------------------
# save_file_for_upload
# ---------------------------------------------------------------------------


class TestSlackSaveFileForUpload:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        file_bytes = b"\x89PNG\r\n\x1a\nfakeimage"

        # HEAD response.
        httpx_mock.add_response(
            method="HEAD",
            headers={"content-length": str(len(file_bytes)), "content-type": "image/png"},
        )
        # GET response.
        httpx_mock.add_response(
            method="GET",
            content=file_bytes,
            headers={"content-type": "image/png"},
        )

        result = await slack_save_file_for_upload(
            SaveFileForUploadParams(url="https://files.slack.com/files-pri/T1/screenshot.png"),
            token=_TOKEN,
        )

        assert isinstance(result, SaveFileForUploadResult)
        assert result.success is True
        assert result.data == file_bytes
        assert result.filename == "screenshot.png"
        assert result.mime_type == "image/png"
        assert result.size == len(file_bytes)
        assert "screenshot.png" in str(result)

        # Verify binary data survives JSON round-trip via Base64Bytes.
        json_str = result.model_dump_json()
        restored = SaveFileForUploadResult.model_validate_json(json_str)
        assert restored.data == file_bytes

    async def test_file_too_large_from_head(self, httpx_mock: HTTPXMock) -> None:
        # HEAD reports file larger than 10 MB.
        httpx_mock.add_response(
            method="HEAD",
            headers={"content-length": str(11 * 1024 * 1024), "content-type": "image/png"},
        )

        result = await slack_save_file_for_upload(
            SaveFileForUploadParams(url="https://files.slack.com/files-pri/T1/huge.zip"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "too large" in result.error.lower()

    async def test_http_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(method="HEAD", status_code=403)

        result = await slack_save_file_for_upload(
            SaveFileForUploadParams(url="https://files.slack.com/files-pri/T1/secret.pdf"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_save_file_for_upload._tool_definition
        assert defn.name == "slack_save_file_for_upload"
        assert defn.provider == "slack"
        assert "files:read" in defn.scopes


# ---------------------------------------------------------------------------
# OAuth re-consent loop regressions
#
# Tools returning bare Slack error codes for non-permissions failures
# (e.g. ``channel_not_found`` when a channel name was passed as channel_id)
# were historically misread by the agent as missing-scope errors, which
# triggered an OAuth re-consent loop. The two helpers below break that
# loop: ``_validate_slack_channel_id`` rejects names at the tool boundary,
# and ``_format_slack_error`` wraps non-permissions error codes with an
# explicit disclaimer. Genuine 401/403/``missing_scope`` errors must still
# pass through unchanged so the existing missing-scopes recovery path keeps
# working.
# ---------------------------------------------------------------------------


class TestValidateSlackChannelId:
    """Catch channel names passed as channel_id before the API call fires."""

    @pytest.mark.parametrize(
        "valid_id",
        [
            "C01234ABCD",  # pragma: allowlist secret
            "C0123456789",  # pragma: allowlist secret
            "GABCDEFGHIJ",  # pragma: allowlist secret
            "D0123456789",  # pragma: allowlist secret
        ],
    )
    def test_accepts_valid_channel_ids(self, valid_id: str) -> None:
        assert slack_tools._validate_slack_channel_id(valid_id) is None

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "any-forge-test",
            "general",
            "#general",
            "C123",
            "c01234abcd",  # pragma: allowlist secret
            "X01234ABCD",  # pragma: allowlist secret
            "",
        ],
    )
    def test_rejects_names_and_malformed_ids(self, invalid_id: str) -> None:
        error = slack_tools._validate_slack_channel_id(invalid_id)
        assert error is not None
        assert "NOT a permissions error" in error or "non-empty" in error

    def test_lowercased_valid_id_suggests_case_fix_not_name_lookup(self) -> None:
        """A lowercased ``c01234abcd`` is a case mistake, not a channel
        name. The hint must tell the agent to retry with the uppercase
        version, not search for a channel called ``#c01234abcd``."""
        error = slack_tools._validate_slack_channel_id("c01234abcd")  # pragma: allowlist secret
        assert error is not None
        assert "case-sensitive" in error
        assert "C01234ABCD" in error  # pragma: allowlist secret
        # Must not prefix the lowercased form with '#' as if it were a name.
        assert "#c01234abcd" not in error

    def test_malformed_id_uses_generic_lookup_hint(self) -> None:
        """An ID with a wrong prefix letter must not be treated as a
        channel name to look up — there is no channel called
        ``#X01234ABCD``."""
        error = slack_tools._validate_slack_channel_id("X01234ABCD")
        assert error is not None
        assert "#X01234ABCD" not in error
        assert "find the correct channel ID" in error


class TestFormatSlackError:
    @pytest.mark.parametrize(
        "error_code",
        [
            "channel_not_found",
            "not_in_channel",
            "is_archived",
            "user_not_found",
            "message_not_found",
            "file_not_found",
            "invalid_arguments",
        ],
    )
    def test_non_permission_codes_get_disclaimer(self, error_code: str) -> None:
        """Known non-permissions error codes must carry the explicit
        disclaimer so the agent stops looping into request_app_connection."""
        result = slack_tools._format_slack_error("read messages", "channel C01234ABCD", error_code)
        assert error_code in result
        assert "NOT a permissions error" in result
        assert "slack_explore_workspace" in result

    @pytest.mark.parametrize(
        "error_code",
        ["missing_scope", "invalid_auth", "not_authed", "token_revoked"],
    )
    def test_genuine_permission_codes_pass_through(self, error_code: str) -> None:
        """Real auth/scope errors must not get the disclaimer — they still
        need to flow through the missing-scopes recovery path."""
        result = slack_tools._format_slack_error("read messages", "channel C01234ABCD", error_code)
        assert error_code in result
        assert "NOT a permissions error" not in result


class TestChannelIdBoundaryRejection:
    """Tools that take a channel_id reject names without hitting the API."""

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_send_channel_message_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_send_channel_message(
            SendChannelMessageParams(channel_id="any-forge-test", message="hi"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.chat_postMessage.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error
        assert "slack_explore_workspace" in result.error
        assert "do not call request_app_connection" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_read_channel_messages_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="any-forge-test"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.conversations_history.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_get_channel_info_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_get_channel_info(
            GetChannelInfoParams(channel_id="general"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.conversations_info.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_read_thread_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_read_thread(
            ReadThreadParams(channel_id="general", thread_ts="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.conversations_replies.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_join_channel_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_join_channel(
            JoinChannelParams(channel_id="general"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.conversations_join.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_edit_message_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_edit_message(
            EditMessageParams(channel_id="general", message_ts="000", new_text="x"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.chat_update.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_get_permalink_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_get_permalink(
            GetPermalinkParams(channel_id="general", message_ts="000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.chat_getPermalink.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_add_reaction_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_add_reaction(
            AddReactionParams(
                channel_id="general",
                timestamp="1512085950.000216",
                reaction_name="thumbsup",
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.reactions_add.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_get_reactions_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_get_reactions(
            GetReactionsParams(channel_id="general", timestamp="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.reactions_get.assert_not_called()
        assert result.success is False
        assert "not a valid Slack channel ID" in result.error
