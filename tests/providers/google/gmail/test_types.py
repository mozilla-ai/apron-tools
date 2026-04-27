"""Tests for Gmail provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.google.gmail.types import (
    AddLabelsToEmailsParams,
    CreateDraftParams,
    CreateDraftResult,
    CreateLabelParams,
    CreateLabelResult,
    EditDraftParams,
    EditDraftResult,
    EmailSummary,
    GetThreadRepliesParams,
    GetThreadRepliesResult,
    GmailLabel,
    ListEmailsParams,
    ListEmailsResult,
    ListLabelsParams,
    ListLabelsResult,
    ModifyLabelsItem,
    ModifyLabelsResult,
    ReadEmailParams,
    ReadEmailResult,
    RemoveLabelsFromEmailsParams,
    ReplyToEmailParams,
    ReplyToEmailResult,
    SendEmailParams,
    SendEmailResult,
    ThreadMessage,
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
        assert params.max_results == 25

    def test_custom(self):
        params = ListEmailsParams(query="from:alice@example.com", max_results=10)
        assert params.query == "from:alice@example.com"
        assert params.max_results == 10


class TestReadEmailParams:
    def test_required(self):
        params = ReadEmailParams(message_id="msg-001")
        assert params.message_id == "msg-001"


class TestSendEmailParams:
    def test_required(self):
        params = SendEmailParams(to="bob@example.com", subject="Hi", body="Hello")
        assert params.to == "bob@example.com"
        assert params.subject == "Hi"
        assert params.body == "Hello"
        assert params.cc is None
        assert params.bcc is None

    def test_with_cc_bcc(self):
        params = SendEmailParams(
            to="bob@example.com",
            subject="Hi",
            body="Hello",
            cc="carol@example.com",
            bcc="dave@example.com",
        )
        assert params.cc == "carol@example.com"
        assert params.bcc == "dave@example.com"


class TestCreateDraftParams:
    def test_required(self):
        params = CreateDraftParams(to="bob@example.com", subject="Draft", body="Content")
        assert params.to == "bob@example.com"
        assert params.subject == "Draft"
        assert params.body == "Content"


class TestEditDraftParams:
    def test_required(self):
        params = EditDraftParams(draft_id="draft-001")
        assert params.draft_id == "draft-001"
        assert params.to is None
        assert params.subject is None
        assert params.body is None

    def test_with_updates(self):
        params = EditDraftParams(draft_id="draft-001", subject="New Subject")
        assert params.subject == "New Subject"


class TestReplyToEmailParams:
    def test_required(self):
        params = ReplyToEmailParams(message_id="msg-001", body="Thanks!")
        assert params.message_id == "msg-001"
        assert params.body == "Thanks!"
        assert params.cc is None


class TestGetThreadRepliesParams:
    def test_required(self):
        params = GetThreadRepliesParams(thread_id="thread-001")
        assert params.thread_id == "thread-001"


class TestListLabelsParams:
    def test_defaults(self):
        params = ListLabelsParams()
        assert params is not None


class TestAddLabelsToEmailsParams:
    def test_required(self):
        params = AddLabelsToEmailsParams(message_ids="msg-001", label_ids="label-001")
        assert params.message_ids == "msg-001"
        assert params.label_ids == "label-001"

    def test_csv_inputs(self):
        params = AddLabelsToEmailsParams(message_ids="msg-001,msg-002", label_ids="label-001,label-002")
        assert params.message_ids == "msg-001,msg-002"
        assert params.label_ids == "label-001,label-002"


class TestRemoveLabelsFromEmailsParams:
    def test_required(self):
        params = RemoveLabelsFromEmailsParams(message_ids="msg-001", label_ids="label-001")
        assert params.message_ids == "msg-001"
        assert params.label_ids == "label-001"

    def test_csv_inputs(self):
        params = RemoveLabelsFromEmailsParams(message_ids="msg-001,msg-002", label_ids="label-001,label-002")
        assert params.message_ids == "msg-001,msg-002"
        assert params.label_ids == "label-001,label-002"


class TestCreateLabelParams:
    def test_required(self):
        params = CreateLabelParams(name="Invoices")
        assert params.name == "Invoices"

    def test_rejects_empty_name(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateLabelParams(name="")


# ---------------------------------------------------------------------------
# ListEmailsResult
# ---------------------------------------------------------------------------


class TestListEmailsResult:
    def test_success_with_emails(self):
        emails = [
            EmailSummary(
                id="msg-001",
                thread_id="thread-001",
                subject="Project Status Update",
                from_address="alice@example.com",
                to_address="bob@example.com",
                date="Mon, 10 Mar 2024 14:00:00 +0000",
                snippet="Hi, just checking in...",
            ),
        ]
        result = ListEmailsResult(success=True, emails=emails)

        assert result.success is True
        assert len(result.emails) == 1
        assert result.emails[0].subject == "Project Status Update"

    def test_str_output(self):
        emails = [
            EmailSummary(
                id="msg-001",
                thread_id="thread-001",
                subject="Test",
                from_address="alice@example.com",
            ),
        ]
        result = ListEmailsResult(success=True, emails=emails)
        text = str(result)

        assert "1 email(s)" in text
        assert "msg-001" in text
        assert "Test" in text

    def test_str_empty(self):
        result = ListEmailsResult(success=True, emails=[])
        assert str(result) == "No emails found."

    def test_str_on_error(self):
        result = ListEmailsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# ReadEmailResult
# ---------------------------------------------------------------------------


class TestReadEmailResult:
    def test_parse_fields(self):
        result = ReadEmailResult(
            success=True,
            id="msg-001",
            thread_id="thread-001",
            subject="Project Status Update",
            from_address="alice@example.com",
            to_address="bob@example.com",
            cc="carol@example.com",
            date="Mon, 10 Mar 2024 14:00:00 +0000",
            body="Hello world",
            label_ids=["INBOX", "UNREAD"],
        )

        assert result.success is True
        assert result.id == "msg-001"
        assert result.body == "Hello world"
        assert result.label_ids == ["INBOX", "UNREAD"]

    def test_str_output(self):
        result = ReadEmailResult(
            success=True,
            id="msg-001",
            thread_id="thread-001",
            subject="Test Subject",
            from_address="alice@example.com",
            to_address="bob@example.com",
            date="Mon, 10 Mar 2024 14:00:00 +0000",
            body="Email body here",
        )
        text = str(result)

        assert "Test Subject" in text
        assert "alice@example.com" in text
        assert "Email body here" in text

    def test_str_with_cc(self):
        result = ReadEmailResult(
            success=True,
            id="msg-001",
            subject="Test",
            from_address="a@b.com",
            to_address="c@d.com",
            cc="e@f.com",
            date="Mon, 10 Mar 2024 14:00:00 +0000",
            body="Body",
        )
        text = str(result)
        assert "Cc: e@f.com" in text

    def test_str_on_error(self):
        result = ReadEmailResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# SendEmailResult
# ---------------------------------------------------------------------------


class TestSendEmailResult:
    def test_success(self):
        result = SendEmailResult(success=True, id="msg-003", thread_id="thread-002")

        assert result.success is True
        assert result.id == "msg-003"

    def test_str_output(self):
        result = SendEmailResult(success=True, id="msg-003", thread_id="thread-002")
        text = str(result)

        assert "msg-003" in text
        assert "sent" in text.lower()

    def test_str_on_error(self):
        result = SendEmailResult(success=False, error="Auth failed")
        assert str(result) == "Error: Auth failed"


# ---------------------------------------------------------------------------
# CreateDraftResult
# ---------------------------------------------------------------------------


class TestCreateDraftResult:
    def test_parse_api_response(self):
        data = _load_json("create_draft.json")
        result = CreateDraftResult.model_validate(data)

        assert result.success is True
        assert result.id == "draft-001"
        assert result.message_id == "msg-004"

    def test_str_output(self):
        result = CreateDraftResult(success=True, id="draft-001", message_id="msg-004")
        text = str(result)

        assert "draft-001" in text
        assert "msg-004" in text

    def test_str_on_error(self):
        result = CreateDraftResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# EditDraftResult
# ---------------------------------------------------------------------------


class TestEditDraftResult:
    def test_parse_api_response(self):
        data = _load_json("edit_draft.json")
        result = EditDraftResult.model_validate(data)

        assert result.success is True
        assert result.id == "draft-001"
        assert result.message_id == "msg-005"

    def test_str_output(self):
        result = EditDraftResult(success=True, id="draft-001", message_id="msg-005")
        text = str(result)

        assert "draft-001" in text
        assert "msg-005" in text

    def test_str_on_error(self):
        result = EditDraftResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ReplyToEmailResult
# ---------------------------------------------------------------------------


class TestReplyToEmailResult:
    def test_success(self):
        result = ReplyToEmailResult(success=True, id="msg-006", thread_id="thread-001")

        assert result.success is True
        assert result.id == "msg-006"
        assert result.thread_id == "thread-001"

    def test_str_output(self):
        result = ReplyToEmailResult(success=True, id="msg-006", thread_id="thread-001")
        text = str(result)

        assert "msg-006" in text
        assert "thread-001" in text

    def test_str_on_error(self):
        result = ReplyToEmailResult(success=False, error="Thread not found")
        assert str(result) == "Error: Thread not found"


# ---------------------------------------------------------------------------
# GetThreadRepliesResult
# ---------------------------------------------------------------------------


class TestGetThreadRepliesResult:
    def test_success_with_messages(self):
        msgs = [
            ThreadMessage(
                id="msg-001",
                from_address="alice@example.com",
                to_address="bob@example.com",
                date="Mon, 10 Mar 2024 14:00:00 +0000",
                snippet="Hi, just checking in...",
            ),
            ThreadMessage(
                id="msg-002",
                from_address="bob@example.com",
                to_address="alice@example.com",
                date="Mon, 10 Mar 2024 15:30:00 +0000",
                snippet="Thanks for the update!",
            ),
        ]
        result = GetThreadRepliesResult(
            success=True,
            thread_id="thread-001",
            subject="Project Status Update",
            messages=msgs,
        )

        assert result.success is True
        assert len(result.messages) == 2
        assert result.subject == "Project Status Update"

    def test_str_output(self):
        msgs = [
            ThreadMessage(
                id="msg-001",
                from_address="alice@example.com",
                date="Mon, 10 Mar 2024 14:00:00 +0000",
                snippet="Check in",
            ),
        ]
        result = GetThreadRepliesResult(
            success=True,
            thread_id="thread-001",
            subject="Test",
            messages=msgs,
        )
        text = str(result)

        assert "thread-001" in text
        assert "1 message(s)" in text
        assert "alice@example.com" in text

    def test_str_empty(self):
        result = GetThreadRepliesResult(success=True, thread_id="thread-001", messages=[])
        assert "no messages" in str(result)

    def test_str_on_error(self):
        result = GetThreadRepliesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ListLabelsResult
# ---------------------------------------------------------------------------


class TestListLabelsResult:
    def test_parse_api_response(self):
        data = _load_json("list_labels.json")
        labels = [GmailLabel.model_validate(lbl) for lbl in data["labels"]]
        result = ListLabelsResult(success=True, labels=labels)

        assert result.success is True
        assert len(result.labels) == 3

    def test_label_fields(self):
        data = _load_json("list_labels.json")
        lbl = GmailLabel.model_validate(data["labels"][2])

        assert lbl.id == "label-001"
        assert lbl.name == "Work"
        assert lbl.type == "user"

    def test_str_output(self):
        labels = [GmailLabel(id="label-001", name="Work", type="user")]
        result = ListLabelsResult(success=True, labels=labels)
        text = str(result)

        assert "1 label(s)" in text
        assert "Work" in text

    def test_str_empty(self):
        result = ListLabelsResult(success=True, labels=[])
        assert str(result) == "No labels found."

    def test_str_on_error(self):
        result = ListLabelsResult(success=False, error="Auth error")
        assert str(result) == "Error: Auth error"


# ---------------------------------------------------------------------------
# ModifyLabelsResult
# ---------------------------------------------------------------------------


class TestModifyLabelsResult:
    def test_str_lists_per_message_outcomes(self):
        result = ModifyLabelsResult(
            success=True,
            items=[
                ModifyLabelsItem(message_id="msg-001", label_ids=["INBOX", "label-001"]),
                ModifyLabelsItem(message_id="msg-002", label_ids=["INBOX"]),
            ],
        )
        text = str(result)

        assert "msg-001" in text
        assert "msg-002" in text
        assert "INBOX" in text
        assert "label-001" in text

    def test_str_marks_per_message_failures(self):
        result = ModifyLabelsResult(
            success=True,
            items=[
                ModifyLabelsItem(message_id="msg-001", label_ids=["INBOX"]),
                ModifyLabelsItem(message_id="bad-id", success=False, error="HTTP 404"),
            ],
        )
        text = str(result)

        assert "msg-001" in text
        assert "bad-id" in text
        assert "HTTP 404" in text

    def test_str_on_top_level_error(self):
        result = ModifyLabelsResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_with_no_items(self):
        result = ModifyLabelsResult(success=True, items=[])
        assert str(result) == "No messages processed."


# ---------------------------------------------------------------------------
# CreateLabelResult
# ---------------------------------------------------------------------------


class TestCreateLabelResult:
    def test_parse_api_response(self):
        data = _load_json("create_label.json")
        result = CreateLabelResult.model_validate(data)

        assert result.success is True
        assert result.id == "Label_42"
        assert result.name == "Invoices"
        assert result.type == "user"

    def test_str_output(self):
        result = CreateLabelResult(success=True, id="Label_42", name="Invoices", type="user")
        text = str(result)

        assert "Label_42" in text
        assert "Invoices" in text

    def test_str_on_error(self):
        result = CreateLabelResult(success=False, error="Label name exists")
        assert str(result) == "Error: Label name exists"
