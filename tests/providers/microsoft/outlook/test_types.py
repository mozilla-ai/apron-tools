"""Tests for Microsoft Outlook provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.microsoft.outlook.types import (
    CreateDraftParams,
    CreateDraftResult,
    EmailAddress,
    EmailBody,
    EmailMessage,
    ListEmailsParams,
    ListEmailsResult,
    ReadEmailParams,
    ReadEmailResult,
    Recipient,
    SendDraftParams,
    SendDraftResult,
    SendEmailParams,
    SendEmailResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListEmailsParams:
    def test_defaults(self):
        params = ListEmailsParams()
        assert params.query == ""
        assert params.limit == 25

    def test_custom(self):
        params = ListEmailsParams(query="isRead eq false", limit=10)
        assert params.query == "isRead eq false"
        assert params.limit == 10


class TestReadEmailParams:
    def test_required(self):
        params = ReadEmailParams(message_id="msg-001")
        assert params.message_id == "msg-001"


class TestSendEmailParams:
    def test_required(self):
        params = SendEmailParams(
            to=["alice@contoso.com"],
            subject="Hello",
            body="Hi Alice",
        )
        assert params.to == ["alice@contoso.com"]
        assert params.subject == "Hello"
        assert params.body == "Hi Alice"
        assert params.cc == []
        assert params.bcc == []

    def test_with_cc_bcc(self):
        params = SendEmailParams(
            to=["alice@contoso.com"],
            subject="Hello",
            body="Hi",
            cc=["bob@contoso.com"],
            bcc=["carol@contoso.com"],
        )
        assert params.cc == ["bob@contoso.com"]
        assert params.bcc == ["carol@contoso.com"]


class TestCreateDraftParams:
    def test_required(self):
        params = CreateDraftParams(
            to=["bob@contoso.com"],
            subject="Draft",
            body="Content",
        )
        assert params.to == ["bob@contoso.com"]
        assert params.subject == "Draft"
        assert params.body == "Content"
        assert params.cc == []
        assert params.bcc == []


class TestSendDraftParams:
    def test_required(self):
        params = SendDraftParams(message_id="msg-draft-001")
        assert params.message_id == "msg-draft-001"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestEmailAddress:
    def test_parse(self):
        addr = EmailAddress(name="Alice Smith", address="alice@contoso.com")
        assert addr.name == "Alice Smith"
        assert addr.address == "alice@contoso.com"

    def test_defaults(self):
        addr = EmailAddress()
        assert addr.name == ""
        assert addr.address == ""


class TestRecipient:
    def test_parse_from_api(self):
        data = _load_json("list_messages.json")
        recipient = Recipient.model_validate(data["value"][0]["toRecipients"][0])
        assert recipient.email_address.name == "Alice Smith"
        assert recipient.email_address.address == "alice@contoso.com"


class TestEmailBody:
    def test_parse_from_api(self):
        data = _load_json("get_message.json")
        body = EmailBody.model_validate(data["body"])
        assert body.content_type == "html"
        assert "past due" in body.content

    def test_defaults(self):
        body = EmailBody()
        assert body.content_type == "text"
        assert body.content == ""


class TestEmailMessage:
    def test_parse_list_item(self):
        data = _load_json("list_messages.json")
        msg = EmailMessage.model_validate(data["value"][0])
        assert msg.id == "msg-001"
        assert msg.subject == "You have late tasks!"
        assert msg.body_preview == "You have tasks that are past due..."
        assert msg.importance == "normal"
        assert msg.is_read is False
        assert msg.is_draft is False
        assert msg.has_attachments is False
        assert msg.received_date_time == "2024-03-15T10:00:00Z"
        assert msg.from_ is not None
        assert msg.from_.email_address.name == "Microsoft Planner"
        assert msg.from_.email_address.address == "noreply@planner.office365.com"
        assert len(msg.to_recipients) == 1
        assert msg.to_recipients[0].email_address.address == "alice@contoso.com"

    def test_parse_full_message(self):
        data = _load_json("get_message.json")
        msg = EmailMessage.model_validate(data)
        assert msg.id == "msg-001"
        assert msg.body is not None
        assert msg.body.content_type == "html"
        assert "past due" in msg.body.content

    def test_parse_draft(self):
        data = _load_json("create_draft.json")
        msg = EmailMessage.model_validate(data)
        assert msg.id == "msg-draft-001"
        assert msg.is_draft is True
        assert msg.body is not None
        assert msg.body.content == "Draft content here"

    def test_read_message_with_cc(self):
        data = _load_json("list_messages.json")
        msg = EmailMessage.model_validate(data["value"][1])
        assert msg.id == "msg-002"
        assert msg.is_read is True
        assert msg.has_attachments is True
        assert len(msg.cc_recipients) == 1
        assert msg.cc_recipients[0].email_address.address == "carol@contoso.com"


# ---------------------------------------------------------------------------
# ListEmailsResult
# ---------------------------------------------------------------------------


class TestListEmailsResult:
    def test_success(self):
        data = _load_json("list_messages.json")
        emails = [EmailMessage.model_validate(m) for m in data["value"]]
        result = ListEmailsResult(success=True, emails=emails)
        assert result.success is True
        assert len(result.emails) == 2

    def test_str_output(self):
        data = _load_json("list_messages.json")
        emails = [EmailMessage.model_validate(m) for m in data["value"]]
        result = ListEmailsResult(success=True, emails=emails)
        text = str(result)
        assert "2 email(s)" in text
        assert "You have late tasks!" in text
        assert "[UNREAD]" in text
        assert "Microsoft Planner" in text

    def test_str_empty(self):
        result = ListEmailsResult(success=True, emails=[])
        assert str(result) == "No emails found."

    def test_str_on_error(self):
        result = ListEmailsResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


# ---------------------------------------------------------------------------
# ReadEmailResult
# ---------------------------------------------------------------------------


class TestReadEmailResult:
    def test_success(self):
        data = _load_json("get_message.json")
        email = EmailMessage.model_validate(data)
        result = ReadEmailResult(success=True, email=email)
        assert result.success is True
        assert result.email is not None
        assert result.email.subject == "You have late tasks!"

    def test_str_output(self):
        data = _load_json("get_message.json")
        email = EmailMessage.model_validate(data)
        result = ReadEmailResult(success=True, email=email)
        text = str(result)
        assert "You have late tasks!" in text
        assert "Microsoft Planner" in text
        assert "alice@contoso.com" in text
        assert "past due" in text

    def test_str_no_email(self):
        result = ReadEmailResult(success=True, email=None)
        assert str(result) == "No email found."

    def test_str_on_error(self):
        result = ReadEmailResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# SendEmailResult
# ---------------------------------------------------------------------------


class TestSendEmailResult:
    def test_success(self):
        result = SendEmailResult(success=True)
        assert result.success is True

    def test_str_output(self):
        result = SendEmailResult(success=True)
        assert str(result) == "Email sent successfully."

    def test_str_on_error(self):
        result = SendEmailResult(success=False, error="Rate limited")
        assert str(result) == "Error: Rate limited"


# ---------------------------------------------------------------------------
# CreateDraftResult
# ---------------------------------------------------------------------------


class TestCreateDraftResult:
    def test_success(self):
        data = _load_json("create_draft.json")
        draft = EmailMessage.model_validate(data)
        result = CreateDraftResult(success=True, draft=draft)
        assert result.success is True
        assert result.draft is not None
        assert result.draft.id == "msg-draft-001"

    def test_str_output(self):
        data = _load_json("create_draft.json")
        draft = EmailMessage.model_validate(data)
        result = CreateDraftResult(success=True, draft=draft)
        text = str(result)
        assert "msg-draft-001" in text
        assert "Draft created successfully" in text

    def test_str_no_draft(self):
        result = CreateDraftResult(success=True, draft=None)
        assert str(result) == "Draft created but no details available."

    def test_str_on_error(self):
        result = CreateDraftResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# SendDraftResult
# ---------------------------------------------------------------------------


class TestSendDraftResult:
    def test_success(self):
        result = SendDraftResult(success=True)
        assert result.success is True

    def test_str_output(self):
        result = SendDraftResult(success=True)
        assert str(result) == "Draft sent successfully."

    def test_str_on_error(self):
        result = SendDraftResult(success=False, error="Bad request")
        assert str(result) == "Error: Bad request"
