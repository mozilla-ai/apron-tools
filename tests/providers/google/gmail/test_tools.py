"""Tests for Gmail tool functions."""

from __future__ import annotations

import base64
import email
import json
from email import policy
from email.message import EmailMessage
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

    @pytest.mark.parametrize(
        ("charset", "body"),
        [
            ("iso-2022-jp", "\u304a\u8336\u3092\u3069\u3046\u305e"),
            ("iso-8859-1", "Caf\u00e9 au lait"),
            ("windows-1252", "A \u201cquoted\u201d caf\u00e9"),
            ("gbk", "\u4e00\u4e0c\u4e10"),
            ("big5", "\u4e33\u4e83\u4e84"),
        ],
        ids=["iso-2022-jp", "latin-1", "windows-1252", "gbk", "big5"],
    )
    async def test_read_email_decodes_a_part_with_its_declared_charset(
        self, httpx_mock: HTTPXMock, charset: str, body: str
    ) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "text/plain",
            "headers": [{"name": "Content-Type", "value": f'text/plain; charset="{charset}"'}],
            "body": {"data": _b64(body.encode(charset))},
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == body

    @pytest.mark.parametrize(
        "charset",
        ["us-ascii", "x-unknown-charset", "iso-8859-1", "windows-1252"],
        ids=["us-ascii", "unknown-charset", "latin-1", "windows-1252"],
    )
    async def test_read_email_reads_utf8_bytes_that_a_part_mislabels(self, httpx_mock: HTTPXMock, charset: str) -> None:
        body = "Caf\u00e9 \u2014 one coffee"
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "text/plain",
            "headers": [{"name": "Content-Type", "value": f"text/plain; charset={charset}"}],
            "body": {"data": _b64(body.encode())},
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == body

    async def test_read_email_reads_a_header_that_carries_no_value(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"]["headers"] = [
            {"name": "Subject", "value": None},
            {"name": "From", "value": "alice@example.com"},
        ]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.subject == ""
        assert result.from_address == "alice@example.com"

    async def test_read_email_joins_a_folded_header_value(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"]["headers"] = [
            {"name": "Subject", "value": "A very long subject\r\n that was folded"},
            {"name": "From", "value": "alice@example.com"},
        ]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.subject == "A very long subject that was folded"

    async def test_read_email_ignores_a_text_attachment_that_precedes_the_body(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "notes.txt",
                    "headers": [{"name": "Content-Disposition", "value": 'attachment; filename="notes.txt"'}],
                    "body": {"data": _b64("Attached note")},
                },
                {"mimeType": "text/plain", "body": {"data": _b64("Real body")}},
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "Real body"

    async def test_read_email_reads_the_first_body_part_in_document_order(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "filename": "message.txt",
                    "headers": [{"name": "Content-Disposition", "value": 'inline; filename="message.txt"'}],
                    "body": {"data": _b64("The body")},
                },
                {"mimeType": "text/plain", "body": {"data": _b64("-- list footer")}},
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "The body"

    @pytest.mark.parametrize(
        "headers",
        [[{"name": "Content-Disposition", "value": 'attachment; filename="forwarded.eml"'}], []],
        ids=["declared-attachment", "no-disposition"],
    )
    async def test_read_email_ignores_the_text_inside_an_attached_email(
        self, httpx_mock: HTTPXMock, headers: list[dict[str, str]]
    ) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "message/rfc822",
                    "filename": "forwarded.eml",
                    "headers": headers,
                    "parts": [{"mimeType": "text/plain", "body": {"data": _b64("Text of the attached email")}}],
                }
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "(No email body found)"

    async def test_read_email_keeps_a_body_part_that_declares_a_file_name(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "text/plain",
            "filename": "message.txt",
            "headers": [{"name": "Content-Disposition", "value": 'inline; filename="message.txt"'}],
            "body": {"data": _b64("Inline body")},
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "Inline body"

    async def test_read_email_reports_no_body_when_only_a_non_text_part_has_data(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/mixed",
            "parts": [{"mimeType": "image/png", "body": {"data": _b64(b"\x89PNG\r\n\x1a\n")}}],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "(No email body found)"

    async def test_read_email_prefers_a_plain_part_in_another_charset_over_html(self, httpx_mock: HTTPXMock) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "headers": [{"name": "Content-Type", "value": "text/plain; charset=iso-8859-1"}],
                    "body": {"data": _b64("Caf\u00e9".encode("iso-8859-1"))},
                },
                {"mimeType": "text/html", "body": {"data": _b64("<p>Cafe</p>")}},
            ],
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "Caf\u00e9"

    @pytest.mark.parametrize(
        "content_type",
        ["text/plain; charset=x-unknown-charset", "text/plain; charset=utf-8"],
        ids=["unknown-charset", "bytes-do-not-match-charset"],
    )
    async def test_read_email_reports_a_part_it_cannot_decode(self, httpx_mock: HTTPXMock, content_type: str) -> None:
        message = _load_json("get_message_full.json")
        message["payload"] = {
            "mimeType": "text/plain",
            "headers": [{"name": "Content-Type", "value": content_type}],
            "body": {"data": _b64(b"caf\xe9")},
        }
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/msg-001?format=full", json=message)

        result = await gmail_read_email(ReadEmailParams(message_id="msg-001"), token=_TOKEN)

        assert result.success is True
        assert result.body == "(Could not decode email body)"

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


def _parse_raw(raw: str) -> EmailMessage:
    message = email.message_from_bytes(base64.urlsafe_b64decode(raw), policy=policy.default)
    assert isinstance(message, EmailMessage)
    return message


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

    async def test_recipients_with_non_ascii_names_keep_their_addresses(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/send", json=_load_json("send_message.json"))

        await gmail_send_email(
            SendEmailParams(to="José <jose@example.com>", cc="Zoë <zoe@example.com>", subject="Café", body="Hi"),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        sent = _parse_raw(json.loads(request.content)["raw"])
        assert [(a.display_name, a.addr_spec) for a in sent["To"].addresses] == [("José", "jose@example.com")]
        assert [(a.display_name, a.addr_spec) for a in sent["Cc"].addresses] == [("Zoë", "zoe@example.com")]
        assert sent["Subject"] == "Café"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await gmail_send_email(
            SendEmailParams(to="bad", subject="Test", body="Body"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_a_non_ascii_body_is_sent_as_ascii_bytes(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/send", json=_load_json("send_message.json"))

        result = await gmail_send_email(
            SendEmailParams(to="bob@example.com", subject="Caf\u00e9", body="Caf\u00e9 \u2014 one coffee"),
            token=_TOKEN,
        )

        assert result.success is True
        send = next(request for request in httpx_mock.get_requests() if request.method == "POST")
        raw = base64.urlsafe_b64decode(json.loads(send.content)["raw"])
        assert raw.isascii(), "a message handed to the API must hold no 8-bit bytes"
        assert _parse_raw(json.loads(send.content)["raw"]).get_content() == "Caf\u00e9 \u2014 one coffee\r\n"

    async def test_a_body_that_cannot_be_written_is_refused(self, httpx_mock: HTTPXMock) -> None:
        result = await gmail_send_email(
            SendEmailParams(to="bob@example.com", subject="Hello", body="lone surrogate: \ud800"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient, subject or body contains a character that cannot be written to an email."
        assert httpx_mock.get_requests() == []

    @pytest.mark.parametrize(
        ("to", "subject", "cc", "bcc"),
        [
            ("one\ntwo: injected", "Hello", None, None),
            ("bob@example.com", "one\ntwo: injected", None, None),
            ("bob@example.com", "Hello", "one\ntwo: injected", None),
            ("bob@example.com", "Hello", None, "one\ntwo: injected"),
        ],
        ids=["to", "subject", "cc", "bcc"],
    )
    async def test_a_header_value_with_a_line_break_is_refused(
        self, httpx_mock: HTTPXMock, to: str, subject: str, cc: str | None, bcc: str | None
    ) -> None:
        result = await gmail_send_email(
            SendEmailParams(to=to, subject=subject, body="Hi Bob", cc=cc, bcc=bcc),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient or subject must not contain a line break."
        assert httpx_mock.get_requests() == []

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

    async def test_a_header_value_with_a_line_break_is_refused(self, httpx_mock: HTTPXMock) -> None:
        result = await gmail_create_draft(
            CreateDraftParams(to="bob@example.com", subject="one\ntwo: injected", body="Hi Bob"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient or subject must not contain a line break."
        assert httpx_mock.get_requests() == []

    async def test_has_tool_definition(self) -> None:
        defn = gmail_create_draft._tool_definition
        assert defn.name == "gmail_create_draft"
        assert defn.provider == "google"
        assert defn.service == "gmail"
        assert "https://www.googleapis.com/auth/gmail.compose" in defn.scopes


# ---------------------------------------------------------------------------
# edit_draft
# ---------------------------------------------------------------------------


def _mime(*lines: str | bytes) -> bytes:
    return b"\r\n".join(line if isinstance(line, bytes) else line.encode() for line in lines)


_DRAFT_HEADERS = (
    "From: Ana <alias@example.com>",
    "Reply-To: team@example.com",
    "To: bob@example.com",
    "Subject: Draft Subject",
    "MIME-Version: 1.0",
)

_DRAFTS = {
    "plain-text": _mime("To: bob@example.com", "Subject: Draft Subject", "", "Original body", ""),
    "html-only": _mime(*_DRAFT_HEADERS, 'Content-Type: text/html; charset="utf-8"', "", "<p>HTML only</p>", ""),
    "alternative-with-attachment": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/mixed; boundary="mixed"',
        "",
        "--mixed",
        'Content-Type: multipart/alternative; boundary="alt"',
        "",
        "--alt",
        "Content-Type: text/plain; charset=iso-8859-1",
        "Content-Transfer-Encoding: 8bit",
        "",
        b"caf\xe9 body",
        "--alt",
        'Content-Type: text/html; charset="utf-8"',
        "",
        "<p>café body</p>",
        "--alt--",
        "--mixed",
        "Content-Type: application/pdf; name=a.pdf",
        "Content-Disposition: attachment; filename=a.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "JVBERi0xLjQK",
        "--mixed--",
        "",
    ),
    "inline-image": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/related; boundary="rel"',
        "",
        "--rel",
        'Content-Type: text/html; charset="utf-8"',
        "",
        '<p><img src="cid:logo"></p>',
        "--rel",
        "Content-Type: image/png",
        "Content-ID: <logo>",
        "Content-Disposition: inline",
        "Content-Transfer-Encoding: base64",
        "",
        "iVBORw0KGgo=",
        "--rel--",
        "",
    ),
    "nested-attachment": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/alternative; boundary="alt"',
        "",
        "--alt",
        "Content-Type: text/plain",
        "",
        "plain text",
        "--alt",
        'Content-Type: multipart/mixed; boundary="mix"',
        "",
        "--mix",
        'Content-Type: text/html; charset="utf-8"',
        "",
        "<p>html</p>",
        "--mix",
        "Content-Type: application/pdf; name=a.pdf",
        "Content-Disposition: attachment; filename=a.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "JVBERi0xLjQK",
        "--mix--",
        "--alt--",
        "",
    ),
    "related-with-attachment": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/related; boundary="rel"',
        "",
        "--rel",
        'Content-Type: text/html; charset="utf-8"',
        "",
        '<p><img src="cid:logo"></p>',
        "--rel",
        "Content-Type: image/png",
        "Content-ID: <logo>",
        "Content-Disposition: inline",
        "Content-Transfer-Encoding: base64",
        "",
        "iVBORw0KGgo=",
        "--rel",
        "Content-Type: application/pdf; name=a.pdf",
        "Content-Disposition: attachment; filename=a.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "JVBERi0xLjQK",
        "--rel--",
        "",
    ),
    "related-holding-a-mixed-part": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/related; boundary="rel"',
        "",
        "--rel",
        'Content-Type: multipart/mixed; boundary="mix"',
        "",
        "--mix",
        'Content-Type: text/html; charset="utf-8"',
        "",
        '<p><img src="cid:logo"></p>',
        "--mix",
        "Content-Type: application/pdf; name=a.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "JVBERi0xLjQK",
        "--mix--",
        "--rel",
        "Content-Type: image/png",
        "Content-ID: <logo>",
        "Content-Disposition: inline",
        "Content-Transfer-Encoding: base64",
        "",
        "iVBORw0KGgo=",
        "--rel--",
        "",
    ),
    "attachment-only": _mime(
        *_DRAFT_HEADERS,
        "Content-Type: application/pdf; name=a.pdf",
        "Content-Disposition: attachment; filename=a.pdf",
        "Content-Transfer-Encoding: base64",
        "",
        "JVBERi0xLjQK",
        "",
    ),
    "attached-email": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/mixed; boundary="mixed"',
        "",
        "--mixed",
        "Content-Type: text/plain",
        "",
        "See the forwarded email.",
        "--mixed",
        "Content-Type: message/rfc822",
        "",
        "Subject: Forwarded",
        "",
        "Forwarded text",
        "--mixed--",
        "",
    ),
    "inline-text-file": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/mixed; boundary="mixed"',
        "",
        "--mixed",
        "Content-Type: text/plain",
        "",
        "Body text",
        "--mixed",
        'Content-Type: text/plain; name="notes.txt"',
        'Content-Disposition: inline; filename="notes.txt"',
        "",
        "note content",
        "--mixed--",
        "",
    ),
    "two-plain-text-parts": _mime(
        *_DRAFT_HEADERS,
        'Content-Type: multipart/mixed; boundary="mixed"',
        "",
        "--mixed",
        "Content-Type: text/plain",
        "",
        "part A",
        "--mixed",
        "Content-Type: text/plain",
        "",
        "-- list footer",
        "--mixed--",
        "",
    ),
    "iso-2022-jp": _mime(
        *_DRAFT_HEADERS, "Content-Type: text/plain; charset=ISO-2022-JP", "", "日本語".encode("iso-2022-jp"), ""
    ),
    "undecodable-part": _mime(
        *_DRAFT_HEADERS, "Content-Type: text/plain", "Content-Transfer-Encoding: base64", "", "!!!invalid!!!", ""
    ),
    "inline-body": _mime(*_DRAFT_HEADERS, "Content-Type: text/plain", "Content-Disposition: inline", "", "Body", ""),
}


def _raw_draft(raw: bytes) -> dict:
    return {"id": "draft-001", "message": {"id": "msg-004", "threadId": "thread-003", "raw": _b64(raw)}}


def _leaf_parts(message: EmailMessage) -> list[tuple[str, object]]:
    return [(part.get_content_type(), part.get_payload()) for part in message.walk() if not part.is_multipart()]


def _put_message(httpx_mock: HTTPXMock) -> dict:
    put = next(request for request in httpx_mock.get_requests() if request.method == "PUT")
    return json.loads(put.content)["message"]


class TestEditDraft:
    @pytest.mark.parametrize("raw", list(_DRAFTS.values()), ids=list(_DRAFTS))
    async def test_header_edit_keeps_the_rest_of_the_draft(self, httpx_mock: HTTPXMock, raw: bytes) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated ☕"), token=_TOKEN)

        assert result.success is True
        original = email.message_from_bytes(raw, policy=policy.default)
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert sent["Subject"] == "Updated ☕"
        assert [sent[name] for name in ("From", "Reply-To", "To")] == [
            original[name] for name in ("From", "Reply-To", "To")
        ]
        assert _leaf_parts(sent) == _leaf_parts(original)

    async def test_edit_replaces_only_the_given_headers(self, httpx_mock: HTTPXMock) -> None:
        raw = _mime(*_DRAFT_HEADERS, "Cc: old@example.com", "Bcc: dave@example.com", "", "Body", "")
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", to="José <jose@example.com>", cc="carol@example.com", bcc=""),
            token=_TOKEN,
        )

        assert result.success is True
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [(a.display_name, a.addr_spec) for a in sent["To"].addresses] == [("José", "jose@example.com")]
        assert sent.get_all("Cc") == ["carol@example.com"]
        assert "Bcc" not in sent
        assert sent["Subject"] == "Draft Subject"
        assert sent["From"] == "Ana <alias@example.com>"

    @pytest.mark.parametrize(
        ("header", "to", "subject", "cc", "bcc"),
        [
            ("To", "", None, None, None),
            ("Subject", None, "", None, None),
            ("Cc", None, None, "", None),
            ("Bcc", None, None, None, ""),
        ],
        ids=["to", "subject", "cc", "bcc"],
    )
    async def test_an_empty_value_clears_a_header(
        self,
        httpx_mock: HTTPXMock,
        header: str,
        to: str | None,
        subject: str | None,
        cc: str | None,
        bcc: str | None,
    ) -> None:
        raw = _mime(*_DRAFT_HEADERS, "Cc: carol@example.com", "Bcc: dan@example.com", "", "Original body", "")
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", to=to, subject=subject, cc=cc, bcc=bcc),
            token=_TOKEN,
        )

        assert result.success is True
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert sent[header] is None
        assert sent.get_content() == "Original body\r\n"

    @pytest.mark.parametrize("draft", ["html-only", "inline-image"])
    async def test_new_body_replaces_the_text_and_html(self, httpx_mock: HTTPXMock, draft: str) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(_DRAFTS[draft]))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert sent.get_content_type() == "text/plain"
        assert sent.get_content() == "New body\r\n"
        assert sent["From"] == "Ana <alias@example.com>"
        assert sent.get_all("MIME-Version") == ["1.0"]

    @pytest.mark.parametrize(
        ("draft", "parts"),
        [
            ("alternative-with-attachment", ["multipart/mixed", "text/plain", "application/pdf"]),
            ("attached-email", ["multipart/mixed", "text/plain", "message/rfc822", "text/plain"]),
        ],
    )
    async def test_new_body_keeps_attachments(self, httpx_mock: HTTPXMock, draft: str, parts: list[str]) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(_DRAFTS[draft]))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        original = email.message_from_bytes(_DRAFTS[draft], policy=policy.default)
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [part.get_content_type() for part in sent.walk()] == parts
        body = sent.get_body(("plain",))
        assert body is not None
        assert body.get_content() == "New body\r\n"
        assert [part.as_string() for part in sent.iter_attachments()] == [
            part.as_string() for part in original.iter_attachments()
        ]
        assert sent.get_all("MIME-Version") == ["1.0"]

    async def test_new_body_replaces_every_text_part(self, httpx_mock: HTTPXMock) -> None:
        draft = _DRAFTS["two-plain-text-parts"]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(draft))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert sent.get_content_type() == "text/plain"
        assert sent.get_content() == "New body\r\n"

    async def test_a_non_ascii_new_body_is_written_as_ascii_bytes(self, httpx_mock: HTTPXMock) -> None:
        draft = _DRAFTS["alternative-with-attachment"]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(draft))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", body="Caf\u00e9 \u2014 one coffee"),
            token=_TOKEN,
        )

        assert result.success is True
        raw = _put_message(httpx_mock)["raw"]
        assert base64.urlsafe_b64decode(raw).isascii(), "a message handed to the API must hold no 8-bit bytes"
        sent = _parse_raw(raw)
        body = sent.get_body(("plain",))
        assert body is not None
        assert body.get_content() == "Caf\u00e9 \u2014 one coffee\r\n"

    async def test_new_body_keeps_a_text_file_that_a_draft_holds(self, httpx_mock: HTTPXMock) -> None:
        draft = _DRAFTS["inline-text-file"]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(draft))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [part.get_content_type() for part in sent.walk()] == ["multipart/mixed", "text/plain", "text/plain"]
        kept = sent.get_payload()[1]
        assert kept.get_filename() == "notes.txt"
        assert kept.get_content() == "note content"

    @pytest.mark.parametrize("draft", ["related-holding-a-mixed-part", "attachment-only"], ids=["related", "bare"])
    async def test_new_body_keeps_a_file_that_no_part_marks_as_an_attachment(
        self, httpx_mock: HTTPXMock, draft: str
    ) -> None:
        raw = _DRAFTS[draft]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        original = email.message_from_bytes(raw, policy=policy.default)
        original_pdf = next(part for part in original.walk() if part.get_filename() == "a.pdf")
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [part.get_content_type() for part in sent.walk()] == [
            "multipart/mixed",
            "text/plain",
            "application/pdf",
        ]
        assert [part.as_string() for part in sent.iter_attachments()] == [original_pdf.as_string()]

    async def test_new_body_keeps_an_attachment_inside_a_nested_part(self, httpx_mock: HTTPXMock) -> None:
        draft = _DRAFTS["nested-attachment"]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(draft))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        original = email.message_from_bytes(draft, policy=policy.default)
        original_pdf = next(part for part in original.walk() if part.get_filename() == "a.pdf")
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [part.get_content_type() for part in sent.walk()] == [
            "multipart/mixed",
            "text/plain",
            "application/pdf",
        ]
        assert [part.as_string() for part in sent.iter_attachments()] == [original_pdf.as_string()]

    async def test_new_body_keeps_an_attachment_of_a_related_draft(self, httpx_mock: HTTPXMock) -> None:
        draft = _DRAFTS["related-with-attachment"]
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(draft))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        original = email.message_from_bytes(draft, policy=policy.default)
        original_pdf = next(part for part in original.iter_attachments() if part.get_filename() == "a.pdf")
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert [part.get_content_type() for part in sent.walk()] == [
            "multipart/mixed",
            "text/plain",
            "application/pdf",
        ]
        assert [part.as_string() for part in sent.iter_attachments()] == [original_pdf.as_string()]

    async def test_edit_keeps_reply_draft_in_its_thread(self, httpx_mock: HTTPXMock) -> None:
        raw = _mime(*_DRAFT_HEADERS, "In-Reply-To: <orig@example.com>", "", "Body", "")
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", body="New body"), token=_TOKEN)

        assert result.success is True
        message = _put_message(httpx_mock)
        assert message["threadId"] == "thread-003"
        assert _parse_raw(message["raw"])["In-Reply-To"] == "<orig@example.com>"

    @pytest.mark.parametrize(
        ("headers", "params"),
        [
            ((), {"body": "New body"}),
            (("In-Reply-To: <orig@example.com>",), {"subject": "New subject"}),
        ],
        ids=["standalone-draft", "reply-draft-with-new-subject"],
    )
    async def test_edit_sends_no_thread_id_when_the_draft_cannot_stay_in_its_thread(
        self, httpx_mock: HTTPXMock, headers: tuple[str, ...], params: dict[str, str]
    ) -> None:
        raw = _mime(*_DRAFT_HEADERS, *headers, "", "Body", "")
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", **params), token=_TOKEN)

        assert result.success is True
        assert "threadId" not in _put_message(httpx_mock)

    async def test_edit_reads_header_names_in_any_case(self, httpx_mock: HTTPXMock) -> None:
        raw = _mime("to: bob@example.com", "subject: Draft Subject", "in-reply-to: <orig@example.com>", "", "Body", "")
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(raw))
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001", json=_load_json("edit_draft.json"))

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", to="carol@example.com"), token=_TOKEN)

        assert result.success is True
        message = _put_message(httpx_mock)
        assert message["threadId"] == "thread-003"
        assert _parse_raw(message["raw"]).get_all("To") == ["carol@example.com"]

    @pytest.mark.parametrize(
        "message",
        [{"id": "msg-004"}, {"id": "msg-004", "raw": "!!!invalid!!!"}, None],
        ids=["missing-raw", "invalid-raw", "no-message"],
    )
    async def test_unreadable_draft_is_not_overwritten(self, httpx_mock: HTTPXMock, message: dict | None) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json={"id": "draft-001", "message": message}
        )

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)

        assert result.success is False
        assert result.error == "The existing draft could not be read."
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw",
            json=_raw_draft(_DRAFTS["plain-text"]),
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
        sent = _parse_raw(_put_message(httpx_mock)["raw"])
        assert sent["Subject"] == "Updated Subject"
        assert sent.get_content() == "Original body\r\n"

    async def test_encodes_draft_id_in_request_paths(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/{_TRICKY_ID_ENC}?format=raw",
            json=_raw_draft(_DRAFTS["plain-text"]),
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

    async def test_a_draft_response_that_is_not_json_is_reported(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", text="<html>not json</html>")

        result = await gmail_edit_draft(EditDraftParams(draft_id="draft-001", subject="Updated"), token=_TOKEN)

        assert result.success is False
        assert result.error == "The existing draft could not be read."
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    async def test_a_body_that_cannot_be_written_leaves_the_draft_alone(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(_DRAFTS["plain-text"])
        )

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", body="lone surrogate: \ud800"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient, subject or body contains a character that cannot be written to an email."
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

    async def test_a_header_value_with_a_line_break_leaves_the_draft_alone(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/drafts/draft-001?format=raw", json=_raw_draft(_DRAFTS["plain-text"])
        )

        result = await gmail_edit_draft(
            EditDraftParams(draft_id="draft-001", subject="one\ntwo: injected"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient or subject must not contain a line break."
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
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
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
            url=f"{_GMAIL_BASE}/messages/{_TRICKY_ID_ENC}?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
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

    async def test_reply_to_a_sender_with_a_non_ascii_name_keeps_the_address(self, httpx_mock: HTTPXMock) -> None:
        original = _load_json("get_message_for_reply.json")
        original["payload"]["headers"][0]["value"] = "José Núñez <jose@example.com>"
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=original,
        )
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/send", json=_load_json("send_reply.json"))

        await gmail_reply_to_email(ReplyToEmailParams(message_id="msg-001", body="Thanks"), token=_TOKEN)

        send = httpx_mock.get_requests()[-1]
        sent = _parse_raw(json.loads(send.content)["raw"])
        assert [(a.display_name, a.addr_spec) for a in sent["To"].addresses] == [("José Núñez", "jose@example.com")]

    async def test_fetch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="bad-id", body="Reply"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_reply_goes_to_the_reply_to_address(self, httpx_mock: HTTPXMock) -> None:
        original = _load_json("get_message_for_reply.json")
        original["payload"]["headers"] = [
            {"name": "From", "value": "notifications@example.com"},
            {"name": "Reply-To", "value": "thread@example.com"},
            {"name": "Subject", "value": "Re: Ticket 7"},
            {"name": "Message-ID", "value": "<ticket-7@example.com>"},
        ]
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=original,
        )
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/send", json=_load_json("send_reply.json"))

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="msg-001", body="Thanks!"),
            token=_TOKEN,
        )

        assert result.success is True
        send = next(request for request in httpx_mock.get_requests() if request.method == "POST")
        sent = _parse_raw(json.loads(send.content)["raw"])
        assert sent.get_all("To") == ["thread@example.com"]

    async def test_reply_keeps_a_folded_references_header(self, httpx_mock: HTTPXMock) -> None:
        original = _load_json("get_message_for_reply.json")
        original["payload"]["headers"] = [
            {"name": "From", "value": "alice@example.com"},
            {"name": "Subject", "value": "Long thread"},
            {"name": "Message-ID", "value": "<third@example.com>"},
            {"name": "References", "value": "<first@example.com>\r\n <second@example.com>"},
        ]
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=original,
        )
        httpx_mock.add_response(url=f"{_GMAIL_BASE}/messages/send", json=_load_json("send_reply.json"))

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="msg-001", body="Thanks!"),
            token=_TOKEN,
        )

        assert result.success is True
        send = next(request for request in httpx_mock.get_requests() if request.method == "POST")
        sent = _parse_raw(json.loads(send.content)["raw"])
        assert sent["References"].split() == [
            "<first@example.com>",
            "<second@example.com>",
            "<third@example.com>",
        ]

    async def test_a_header_value_with_a_line_break_is_refused(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GMAIL_BASE}/messages/msg-001?format=metadata&metadataHeaders=From&metadataHeaders=Reply-To&metadataHeaders=To&metadataHeaders=Subject&metadataHeaders=Message-ID&metadataHeaders=References",
            json=_load_json("get_message_for_reply.json"),
        )

        result = await gmail_reply_to_email(
            ReplyToEmailParams(message_id="msg-001", body="Thanks!", cc="one\ntwo: injected"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "A recipient or subject must not contain a line break."
        assert [request.method for request in httpx_mock.get_requests()] == ["GET"]

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
