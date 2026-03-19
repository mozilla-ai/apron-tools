"""Tests for Microsoft Outlook tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.outlook.tools import (
    microsoft_outlook_create_draft,
    microsoft_outlook_list_emails,
    microsoft_outlook_read_email,
    microsoft_outlook_send_draft,
    microsoft_outlook_send_email,
)
from apron_tools.providers.microsoft.outlook.types import (
    CreateDraftParams,
    CreateDraftResult,
    ListEmailsParams,
    ListEmailsResult,
    ReadEmailParams,
    ReadEmailResult,
    SendDraftParams,
    SendDraftResult,
    SendEmailParams,
    SendEmailResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_MESSAGE_ID = "msg-001"
_DRAFT_ID = "msg-draft-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_emails
# ---------------------------------------------------------------------------


class TestListEmails:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_messages.json"))

        result = await microsoft_outlook_list_emails(ListEmailsParams(), token=_TOKEN)

        assert isinstance(result, ListEmailsResult)
        assert result.success is True
        assert len(result.emails) == 2
        assert result.emails[0].subject == "You have late tasks!"
        assert result.emails[0].is_read is False
        assert result.emails[1].is_read is True

    async def test_with_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_messages.json"))

        result = await microsoft_outlook_list_emails(
            ListEmailsParams(query="isRead eq false", limit=10),
            token=_TOKEN,
        )

        assert isinstance(result, ListEmailsResult)
        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await microsoft_outlook_list_emails(ListEmailsParams(), token=_TOKEN)

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_outlook_list_emails._tool_definition
        assert defn.name == "microsoft_outlook_list_emails"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_outlook"
        assert "Mail.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_email
# ---------------------------------------------------------------------------


class TestReadEmail:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/messages/{_MESSAGE_ID}",
            json=_load_json("get_message.json"),
        )

        result = await microsoft_outlook_read_email(
            ReadEmailParams(message_id=_MESSAGE_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadEmailResult)
        assert result.success is True
        assert result.email is not None
        assert result.email.subject == "You have late tasks!"
        assert result.email.body is not None
        assert "past due" in result.email.body.content

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_outlook_read_email(
            ReadEmailParams(message_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_outlook_read_email._tool_definition
        assert defn.name == "microsoft_outlook_read_email"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_outlook"
        assert "Mail.Read" in defn.scopes


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------


class TestSendEmail:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/sendMail",
            status_code=202,
        )

        result = await microsoft_outlook_send_email(
            SendEmailParams(
                to=["alice@contoso.com"],
                subject="Hello",
                body="Hi Alice",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, SendEmailResult)
        assert result.success is True

    async def test_with_cc_bcc(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/sendMail",
            status_code=202,
        )

        result = await microsoft_outlook_send_email(
            SendEmailParams(
                to=["alice@contoso.com"],
                subject="Hello",
                body="Hi",
                cc=["bob@contoso.com"],
                bcc=["carol@contoso.com"],
            ),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await microsoft_outlook_send_email(
            SendEmailParams(
                to=["alice@contoso.com"],
                subject="Hello",
                body="Hi",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_outlook_send_email._tool_definition
        assert defn.name == "microsoft_outlook_send_email"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_outlook"
        assert "Mail.Send" in defn.scopes


# ---------------------------------------------------------------------------
# create_draft
# ---------------------------------------------------------------------------


class TestCreateDraft:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/messages",
            json=_load_json("create_draft.json"),
        )

        result = await microsoft_outlook_create_draft(
            CreateDraftParams(
                to=["bob@contoso.com"],
                subject="Draft email",
                body="Draft content here",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateDraftResult)
        assert result.success is True
        assert result.draft is not None
        assert result.draft.id == "msg-draft-001"
        assert result.draft.is_draft is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await microsoft_outlook_create_draft(
            CreateDraftParams(
                to=["bob@contoso.com"],
                subject="Draft",
                body="Content",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_outlook_create_draft._tool_definition
        assert defn.name == "microsoft_outlook_create_draft"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_outlook"
        assert "Mail.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# send_draft
# ---------------------------------------------------------------------------


class TestSendDraft:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/messages/{_DRAFT_ID}/send",
            status_code=202,
        )

        result = await microsoft_outlook_send_draft(
            SendDraftParams(message_id=_DRAFT_ID),
            token=_TOKEN,
        )

        assert isinstance(result, SendDraftResult)
        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_outlook_send_draft(
            SendDraftParams(message_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_outlook_send_draft._tool_definition
        assert defn.name == "microsoft_outlook_send_draft"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_outlook"
        assert "Mail.Send" in defn.scopes
