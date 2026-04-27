"""Tests for Gmail tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.google.gmail.tools import (
    gmail_add_labels_to_emails,
    gmail_create_draft,
    gmail_create_label,
    gmail_edit_draft,
    gmail_get_thread_replies,
    gmail_list_emails,
    gmail_list_labels,
    gmail_read_email,
    gmail_remove_labels_from_emails,
    gmail_reply_to_email,
    gmail_send_email,
)
from apron_tools.providers.google.gmail.types import (
    AddLabelsToEmailsParams,
    CreateDraftParams,
    CreateDraftResult,
    CreateLabelParams,
    CreateLabelResult,
    EditDraftParams,
    EditDraftResult,
    GetThreadRepliesParams,
    GetThreadRepliesResult,
    ListEmailsParams,
    ListEmailsResult,
    ListLabelsParams,
    ListLabelsResult,
    ModifyLabelsResult,
    ReadEmailParams,
    ReadEmailResult,
    RemoveLabelsFromEmailsParams,
    ReplyToEmailParams,
    ReplyToEmailResult,
    SendEmailParams,
    SendEmailResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_emails
# ---------------------------------------------------------------------------


class TestListEmails:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages?maxResults=25&q=from%3Aalice%40example.com",
            json=_load_json("list_messages.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_message_meta_1.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-002?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_message_meta_2.json"),
        )

        result = await gmail_list_emails(
            ListEmailsParams(query="from:alice@example.com"),
            token=_TOKEN,
        )

        assert isinstance(result, ListEmailsResult)
        assert result.success is True
        assert len(result.emails) == 2
        assert result.emails[0].subject == "Project Status Update"
        assert result.emails[0].from_address == "alice@example.com"
        assert result.emails[1].subject == "Re: Project Status Update"

    async def test_empty_results(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json={"resultSizeEstimate": 0},
        )

        result = await gmail_list_emails(
            ListEmailsParams(query="from:nobody@example.com"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.emails == []

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await gmail_list_emails(ListEmailsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_list_emails._tool_definition
        assert defn.name == "gmail_list_emails"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# read_email
# ---------------------------------------------------------------------------


class TestReadEmail:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=_load_json("get_message_full.json"),
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert isinstance(result, ReadEmailResult)
        assert result.success is True
        assert result.id == "msg-001"
        assert result.thread_id == "thread-001"
        assert result.subject == "Project Status Update"
        assert result.from_address == "alice@example.com"
        assert result.to_address == "bob@example.com"
        assert result.cc == "carol@example.com"
        assert result.body == "Hello world"
        assert result.label_ids == ["INBOX", "UNREAD"]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_read_email(
            ReadEmailParams(message_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_read_email._tool_definition
        assert defn.name == "gmail_read_email"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------


class TestSendEmail:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/send",
            json=_load_json("send_message.json"),
        )

        result = await gmail_send_email(
            SendEmailParams(
                to="bob@example.com",
                subject="Hello",
                body="Hi Bob",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, SendEmailResult)
        assert result.success is True
        assert result.id == "msg-003"
        assert result.thread_id == "thread-002"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await gmail_send_email(
            SendEmailParams(to="bad", subject="Test", body="Body"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_send_email._tool_definition
        assert defn.name == "gmail_send_email"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.compose" in defn.scopes


# ---------------------------------------------------------------------------
# create_draft
# ---------------------------------------------------------------------------


class TestCreateDraft:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts",
            json=_load_json("create_draft.json"),
        )

        result = await gmail_create_draft(
            CreateDraftParams(
                to="bob@example.com",
                subject="Draft Subject",
                body="Draft body",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateDraftResult)
        assert result.success is True
        assert result.id == "draft-001"
        assert result.message_id == "msg-004"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await gmail_create_draft(
            CreateDraftParams(to="bob@example.com", subject="Test", body="Body"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_create_draft._tool_definition
        assert defn.name == "gmail_create_draft"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.compose" in defn.scopes


# ---------------------------------------------------------------------------
# edit_draft
# ---------------------------------------------------------------------------


class TestEditDraft:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=full",
            json=_load_json("get_draft.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001",
            json=_load_json("edit_draft.json"),
        )

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", subject="Updated Subject"),
            token=_TOKEN,
        )

        assert isinstance(result, EditDraftResult)
        assert result.success is True
        assert result.id == "draft-001"
        assert result.message_id == "msg-005"

    async def test_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="bad-id", subject="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_edit_draft._tool_definition
        assert defn.name == "gmail_edit_draft"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.compose" in defn.scopes


# ---------------------------------------------------------------------------
# reply_to_email
# ---------------------------------------------------------------------------


class TestReplyToEmail:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=_load_json("get_message_for_reply.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/send",
            json=_load_json("send_reply.json"),
        )

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="msg-001", body="Thanks for the update!"),
            token=_TOKEN,
        )

        assert isinstance(result, ReplyToEmailResult)
        assert result.success is True
        assert result.id == "msg-006"
        assert result.thread_id == "thread-001"

    async def test_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="bad-id", body="Reply"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_reply_to_email._tool_definition
        assert defn.name == "gmail_reply_to_email"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.compose" in defn.scopes


# ---------------------------------------------------------------------------
# get_thread_replies
# ---------------------------------------------------------------------------


class TestGetThreadReplies:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/threads/thread-001?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_thread.json"),
        )

        result = await gmail_get_thread_replies(
            GetThreadRepliesParams(thread_id="thread-001"),
            token=_TOKEN,
        )

        assert isinstance(result, GetThreadRepliesResult)
        assert result.success is True
        assert result.thread_id == "thread-001"
        assert result.subject == "Project Status Update"
        assert len(result.messages) == 2
        assert result.messages[0].from_address == "alice@example.com"
        assert result.messages[1].from_address == "bob@example.com"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_get_thread_replies(
            GetThreadRepliesParams(thread_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_get_thread_replies._tool_definition
        assert defn.name == "gmail_get_thread_replies"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# list_labels
# ---------------------------------------------------------------------------


class TestListLabels:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/labels",
            json=_load_json("list_labels.json"),
        )

        result = await gmail_list_labels(ListLabelsParams(), token=_TOKEN)

        assert isinstance(result, ListLabelsResult)
        assert result.success is True
        assert len(result.labels) == 3
        assert result.labels[2].name == "Work"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await gmail_list_labels(ListLabelsParams(), token=_TOKEN)

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_list_labels._tool_definition
        assert defn.name == "gmail_list_labels"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# add_labels_to_emails (bulk)
# ---------------------------------------------------------------------------


class TestAddLabelsToEmails:
    async def test_single_message(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/modify",
            json=_load_json("modify_add_label.json"),
        )

        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids="msg-001", label_ids="label-001"),
            token=_TOKEN,
        )

        assert isinstance(result, ModifyLabelsResult)
        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].message_id == "msg-001"
        assert result.items[0].success is True
        assert "label-001" in result.items[0].label_ids

    async def test_multiple_messages(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/modify",
            json={"id": "msg-001", "threadId": "t-1", "labelIds": ["INBOX", "label-001"]},
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-002/modify",
            json={"id": "msg-002", "threadId": "t-2", "labelIds": ["INBOX", "label-001"]},
        )

        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids="msg-001, msg-002", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert [item.message_id for item in result.items] == ["msg-001", "msg-002"]
        assert all(item.success for item in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/modify",
            json=_load_json("modify_add_label.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/bad-id/modify",
            status_code=404,
            text="Not Found",
        )

        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids="msg-001,bad-id", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "404" in (result.items[1].error or "")

    async def test_empty_message_ids(self) -> None:
        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids="", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No message IDs provided."

    async def test_empty_label_ids(self) -> None:
        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids="msg-001", label_ids=" , "),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No label IDs provided."

    async def test_has_tool_definition(self) -> None:
        defn = gmail_add_labels_to_emails._tool_definition
        assert defn.name == "gmail_add_labels_to_emails"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.modify" in defn.scopes


# ---------------------------------------------------------------------------
# remove_labels_from_emails (bulk)
# ---------------------------------------------------------------------------


class TestRemoveLabelsFromEmails:
    async def test_single_message(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/modify",
            json=_load_json("modify_remove_label.json"),
        )

        result = await gmail_remove_labels_from_emails(
            RemoveLabelsFromEmailsParams(message_ids="msg-001", label_ids="label-001"),
            token=_TOKEN,
        )

        assert isinstance(result, ModifyLabelsResult)
        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].message_id == "msg-001"
        assert "label-001" not in result.items[0].label_ids

    async def test_multiple_messages(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/modify",
            json={"id": "msg-001", "threadId": "t-1", "labelIds": ["INBOX"]},
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-002/modify",
            json={"id": "msg-002", "threadId": "t-2", "labelIds": ["INBOX"]},
        )

        result = await gmail_remove_labels_from_emails(
            RemoveLabelsFromEmailsParams(message_ids="msg-001,msg-002", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert [item.message_id for item in result.items] == ["msg-001", "msg-002"]
        assert all(item.success for item in result.items)

    async def test_api_error_per_item(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/bad-id/modify",
            status_code=403,
            text="Forbidden",
        )

        result = await gmail_remove_labels_from_emails(
            RemoveLabelsFromEmailsParams(message_ids="bad-id", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is False
        assert "403" in (result.items[0].error or "")

    async def test_empty_message_ids(self) -> None:
        result = await gmail_remove_labels_from_emails(
            RemoveLabelsFromEmailsParams(message_ids="  ", label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No message IDs provided."

    async def test_has_tool_definition(self) -> None:
        defn = gmail_remove_labels_from_emails._tool_definition
        assert defn.name == "gmail_remove_labels_from_emails"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.modify" in defn.scopes


# ---------------------------------------------------------------------------
# create_label
# ---------------------------------------------------------------------------


class TestCreateLabel:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/labels",
            json=_load_json("create_label.json"),
        )

        result = await gmail_create_label(
            CreateLabelParams(name="Invoices"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateLabelResult)
        assert result.success is True
        assert result.id == "Label_42"
        assert result.name == "Invoices"
        assert result.type == "user"

    async def test_trims_whitespace_in_request(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/labels",
            json=_load_json("create_label.json"),
        )

        result = await gmail_create_label(
            CreateLabelParams(name="  Invoices  "),
            token=_TOKEN,
        )

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        assert json.loads(request.content)["name"] == "Invoices"

    async def test_rejects_whitespace_only_name(self) -> None:
        result = await gmail_create_label(
            CreateLabelParams(name="   "),
            token=_TOKEN,
        )

        assert result.success is False
        assert "empty" in result.error.lower()

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=409, text="Label name exists")

        result = await gmail_create_label(
            CreateLabelParams(name="Invoices"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "409" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = gmail_create_label._tool_definition
        assert defn.name == "gmail_create_label"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.labels" in defn.scopes
