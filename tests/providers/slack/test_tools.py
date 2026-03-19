"""Tests for Slack tool functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

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
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.team_info.return_value = _mock_response(_load_json("team_info.json"))
        client.conversations_list.return_value = _mock_response(_load_json("conversations_list.json"))
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
        client.conversations_list.return_value = _mock_response(_load_json("conversations_list.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_TOKEN, base_url=_BASE_URL)

        assert result.success is True
        assert result.workspace_name == "Slack Workspace"
        assert len(result.channels) == 2

    async def test_has_tool_definition(self) -> None:
        defn = slack_explore_workspace._tool_definition
        assert defn.name == "slack_explore_workspace"
        assert defn.provider == "slack"
        assert "team:read" in defn.scopes


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
            SendChannelMessageParams(channel_id="C000", message="test"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "channel_not_found"

    async def test_has_tool_definition(self) -> None:
        defn = slack_send_channel_message._tool_definition
        assert defn.name == "slack_send_channel_message"
        assert defn.provider == "slack"
        assert "chat:write" in defn.scopes


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
        assert result.error == "user_not_found"

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
            ReadChannelMessagesParams(channel_id="C000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "channel_not_found"

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
            GetChannelInfoParams(channel_id="C000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "channel_not_found"

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
        assert result.error == "thread_not_found"

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
            JoinChannelParams(channel_id="C000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "is_archived"

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
            EditMessageParams(channel_id="C000", message_ts="000", new_text="x"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
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
            GetPermalinkParams(channel_id="C000", message_ts="000"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "message_not_found"

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
        assert result.error == "file_not_found"

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
