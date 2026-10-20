"""Tests for Gmail tool functions."""

from __future__ import annotations

import base64
import email
import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from apron_tools.providers.google.gmail.tools import (
    _extract_body,
    gmail_add_labels_to_emails,
    gmail_create_draft,
    gmail_create_label,
    gmail_edit_draft,
    gmail_get_attachment,
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
    GetAttachmentParams,
    GetAttachmentResult,
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
from apron_tools.types import FileFromBytes

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# An ID whose characters would corrupt the request path if interpolated unencoded.
_TRICKY_ID = "msg 001/x?y#z"
_TRICKY_ID_ENC = "msg%20001%2Fx%3Fy%23z"


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

    async def test_encodes_message_id_in_detail_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages?maxResults=25",
            json={"messages": [{"id": _TRICKY_ID}], "resultSizeEstimate": 1},
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_message_meta_1.json"),
        )

        result = await gmail_list_emails(ListEmailsParams(), token=_TOKEN)

        assert result.success is True
        assert len(result.emails) == 1

    async def test_skips_message_stub_without_id(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages?maxResults=25",
            json={"messages": [{"id": None}, {}, {"id": "msg-001"}], "resultSizeEstimate": 3},
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_message_meta_1.json"),
        )

        result = await gmail_list_emails(ListEmailsParams(), token=_TOKEN)

        assert result.success is True
        assert len(result.emails) == 1
        assert result.emails[0].id == "msg-001"

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

    async def test_encodes_message_id_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}?format=full",
            json=_load_json("get_message_full.json"),
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id=_TRICKY_ID),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_success_with_unpadded_single_part_body(self, httpx_mock: HTTPXMock) -> None:
        # Gmail commonly returns MessagePartBody.data without trailing '=' padding.
        body = "Hi Bob, following up on the thread."
        padded = base64.urlsafe_b64encode(body.encode()).decode("ascii")
        assert padded.endswith("="), "test payload must exercise padding removal"

        message = _load_json("get_message_full.json")
        message["payload"]["mimeType"] = "text/plain"
        message["payload"]["body"] = {"size": len(body), "data": padded.rstrip("=")}
        message["payload"].pop("parts")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == body

    async def test_success_with_unpadded_multipart_body(self, httpx_mock: HTTPXMock) -> None:
        body = "Hi Bob, following up on the thread."
        padded = base64.urlsafe_b64encode(body.encode()).decode("ascii")
        assert padded.endswith("="), "test payload must exercise padding removal"

        message = _load_json("get_message_full.json")
        message["payload"]["parts"][0]["body"] = {
            "size": len(body),
            "data": padded.rstrip("="),
        }

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == body

    @pytest.mark.parametrize(
        "plain_body",
        [{"size": 0}, {"data": base64.urlsafe_b64encode(b"caf\xe9").decode("ascii")}],
        ids=["missing-plain-data", "invalid-plain-utf8"],
    )
    async def test_read_email_keeps_html_fallback(self, httpx_mock: HTTPXMock, plain_body: dict) -> None:
        body = "<p>Keep this HTML body</p>"
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": plain_body},
                {"mimeType": "text/html", "body": {"data": _b64(body)}},
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == body

    async def test_success_with_unpadded_html_body(self, httpx_mock: HTTPXMock) -> None:
        # Unlike the other unpadded regression tests above, this payload requires
        # two padding characters ('==') rather than just one.
        body = "<p>Hi Bob, following up.</p>"
        padded = base64.urlsafe_b64encode(body.encode()).decode("ascii")
        assert padded.endswith("=="), "test payload must require two padding characters"

        message = _load_json("get_message_full.json")
        message["payload"]["parts"][0] = {
            "mimeType": "text/html",
            "body": {"size": len(body), "data": padded.rstrip("=")},
        }

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == body

    async def test_single_part_body_with_undecodable_base64_returns_placeholder(self, httpx_mock: HTTPXMock) -> None:
        # An invalid base64url length (a single data character) raises
        # binascii.Error, a ValueError subclass, which the single-part path
        # catches and reports as a decode failure.
        message = _load_json("get_message_full.json")
        message["payload"]["mimeType"] = "text/plain"
        message["payload"]["body"] = {"size": 1, "data": "A"}
        message["payload"].pop("parts")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == "(Could not decode email body)"

    async def test_single_part_body_with_invalid_base64_alphabet_returns_placeholder(
        self, httpx_mock: HTTPXMock
    ) -> None:
        # A complete valid Base64 block ("YWJj" -> "abc") followed by a stray
        # character outside the base64url alphabet. The lenient decoder would
        # discard the stray character and still decode "abc"; strict validation
        # rejects it. This isolates the alphabet check rather than tripping the
        # padding check the way a shorter invalid payload would.
        message = _load_json("get_message_full.json")
        message["payload"]["mimeType"] = "text/plain"
        message["payload"]["body"] = {"size": 3, "data": "YWJj*"}
        message["payload"].pop("parts")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == "(Could not decode email body)"

    async def test_single_part_body_with_non_utf8_bytes_returns_placeholder(self, httpx_mock: HTTPXMock) -> None:
        # Valid base64url that decodes to bytes that are not valid UTF-8 raises
        # UnicodeDecodeError, also a ValueError subclass, on the single-part path.
        non_utf8 = base64.urlsafe_b64encode(b"\xff\xfe").decode("ascii")

        message = _load_json("get_message_full.json")
        message["payload"]["mimeType"] = "text/plain"
        message["payload"]["body"] = {"size": 2, "data": non_utf8}
        message["payload"].pop("parts")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == "(Could not decode email body)"

    async def test_multipart_body_with_non_utf8_bytes_returns_decode_placeholder(self, httpx_mock: HTTPXMock) -> None:
        # An undecodable multipart body is unreadable rather than absent.
        non_utf8 = base64.urlsafe_b64encode(b"\xff\xfe").decode("ascii")

        message = _load_json("get_message_full.json")
        message["payload"]["parts"][0]["body"] = {"size": 2, "data": non_utf8}

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == "(Could not decode email body)"

    async def test_multipart_sibling_text_survives_undecodable_nested_sibling(self, httpx_mock: HTTPXMock) -> None:
        # The first readable sibling wins even when a later parent has invalid data.
        sibling_text = "Sibling one text"
        sibling_data = base64.urlsafe_b64encode(sibling_text.encode()).decode("ascii")
        nested_text = "Nested sibling text"
        nested_data = base64.urlsafe_b64encode(nested_text.encode()).decode("ascii")

        message = _load_json("get_message_full.json")
        message["payload"]["mimeType"] = "multipart/mixed"
        message["payload"]["parts"] = [
            {
                "mimeType": "text/plain",
                "body": {"size": len(sibling_text), "data": sibling_data},
            },
            {
                "mimeType": "multipart/related",
                # A malformed but non-empty body.data on the multipart part
                # itself: present, but not decodable.
                "body": {"data": "!!!invalid!!!"},
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"size": len(nested_text), "data": nested_data},
                    }
                ],
            },
        ]

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=full",
            json=message,
        )

        result = await gmail_read_email(
            ReadEmailParams(message_id="msg-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.body == sibling_text

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


def _b64(value: str | bytes) -> str:
    return base64.urlsafe_b64encode(value if isinstance(value, bytes) else value.encode()).decode()


class TestExtractBody:
    def test_nested_body_precedes_later_footer(self) -> None:
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _b64("MAIN BODY")}},
                        {"mimeType": "text/html", "body": {"data": _b64("<p>MAIN BODY</p>")}},
                    ],
                },
                {"mimeType": "text/plain", "body": {"data": _b64("-- list footer")}},
            ],
        }
        assert _extract_body(payload) == "MAIN BODY"

    def test_child_body_survives_undecodable_parent_body(self) -> None:
        payload = {
            "mimeType": "multipart/related",
            "body": {"data": "!!!invalid!!!"},
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64("Child text")}},
            ],
        }
        assert _extract_body(payload) == "Child text"

    def test_first_same_type_sibling_wins(self) -> None:
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64("part A")}},
                {"mimeType": "image/jpeg", "body": {}},
                {"mimeType": "text/plain", "body": {"data": _b64("part B")}},
            ],
        }
        assert _extract_body(payload) == "part A"

    def test_plain_text_preferred_over_nested_html(self) -> None:
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/html", "body": {"data": _b64("<p>HTML</p>")}},
                    ],
                },
                {"mimeType": "text/plain", "body": {"data": _b64("Plain text")}},
            ],
        }
        assert _extract_body(payload) == "Plain text"

    def test_strict_mode_raises_on_undecodable_part_before_readable_part(self) -> None:
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64(b"MAIN caf\xe9")}},
                {"mimeType": "text/plain", "body": {"data": _b64("-- list footer")}},
            ],
        }
        assert _extract_body(payload) == "-- list footer"
        with pytest.raises(ValueError, match="Could not decode"):
            _extract_body(payload, strict=True)


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
        assert "https://www.googleapis.com/auth/gmail.send" in defn.scopes


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
    @pytest.mark.parametrize(
        "plain_body",
        [{"size": 0}, {"data": base64.urlsafe_b64encode(b"caf\xe9").decode("ascii")}],
        ids=["missing-plain-data", "invalid-plain-utf8"],
    )
    async def test_subject_only_edit_refuses_html_fallback(self, httpx_mock: HTTPXMock, plain_body: dict) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": plain_body},
                {"mimeType": "text/html", "body": {"data": _b64("<p>Keep this HTML body</p>")}},
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"), is_optional=True
        )

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)

        assert result.success is False
        assert "body" in result.error.lower()
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    async def test_subject_only_edit_preserves_empty_plain_body(self, httpx_mock: HTTPXMock) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"]["body"] = {"size": 0}
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)

        assert result.success is True
        put = next(request for request in httpx_mock.get_requests() if request.method == "PUT")
        raw = json.loads(put.content)["message"]["raw"]
        assert email.message_from_bytes(base64.urlsafe_b64decode(raw)).get_payload() == ""

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64(b"caf\xe9")}},
                ],
            },
            {"mimeType": "text/html", "body": {"data": _b64("<p>HTML only</p>")}},
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Text")}},
                    {"mimeType": "application/pdf", "filename": "file.pdf", "body": {"data": _b64("PDF")}},
                ],
            },
            {
                "mimeType": "multipart/related",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Text")}},
                    {"mimeType": "image/png", "body": {"attachmentId": "inline-image"}},
                ],
            },
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Text")}},
                    {
                        "mimeType": "multipart/related",
                        "parts": [
                            {"mimeType": "image/png", "filename": "inline.png", "body": {}},
                        ],
                    },
                ],
            },
        ],
        ids=["undecodable-multipart", "html-only", "attachment", "inline", "nested-inline"],
    )
    async def test_subject_only_edit_refuses_unrecoverable_content(self, httpx_mock: HTTPXMock, payload: dict) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = payload
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)
        assert result.success is False
        assert "body" in result.error.lower()
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    @pytest.mark.parametrize(
        "part",
        [
            {
                "mimeType": "image/png",
                "filename": "",
                "headers": [
                    {"name": "Content-Disposition", "value": "inline"},
                    {"name": "Content-ID", "value": "<logo>"},
                ],
                "body": {"size": 8, "data": "iVBORw0KGgo="},
            },
            {
                "mimeType": "text/plain",
                "headers": [{"name": "content-disposition", "value": "INLINE; filename=note.txt"}],
                "body": {"data": _b64("Inline note")},
            },
            {
                "mimeType": "text/plain",
                "headers": [{"name": "content-id", "value": "<note>"}],
                "body": {"data": _b64("Referenced note")},
            },
            {
                "mimeType": "application/pdf",
                "headers": [{"name": "Content-Disposition", "value": "attachment"}],
                "body": {},
            },
            {"mimeType": "image/png", "body": {"data": "iVBORw0KGgo="}},
        ],
        ids=["embedded-inline-image", "inline-text", "content-id", "attachment-disposition", "nontext-data"],
    )
    async def test_subject_only_edit_refuses_unnamed_parts(self, httpx_mock: HTTPXMock, part: dict) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = {
            "mimeType": "multipart/related",
            "parts": [{"mimeType": "text/plain", "body": {"data": _b64("Keep this body")}}, part],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001",
            json=_load_json("edit_draft.json"),
            is_optional=True,
        )
        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)
        assert result.success is False
        assert "attachments or inline parts" in result.error
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"mimeType": "text/html", "filename": "inline.html", "body": {"data": "!!!invalid!!!"}},
            {
                "mimeType": "image/png",
                "headers": [{"name": "Content-ID", "value": "<logo>"}],
                "body": {"data": "iVBORw0KGgo="},
            },
        ],
        ids=["html-attachment", "embedded-inline-image"],
    )
    async def test_explicit_body_can_replace_html_and_attachments(self, httpx_mock: HTTPXMock, payload: dict) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = payload
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))
        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="Replacement"), token=_TOKEN)
        assert result.success is True
        put = next(request for request in httpx_mock.get_requests() if request.method == "PUT")
        raw = json.loads(put.content)["message"]["raw"]
        assert email.message_from_bytes(base64.urlsafe_b64decode(raw)).get_payload() == "Replacement"

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "parts": [
                            {"mimeType": "text/plain", "body": {"data": _b64("MAIN BODY")}},
                            {"mimeType": "text/html", "body": {"data": _b64("<p>MAIN BODY</p>")}},
                        ],
                    },
                    {"mimeType": "text/plain", "body": {"data": _b64("-- list footer")}},
                ],
            },
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("part A")}},
                    {"mimeType": "text/plain", "body": {"data": _b64("part B")}},
                ],
            },
        ],
        ids=["nested-body-and-footer", "sibling-parts"],
    )
    async def test_subject_only_edit_refuses_multiple_plain_text_parts(
        self, httpx_mock: HTTPXMock, payload: dict
    ) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = payload
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"), is_optional=True
        )
        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)
        assert result.success is False
        assert "more than one plain-text part" in result.error
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

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

    async def test_encodes_draft_id_in_request_paths(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/{_TRICKY_ID_ENC}?format=full",
            json=_load_json("get_draft.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/{_TRICKY_ID_ENC}",
            json=_load_json("edit_draft.json"),
        )

        result = await gmail_edit_draft(
            EditDraftParams(draft_id=_TRICKY_ID, subject="Updated Subject"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="bad-id", subject="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_subject_only_edit_does_not_clobber_undecodable_body(self, httpx_mock: HTTPXMock) -> None:
        # Editing only the subject (params.body is None, the documented
        # normal case) of a draft whose stored body cannot be decoded must
        # not write a placeholder string over the real body, and must not
        # report success.
        draft = _load_json("get_draft.json")
        draft["message"]["payload"]["body"] = {"size": 13, "data": "!!!invalid!!!"}

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=full",
            json=draft,
        )

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", subject="Updated Subject Only"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error

        # No PUT was issued: the tool must bail out before writing anything,
        # not merely report failure after already clobbering the draft.
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "GET"

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "multipart/alternative",
                        "parts": [
                            {"mimeType": "text/plain", "body": {"data": _b64(b"MAIN caf\xe9")}},
                            {"mimeType": "text/html", "body": {"data": _b64("<p>MAIN</p>")}},
                        ],
                    },
                    {"mimeType": "text/plain", "body": {"data": _b64("-- list footer")}},
                ],
            },
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Keep this body")}},
                    {"mimeType": "text/html", "body": {"data": _b64(b"<p>caf\xe9</p>")}},
                ],
            },
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Sibling text")}},
                    {
                        "mimeType": "multipart/related",
                        "body": {"data": "!!!invalid!!!"},
                        "parts": [{"mimeType": "text/plain", "body": {"data": _b64(b"caf\xe9")}}],
                    },
                ],
            },
        ],
        ids=["undecodable-body-before-footer", "undecodable-html-alternative", "undecodable-nested-part"],
    )
    async def test_subject_only_edit_refuses_undecodable_parts(self, httpx_mock: HTTPXMock, payload: dict) -> None:
        draft = _load_json("get_draft.json")
        draft["message"]["payload"] = payload
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=full", json=draft)
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"), is_optional=True
        )
        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)
        assert result.success is False
        assert "could not be read" in result.error
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

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

    async def test_encodes_message_id_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=_load_json("get_message_for_reply.json"),
        )
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/send",
            json=_load_json("send_reply.json"),
        )

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id=_TRICKY_ID, body="Thanks for the update!"),
            token=_TOKEN,
        )

        assert result.success is True

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

    async def test_encodes_thread_id_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/threads/{_TRICKY_ID_ENC}?format=metadata&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Date",
            json=_load_json("get_thread.json"),
        )

        result = await gmail_get_thread_replies(
            GetThreadRepliesParams(thread_id=_TRICKY_ID),
            token=_TOKEN,
        )

        assert result.success is True

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

    async def test_encodes_message_id_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}/modify",
            json=_load_json("modify_add_label.json"),
        )

        result = await gmail_add_labels_to_emails(
            AddLabelsToEmailsParams(message_ids=_TRICKY_ID, label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True

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

    async def test_encodes_message_id_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}/modify",
            json=_load_json("modify_remove_label.json"),
        )

        result = await gmail_remove_labels_from_emails(
            RemoveLabelsFromEmailsParams(message_ids=_TRICKY_ID, label_ids="label-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True

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


# ---------------------------------------------------------------------------
# get_attachment
# ---------------------------------------------------------------------------


class TestGetAttachment:
    _RAW = b"%PDF-1.4 fake attachment bytes\x00\x01\x02"

    def _encoded(self) -> str:
        return base64.urlsafe_b64encode(self._RAW).decode("ascii")

    async def test_success_with_hints(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-001",
            json={"attachmentId": "att-001", "size": len(self._RAW), "data": self._encoded()},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(
                message_id="msg-001",
                attachment_id="att-001",
                filename="report.pdf",
                mime_type="application/pdf",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, GetAttachmentResult)
        assert result.success is True
        assert result.data == self._RAW
        assert result.size == len(self._RAW)
        assert result.filename == "report.pdf"
        assert result.mime_type == "application/pdf"

    async def test_encodes_message_and_attachment_ids_in_request_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}/attachments/att%3F1%232",
            json={"attachmentId": "att?1#2", "size": len(self._RAW), "data": self._encoded()},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id=_TRICKY_ID, attachment_id="att?1#2"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.data == self._RAW

    async def test_success_without_hints_uses_defaults(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-002",
            json={"attachmentId": "att-002", "size": len(self._RAW), "data": self._encoded()},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="att-002"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.filename == "attachment"
        assert result.mime_type == "application/octet-stream"

    async def test_result_round_trips_into_file_from_bytes(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-001",
            json={"attachmentId": "att-001", "size": len(self._RAW), "data": self._encoded()},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(
                message_id="msg-001",
                attachment_id="att-001",
                filename="report.pdf",
                mime_type="application/pdf",
            ),
            token=_TOKEN,
        )

        # A cross-tool caller receives the JSON-serialized result (where
        # ``data`` is a base64 string) and rebuilds a FileFromBytes from it.
        dumped = result.model_dump(mode="json")
        file_input = FileFromBytes(
            data=dumped["data"],
            filename=dumped["filename"],
            mime_type=dumped["mime_type"],
        )
        assert file_input.data == self._RAW
        assert len(file_input.data) == result.size

    async def test_success_with_unpadded_data(self, httpx_mock: HTTPXMock) -> None:
        # Gmail commonly returns base64url data without trailing '=' padding.
        raw = b"unpadded attachment!"
        padded = base64.urlsafe_b64encode(raw).decode("ascii")
        assert padded.endswith("="), "test payload must exercise padding removal"
        unpadded = padded.rstrip("=")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-004",
            json={"attachmentId": "att-004", "size": len(raw), "data": unpadded},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="att-004"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.data == raw
        assert result.size == len(raw)

    async def test_success_with_unpadded_data_requiring_double_padding(self, httpx_mock: HTTPXMock) -> None:
        # Unlike test_success_with_unpadded_data above, which only strips one
        # padding character, this payload requires two ('==').
        raw = b"unpadded pdf report bytes"
        padded = base64.urlsafe_b64encode(raw).decode("ascii")
        assert padded.endswith("=="), "test payload must require two padding characters"
        unpadded = padded.rstrip("=")

        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-006",
            json={"attachmentId": "att-006", "size": len(raw), "data": unpadded},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="att-006"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.data == raw
        assert result.size == len(raw)

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-005",
            status_code=200,
            text="<html>not json</html>",
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="att-005"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "json" in result.error.lower()
        assert result.data == b""

    async def test_empty_data(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001/attachments/att-003",
            json={"attachmentId": "att-003", "size": 0, "data": ""},
        )

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="att-003"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.data == b""
        assert "no data" in result.error.lower()

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_get_attachment(
            GetAttachmentParams(message_id="msg-001", attachment_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error
        assert result.data == b""

    async def test_has_tool_definition(self) -> None:
        defn = gmail_get_attachment._tool_definition
        assert defn.name == "gmail_get_attachment"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.readonly" in defn.scopes
