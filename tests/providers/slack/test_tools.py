"""Tests for Slack tool functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_httpx import HTTPXMock
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from apron_tools.providers import slack as slack_pkg
from apron_tools.providers.slack import tools as slack_tools
from apron_tools.providers.slack.tools import (
    slack_add_reactions,
    slack_download_file,
    slack_edit_message,
    slack_explore_workspace,
    slack_get_channel_info,
    slack_get_file_info,
    slack_get_permalink,
    slack_get_reactions,
    slack_join_channel,
    slack_list_my_conversations,
    slack_list_saved_items,
    slack_read_channel_messages,
    slack_read_thread,
    slack_save_file_for_upload,
    slack_search_messages,
    slack_send_channel_message,
    slack_send_channel_message_with_file,
    slack_send_user_message,
)
from apron_tools.providers.slack.types import (
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
    ListSavedItemsParams,
    ListSavedItemsResult,
    ReadChannelMessagesParams,
    ReadChannelMessagesResult,
    ReadThreadParams,
    ReadThreadResult,
    SaveFileForUploadParams,
    SaveFileForUploadResult,
    SearchMessagesParams,
    SearchMessagesResult,
    SendChannelMessageParams,
    SendChannelMessageResult,
    SendChannelMessageWithFileParams,
    SendChannelMessageWithFileResult,
    SendUserMessageParams,
    SendUserMessageResult,
)
from apron_tools.types import FileFromBytes, FileFromUrl

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "xoxp-test-token-abc123"
_BOT_TOKEN = "xoxb-test-token-abc123"
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
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=_BOT_TOKEN, base_url=_BASE_URL)

        assert result.success is False
        assert "requires a user token" in result.error
        client.team_info.assert_not_called()

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
# slack_list_my_conversations
# ---------------------------------------------------------------------------


class TestSlackListMyConversations:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_list_my_conversations(
            ListMyConversationsParams(),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.users_conversations.assert_not_called()

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.users_conversations.return_value = _mock_response(
            {
                "ok": True,
                "channels": [
                    {
                        "id": "C012AB3CD",
                        "name": "general",
                        "is_im": False,
                        "is_mpim": False,
                        "is_private": False,
                        "updated": 1735689600,
                    },
                    {
                        "id": "D012AB3CD",
                        "is_im": True,
                        "is_private": True,
                        "user": "U012A3CDE",
                        "updated": 1735689601,
                    },
                ],
            }
        )

        result = await slack_list_my_conversations(
            ListMyConversationsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, ListMyConversationsResult)
        assert result.success is True
        assert len(result.conversations) == 2
        assert result.conversations[0].name == "general"
        assert result.conversations[1].is_im is True
        client.users_conversations.assert_called_once_with(
            types="im,mpim,public_channel,private_channel",
            exclude_archived=True,
            limit=200,
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_rejects_invalid_types_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_list_my_conversations(
            ListMyConversationsParams(types="im,not_a_real_type"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "Unsupported conversation type" in result.error
        client.users_conversations.assert_not_called()

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.users_conversations.side_effect = _slack_api_error("invalid_arguments")

        result = await slack_list_my_conversations(
            ListMyConversationsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "invalid_arguments" in result.error
        assert "NOT a permissions error" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_list_my_conversations._tool_definition
        assert defn.name == "slack_list_my_conversations"
        assert defn.provider == "slack"
        assert "channels:read" in defn.scopes
        assert "groups:read" in defn.scopes
        assert "im:read" in defn.scopes
        assert "mpim:read" in defn.scopes


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
# slack_send_channel_message_with_file
# ---------------------------------------------------------------------------


class TestSlackSendChannelMessageWithFile:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_uploads_file_from_bytes_with_comment(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.files_upload_v2.return_value = _mock_response(
            {
                "ok": True,
                "file": {
                    "id": "F123",
                    "permalink": "https://example.slack.com/files/F123",
                },
            }
        )

        result = await slack_send_channel_message_with_file(
            SendChannelMessageWithFileParams(
                channel_id="C012AB3CD",
                file=FileFromBytes(
                    data=b"aGVsbG8sIHNsYWNr",
                    filename="hello.txt",
                    mime_type="text/plain",
                ),
                comment="Please review",
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, SendChannelMessageWithFileResult)
        assert result.success is True
        assert result.channel == "C012AB3CD"
        assert result.file_id == "F123"
        assert result.file_permalink == "https://example.slack.com/files/F123"
        client.files_upload_v2.assert_called_once_with(
            channel="C012AB3CD",
            content=b"hello, slack",
            filename="hello.txt",
            initial_comment="Please review",
        )

    @patch("apron_tools.providers.slack.tools.resolve_file_input", new_callable=AsyncMock)
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_file_from_url_is_resolved_before_upload(
        self,
        mock_cls: AsyncMock,
        mock_resolve_file_input: AsyncMock,
    ) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        mock_resolve_file_input.return_value = (b"resolved-bytes", "report.pdf", "application/pdf")
        client.files_upload_v2.return_value = _mock_response(
            {
                "ok": True,
                "files": [{"id": "F456", "permalink": "https://example.slack.com/files/F456"}],
            }
        )

        file_input = FileFromUrl(url="https://example.com/report.pdf")
        result = await slack_send_channel_message_with_file(
            SendChannelMessageWithFileParams(
                channel_id="C012AB3CD",
                file=file_input,
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        mock_resolve_file_input.assert_awaited_once_with(file_input)
        client.files_upload_v2.assert_called_once_with(
            channel="C012AB3CD",
            content=b"resolved-bytes",
            filename="report.pdf",
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_upload_failure_returns_domain_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.files_upload_v2.side_effect = _slack_api_error("invalid_arguments")

        result = await slack_send_channel_message_with_file(
            SendChannelMessageWithFileParams(
                channel_id="C012AB3CD",
                file=FileFromBytes(
                    data=b"eA==",
                    filename="x.txt",
                    mime_type="text/plain",
                ),
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "invalid_arguments" in result.error
        assert "NOT a permissions error" in result.error
        assert "SlackApiError" not in result.error

    async def test_has_tool_definition(self) -> None:
        defn = slack_send_channel_message_with_file._tool_definition
        assert defn.name == "slack_send_channel_message_with_file"
        assert defn.provider == "slack"
        assert "chat:write" in defn.scopes
        assert "files:write" in defn.scopes


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
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.conversations_history.assert_not_called()

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
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_get_channel_info(
            GetChannelInfoParams(channel_id="C012AB3CD"),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.conversations_info.assert_not_called()

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
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_read_thread(
            ReadThreadParams(channel_id="C012AB3CD", thread_ts="1512085950.000216"),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.conversations_replies.assert_not_called()

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

    async def test_rejects_ssrf_url(self) -> None:
        """slack_download_file returns an error for non-Slack URLs."""
        result = await slack_download_file(
            DownloadFileParams(url="http://169.254.169.254/latest/meta-data/"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "Failed to download file" in result.error


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
# slack_add_reactions (bulk)
# ---------------------------------------------------------------------------


class TestSlackAddReactions:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_single_message(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.return_value = _mock_response(_load_json("reactions_add.json"))

        result = await slack_add_reactions(
            AddReactionsParams(channel_id="C012AB3CD", timestamps="1512085950.000216", reaction_name="thumbsup"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, AddReactionsResult)
        assert result.success is True
        assert result.reaction_name == "thumbsup"
        assert result.channel_id == "C012AB3CD"
        assert len(result.items) == 1
        assert result.items[0].timestamp == "1512085950.000216"
        assert result.items[0].success is True
        client.reactions_add.assert_called_once_with(
            channel="C012AB3CD", timestamp="1512085950.000216", name="thumbsup"
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_multiple_messages(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.return_value = _mock_response(_load_json("reactions_add.json"))

        result = await slack_add_reactions(
            AddReactionsParams(
                channel_id="C012AB3CD",
                timestamps="1512085950.000216, 1512085951.000217",
                reaction_name="thumbsup",
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert [item.timestamp for item in result.items] == [
            "1512085950.000216",
            "1512085951.000217",
        ]
        assert all(item.success for item in result.items)
        assert client.reactions_add.await_count == 2

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_strips_colons(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.return_value = _mock_response(_load_json("reactions_add.json"))

        result = await slack_add_reactions(
            AddReactionsParams(
                channel_id="C012AB3CD",
                timestamps="1512085950.000216",
                reaction_name=":thumbsup:",
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.reaction_name == "thumbsup"

    async def test_empty_reaction_name(self) -> None:
        result = await slack_add_reactions(
            AddReactionsParams(channel_id="C012AB3CD", timestamps="000", reaction_name="::"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "empty" in result.error

    async def test_invalid_reaction_name(self) -> None:
        result = await slack_add_reactions(
            AddReactionsParams(channel_id="C012AB3CD", timestamps="000", reaction_name="bad emoji!"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "invalid" in result.error

    async def test_empty_timestamps(self) -> None:
        result = await slack_add_reactions(
            AddReactionsParams(channel_id="C012AB3CD", timestamps=" , ", reaction_name="thumbsup"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert result.error == "No timestamps provided."

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_partial_failure(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.reactions_add.side_effect = [
            _mock_response(_load_json("reactions_add.json")),
            _slack_api_error("already_reacted"),
        ]

        result = await slack_add_reactions(
            AddReactionsParams(
                channel_id="C012AB3CD",
                timestamps="ts-001,ts-002",
                reaction_name="thumbsup",
            ),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert result.items[1].error == "already_reacted"

    async def test_has_tool_definition(self) -> None:
        defn = slack_add_reactions._tool_definition
        assert defn.name == "slack_add_reactions"
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

    async def test_rejects_ssrf_url(self) -> None:
        """slack_save_file_for_upload returns an error for non-Slack URLs."""
        result = await slack_save_file_for_upload(
            SaveFileForUploadParams(url="http://169.254.169.254/latest/meta-data/"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "Failed to save file" in result.error


# ---------------------------------------------------------------------------
# slack_search_messages
# ---------------------------------------------------------------------------


class TestSlackSearchMessages:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_search_messages(
            SearchMessagesParams(query="hello"),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.search_messages.assert_not_called()

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.return_value = _mock_response(_load_json("search_messages.json"))

        result = await slack_search_messages(
            SearchMessagesParams(query="meaning of life"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, SearchMessagesResult)
        assert result.success is True
        assert len(result.matches) == 2
        first = result.matches[0]
        assert first.channel_id == "C012AB3GH"
        assert first.channel_name == "general"
        assert first.is_im is False
        assert first.user == "U2U85N1RV"
        assert first.username == "roach"
        assert first.permalink.startswith("https://")
        # Bot/integration messages have user="" and the display name in username.
        bot_match = result.matches[1]
        assert bot_match.user == ""
        assert bot_match.username == "robot overlord"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_passes_sort_defaults(self, mock_cls: AsyncMock) -> None:
        """Defaults to timestamp/desc (newest first), not Slack's score/desc."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.return_value = _mock_response({"ok": True, "messages": {"matches": []}})

        await slack_search_messages(
            SearchMessagesParams(query="hello"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.search_messages.assert_called_once_with(
            query="hello",
            count=20,
            sort="timestamp",
            sort_dir="desc",
        )

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_empty_matches(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.return_value = _mock_response({"ok": True, "messages": {"matches": []}})

        result = await slack_search_messages(
            SearchMessagesParams(query="nothing matches"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.matches == []
        assert "No matches found" in str(result)

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_im_match_detected_via_match_type(self, mock_cls: AsyncMock) -> None:
        """Slack sets ``type: 'im'`` at the match level for DM hits even when
        ``channel.is_im`` is absent — the parser must honour that signal."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.return_value = _mock_response(
            {
                "ok": True,
                "messages": {
                    "matches": [
                        {
                            "type": "im",
                            "channel": {"id": "D012AB3CD", "name": "U999XYZ"},
                            "user": "U999XYZ",
                            "text": "ping",
                            "ts": "1700000000.000100",
                            "permalink": "https://example.slack.com/archives/D012AB3CD/p1700000000000100",
                        }
                    ]
                },
            }
        )

        result = await slack_search_messages(
            SearchMessagesParams(query="ping"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert len(result.matches) == 1
        assert result.matches[0].is_im is True

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.side_effect = _slack_api_error("ratelimited")

        result = await slack_search_messages(
            SearchMessagesParams(query="hello"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "ratelimited" in result.error

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_str_shows_username_and_user_id_when_both_present(self, mock_cls: AsyncMock) -> None:
        """For human-authored messages the LLM-readable summary surfaces the
        display name plus the user ID (``username (user_id)``); bot/integration
        posts with no user ID surface the name alone."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.search_messages.return_value = _mock_response(_load_json("search_messages.json"))

        result = await slack_search_messages(
            SearchMessagesParams(query="meaning of life"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        rendered = str(result)
        # First match is human-authored (user + username both present).
        assert "roach (U2U85N1RV)" in rendered
        # Second match is a bot post (user empty, only username).
        assert "robot overlord" in rendered
        assert "robot overlord (" not in rendered

    async def test_has_tool_definition(self) -> None:
        defn = slack_search_messages._tool_definition
        assert defn.name == "slack_search_messages"
        assert defn.provider == "slack"
        assert "search:read" in defn.scopes


# ---------------------------------------------------------------------------
# slack_list_saved_items
# ---------------------------------------------------------------------------


class TestSlackListSavedItems:
    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_rejects_bot_token_before_api_call(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_list_saved_items(
            ListSavedItemsParams(),
            token=_BOT_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "requires a user token" in result.error
        client.stars_list.assert_not_called()

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_success(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.stars_list.return_value = _mock_response(_load_json("stars_list.json"))

        result = await slack_list_saved_items(
            ListSavedItemsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert isinstance(result, ListSavedItemsResult)
        assert result.success is True
        assert len(result.items) == 1
        item = result.items[0]
        assert item.type == "message"
        assert item.channel_id == "C012AB3GH"
        assert item.message_ts == "1655762568.324229"
        # The fixture's bot_message subtype carries empty text — content is in
        # attachments. The parser surfaces the empty text faithfully rather
        # than guessing at attachment content.
        assert item.text == ""
        client.stars_list.assert_called_once_with(limit=100)

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_empty_items(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.stars_list.return_value = _mock_response({"ok": True, "items": []})

        result = await slack_list_saved_items(
            ListSavedItemsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.items == []
        assert "No saved items" in str(result)

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_channel_type_item_has_no_message_text(self, mock_cls: AsyncMock) -> None:
        """For type=channel|im|group items the saved item is the channel
        itself; ``text`` and ``message_ts`` stay empty."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.stars_list.return_value = _mock_response(
            {
                "ok": True,
                "items": [
                    {"type": "channel", "channel": "C0G9QF9GZ"},
                    {"type": "im", "channel": "D0K3F9GZ1"},
                ],
            }
        )

        result = await slack_list_saved_items(
            ListSavedItemsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert len(result.items) == 2
        assert result.items[0].type == "channel"
        assert result.items[0].channel_id == "C0G9QF9GZ"
        assert result.items[0].text == ""
        assert result.items[0].message_ts == ""
        assert result.items[1].type == "im"
        assert result.items[1].channel_id == "D0K3F9GZ1"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_passes_custom_limit(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.stars_list.return_value = _mock_response({"ok": True, "items": []})

        await slack_list_saved_items(
            ListSavedItemsParams(limit=50),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        client.stars_list.assert_called_once_with(limit=50)

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_api_error(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.stars_list.side_effect = _slack_api_error("ratelimited")

        result = await slack_list_saved_items(
            ListSavedItemsParams(),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is False
        assert "ratelimited" in result.error

    def test_rejects_limit_at_or_above_1000(self) -> None:
        """Slack documents the ``stars.list`` cap as 'limit value under 1000'."""
        with pytest.raises(ValueError):
            ListSavedItemsParams(limit=1000)

    async def test_has_tool_definition(self) -> None:
        defn = slack_list_saved_items._tool_definition
        assert defn.name == "slack_list_saved_items"
        assert defn.provider == "slack"
        assert "stars:read" in defn.scopes


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


class TestValidateUserToken:
    def test_rejects_bot_token(self) -> None:
        error = slack_tools._validate_user_token(_BOT_TOKEN)
        assert error is not None
        assert "requires a user token" in error
        assert "NOT a transient API error" in error

    @pytest.mark.parametrize("token", [_TOKEN, "", "totally-not-a-slack-token"])
    def test_non_bot_tokens_pass_through_for_scope_checks(self, token: str) -> None:
        assert slack_tools._validate_user_token(token) is None


class TestTokenPrefixHelpers:
    def test_constants_match_slack_token_scheme(self) -> None:
        assert slack_pkg.USER_TOKEN_PREFIX == "xoxp-"
        assert slack_pkg.BOT_TOKEN_PREFIX == "xoxb-"

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            (_TOKEN, True),
            (_BOT_TOKEN, False),
            ("", False),
            ("xoxa-not-a-user-token", False),
        ],
    )
    def test_is_user_token(self, token: str, expected: bool) -> None:
        assert slack_pkg.is_user_token(token) is expected

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            (_BOT_TOKEN, True),
            (_TOKEN, False),
            ("", False),
            ("xoxa-not-a-bot-token", False),
        ],
    )
    def test_is_bot_token(self, token: str, expected: bool) -> None:
        assert slack_pkg.is_bot_token(token) is expected


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
    async def test_add_reactions_rejects_name(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client

        result = await slack_add_reactions(
            AddReactionsParams(
                channel_id="general",
                timestamps="1512085950.000216",
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


# ---------------------------------------------------------------------------
# Block Kit + attachment message-text extraction.
#
# Slack messages built with Block Kit or legacy attachments carry their real
# content inside the ``blocks`` or ``attachments`` arrays; the top-level
# ``text`` is often just a short notification fallback. The read tools must
# surface the rich content so agents can actually read what was said.
# ---------------------------------------------------------------------------


class TestCollectText:
    """Unit tests for ``_collect_text`` — the recursive Slack text walker."""

    def _text(self, obj: object) -> str:
        return "\n".join(slack_tools._collect_text(obj))

    def test_section_block_text(self) -> None:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":tada: *New User Signup*\n• *Name:* Alice\n• *Email:* alice@example.com\n• *Role:* Engineer"
                    ),
                },
            }
        ]
        result = self._text(blocks)
        assert "Alice" in result
        assert "alice@example.com" in result
        assert "Engineer" in result

    def test_header_block(self) -> None:
        blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Important"}}]
        assert "Important" in self._text(blocks)

    def test_context_block(self) -> None:
        blocks = [
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "Posted by bot"}],
            }
        ]
        assert "Posted by bot" in self._text(blocks)

    def test_rich_text_nested_elements(self) -> None:
        blocks = [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [{"type": "text", "text": "Hello world"}],
                    }
                ],
            }
        ]
        assert "Hello world" in self._text(blocks)

    def test_section_with_fields(self) -> None:
        blocks = [
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": "*Name:* Bob"},
                    {"type": "mrkdwn", "text": "*Role:* PM"},
                ],
            }
        ]
        result = self._text(blocks)
        assert "*Name:* Bob" in result
        assert "*Role:* PM" in result

    def test_empty_input(self) -> None:
        assert self._text([]) == ""

    def test_divider_only_returns_empty(self) -> None:
        assert self._text([{"type": "divider"}]) == ""

    def test_attachment_text(self) -> None:
        assert "Deploy succeeded" in self._text([{"text": "Deploy succeeded for main branch"}])

    def test_attachment_fallback(self) -> None:
        assert "GitHub notification" in self._text([{"fallback": "GitHub notification"}])

    def test_multiple_attachments(self) -> None:
        result = self._text([{"text": "First attachment"}, {"text": "Second attachment"}])
        assert "First attachment" in result
        assert "Second attachment" in result

    def test_walks_arbitrary_nesting(self) -> None:
        """Unknown block types are walked transparently."""
        blocks = [
            {
                "type": "future_block_type",
                "content": {"type": "plain_text", "text": "Discovered via recursion"},
            }
        ]
        assert "Discovered via recursion" in self._text(blocks)


class TestGetMessageText:
    """Unit tests for ``_get_message_text`` — the blocks/attachments/text priority."""

    def test_prefers_blocks_over_text(self) -> None:
        msg = {
            "text": "New user signup: alice@example.com",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":tada: *New User Signup*\n• *Name:* Alice\n• *Email:* alice@example.com",
                    },
                }
            ],
        }
        result = slack_tools._get_message_text(msg)
        assert "Name:" in result
        assert "Alice" in result

    def test_falls_back_to_text_when_no_blocks(self) -> None:
        assert slack_tools._get_message_text({"text": "Hello world"}) == "Hello world"

    def test_falls_back_to_text_when_blocks_empty(self) -> None:
        assert slack_tools._get_message_text({"text": "Fallback", "blocks": []}) == "Fallback"

    def test_falls_back_when_blocks_yield_no_text(self) -> None:
        msg = {"text": "Fallback", "blocks": [{"type": "divider"}]}
        assert slack_tools._get_message_text(msg) == "Fallback"

    def test_missing_text_and_blocks(self) -> None:
        assert slack_tools._get_message_text({}) == ""

    def test_prefers_blocks_over_attachments(self) -> None:
        msg = {
            "text": "fallback",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Block content"}}],
            "attachments": [{"text": "Attachment content"}],
        }
        assert slack_tools._get_message_text(msg) == "Block content"

    def test_falls_back_to_attachments_when_no_blocks(self) -> None:
        msg = {"text": "fallback", "attachments": [{"text": "Attachment content here"}]}
        assert slack_tools._get_message_text(msg) == "Attachment content here"

    def test_falls_back_to_text_when_attachments_empty(self) -> None:
        assert slack_tools._get_message_text({"text": "plain text", "attachments": []}) == "plain text"


class TestReadChannelMessagesBlocksAndAttachments:
    """``slack_read_channel_messages`` surfaces block/attachment content in message text."""

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_message_with_blocks_surfaces_block_content(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history_blocks.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert len(result.messages) == 1
        assert "Alice Smith" in result.messages[0].text
        assert "alice@example.com" in result.messages[0].text
        assert "Engineer" in result.messages[0].text

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_message_without_blocks_still_uses_plain_text(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history_plain_text.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert result.messages[0].text == "Just a plain text message"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_message_with_legacy_attachments_surfaces_values(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(_load_json("conversations_history_attachments.json"))
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        text = result.messages[0].text
        assert "New PR opened" in text
        assert "Fix login redirect bug" in text
        assert "apron-tools" in text
        assert "alice" in text

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_files_still_surfaced_alongside_block_text(self, mock_cls: AsyncMock) -> None:
        """Ports should not regress the existing ``files`` surfacing."""
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_history.return_value = _mock_response(
            _load_json("conversations_history_blocks_with_files.json")
        )
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_channel_messages(
            ReadChannelMessagesParams(channel_id="C012AB3CD"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        msg = result.messages[0]
        assert "Rich block body" in msg.text
        assert msg.files is not None
        assert msg.files[0]["name"] == "diagram.png"


class TestReadThreadBlocksAndAttachments:
    """``slack_read_thread`` surfaces block/attachment content in message text."""

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_thread_parent_with_blocks(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_replies.return_value = _mock_response(
            _load_json("conversations_replies_parent_blocks.json")
        )
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_thread(
            ReadThreadParams(channel_id="C012AB3CD", thread_ts="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert len(result.messages) == 2
        assert "Detailed parent content" in result.messages[0].text
        assert result.messages[1].text == "Reply text"

    @patch("apron_tools.providers.slack.tools.AsyncWebClient")
    async def test_thread_reply_with_attachments(self, mock_cls: AsyncMock) -> None:
        client = AsyncMock()
        mock_cls.return_value = client
        client.conversations_replies.return_value = _mock_response(
            _load_json("conversations_replies_reply_attachments.json")
        )
        client.users_list.return_value = _mock_response(_load_json("users_list.json"))

        result = await slack_read_thread(
            ReadThreadParams(channel_id="C012AB3CD", thread_ts="1512085950.000216"),
            token=_TOKEN,
            base_url=_BASE_URL,
        )

        assert result.success is True
        assert "Build failed on main" in result.messages[1].text


# ---------------------------------------------------------------------------
# SSRF prevention — _validate_slack_file_url
# ---------------------------------------------------------------------------


class TestValidateSlackFileUrl:
    """CWE-918: Server-Side Request Forgery (SSRF) prevention.

    slack_download_file and slack_save_file_for_upload make authenticated
    HTTP requests using the user's Slack OAuth token.  Without URL validation
    a malicious actor who can inject content into a Slack channel (prompt
    injection) could redirect those requests to internal cloud metadata
    services (e.g. http://169.254.169.254/) or other private hosts.
    """

    def test_valid_files_slack_com_url(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        assert _validate_slack_file_url("https://files.slack.com/files-pri/T123/F456/img.png") is None

    def test_valid_slack_files_com_url(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        assert _validate_slack_file_url("https://files.slack-files.com/files-pri/T123/F456/img.png") is None

    def test_valid_slack_edge_com_url(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        assert _validate_slack_file_url("https://a.slack-edge.com/T123/img-thumb.png") is None

    def test_rejects_cloud_metadata_endpoint(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        error = _validate_slack_file_url("http://169.254.169.254/latest/meta-data/")
        assert error is not None
        assert "HTTPS" in error or "Slack" in error

    def test_rejects_http_scheme(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        error = _validate_slack_file_url("http://files.slack.com/files-pri/T123/F456/img.png")
        assert error is not None
        assert "HTTPS" in error

    def test_rejects_internal_ip(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        error = _validate_slack_file_url("https://10.0.0.1/secret")
        assert error is not None

    def test_rejects_arbitrary_external_host(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        error = _validate_slack_file_url("https://evil.example.com/slack.com/file")
        assert error is not None

    def test_rejects_slack_com_lookalike(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        # hostname is ``evil-slack.com`` — suffix check must use dot-prefix.
        error = _validate_slack_file_url("https://evil-slack.com/file")
        assert error is not None

    def test_rejects_slack_com_prefix_lookalike(self) -> None:
        from apron_tools.providers.slack.tools import _validate_slack_file_url

        # hostname is ``evilslack.com`` — suffix check must use dot-prefix.
        error = _validate_slack_file_url("https://evilslack.com/file")
        assert error is not None
