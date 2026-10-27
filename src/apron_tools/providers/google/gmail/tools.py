"""Gmail tool functions for interacting with the Gmail REST API."""

from __future__ import annotations

import base64
import copy
import email
import re
from collections.abc import Iterator
from email import policy
from email.message import EmailMessage, Message, MIMEPart
from email.utils import getaddresses

import httpx

from apron_tools._utils import parse_csv_ids, quote_path_segment
from apron_tools.providers.google.gmail.types import (
    AddLabelsToEmailsParams,
    CreateDraftParams,
    CreateDraftResult,
    CreateLabelParams,
    CreateLabelResult,
    EditDraftParams,
    EditDraftResult,
    EmailSummary,
    GetAttachmentParams,
    GetAttachmentResult,
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
from apron_tools.tool import tool

from .scopes import SCOPES

_GMAIL_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
_TIMEOUT = 60.0

# NOTE: These are display strings for a missing or unreadable body. Do not write them back to a message.
_BODY_DECODE_FAILED = "(Could not decode email body)"
_BODY_MEDIA_TYPES = ("text/html", "text/plain")
_BODY_NOT_FOUND = "(No email body found)"
# A source header is written back as it was read, so a long MIME boundary keeps the plain form that RFC 2046 needs.
_DRAFT_POLICY = policy.SMTP.clone(refold_source="none")

_HEADER_FOLD_PATTERN = re.compile(r"\r?\n([ \t])")
_HEADER_LINE_BREAK_ERROR = "A recipient or subject must hold a single line."
# NOTE: str.splitlines() also splits on a page break and other control characters, which end no line of an email.
_LINE_BREAK_PATTERN = re.compile(r"\r\n|[\r\n]")
# NOTE: RFC 5322 allows at most 998 octets in a line, without the line break that ends it.
_MAX_LINE_OCTETS = 998
_NON_ASCII_ADDRESS_ERROR = "A recipient address must hold only ASCII characters."
_NON_ASCII_SENDER_ERROR = "The address of the original sender must hold only ASCII characters."
_UNWRITABLE_VALUE_ERROR = "A recipient, subject or body contains a character that cannot be written to an email."


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Gmail API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _decode_base64url(data: str) -> bytes:
    """Decode Gmail base64url data, restoring the padding Gmail omits.

    The Gmail API returns ``MessagePartBody.data`` and attachment data as
    base64url that commonly drops the trailing ``=``, which
    ``base64.urlsafe_b64decode`` rejects. Restoring it is a no-op on input
    that is already padded. Decoding is strict: characters outside the
    base64url alphabet are rejected rather than silently discarded, so
    corrupt data surfaces as an error instead of truncated bytes.

    Args:
        data: The base64url-encoded string to decode, with or without padding.

    Returns:
        The decoded bytes.

    Raises:
        ValueError: If ``data`` cannot be decoded, such as an invalid length,
            a character outside the base64url alphabet, or non-ASCII input.
    """
    return base64.b64decode(data + "=" * (-len(data) % 4), altchars=b"-_", validate=True)


def _reads_any_byte(charset: str) -> bool:
    """Report whether a character set reads a single byte above ASCII, which no multi-byte character set does.

    A character set that reads any byte cannot report that its bytes hold text of another character set.
    """
    try:
        b"\xe9".decode(charset)
    except (LookupError, ValueError):
        return False
    return True


def _decode_body_data(data: str, charset: str) -> str:
    """Decode base64url body data as text, as UTF-8 where the bytes hold UTF-8, and in the given character set if not.

    NOTE: A message can declare a character set that its own bytes do not fit, most often us-ascii or a single-byte
    character set for UTF-8 bytes. Where the declared character set cannot report such a mismatch, bytes outside
    ASCII that read as UTF-8 are taken as UTF-8, because they are almost never single-byte text.

    Args:
        data: The base64url-encoded body data to decode.
        charset: The character set that the body declares.

    Returns:
        The decoded text.

    Raises:
        ValueError: If the data is not valid base64url, or the bytes fit neither character set.
    """
    decoded = _decode_base64url(data)
    if not decoded.isascii() and _reads_any_byte(charset):
        try:
            return decoded.decode("utf-8")
        except ValueError:
            pass
    try:
        return decoded.decode(charset)
    except (LookupError, ValueError):
        return decoded.decode("utf-8")


def _extract_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a single header value from a Gmail payload headers list, matching the name in any case.

    A value that is folded over several lines is joined into one line, which is how a reader of a header must take it.
    """
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return _HEADER_FOLD_PATTERN.sub(r"\1", h.get("value") or "")
    return ""


def _declared_charset(part: dict) -> str:
    """Return the character set that a Gmail payload part declares for its body, or UTF-8 if it declares none."""
    part_headers = Message()
    part_headers["Content-Type"] = _extract_header(part.get("headers", []), "Content-Type")
    return part_headers.get_content_charset() or "utf-8"


def _mime_type(part: dict) -> str:
    """Return the media type that a Gmail payload part declares, in the lower case that a comparison needs."""
    return part.get("mimeType", "").strip().lower()


def _is_attached_content(part: dict) -> bool:
    """Report whether a Gmail payload part holds content of its own rather than a piece of the message body.

    A part that declares itself an attachment holds its own content, and so does a part that holds a whole message.
    """
    part_headers = Message()
    part_headers["Content-Disposition"] = _extract_header(part.get("headers", []), "Content-Disposition")
    if part_headers.get_content_disposition() == "attachment":
        return True
    return _mime_type(part).startswith("message/")


def _walk_parts(payload: dict) -> Iterator[dict]:
    """Yield a payload and the MIME parts below it in document order, entering no part that holds content of its own.

    NOTE: The payload given is always yielded. A message whose whole content is one attached file still holds that
    file as its body.
    """
    yield payload
    for part in payload.get("parts", []):
        if not _is_attached_content(part):
            yield from _walk_parts(part)


def _body_candidates(payload: dict) -> Iterator[dict]:
    """Yield the parts of a Gmail payload that can hold the body text, in document order.

    NOTE: Some mail programs name the body part of a message, so a part that names a file is a candidate as well.
    """
    return (part for part in _walk_parts(payload) if _mime_type(part) in ("", *_BODY_MEDIA_TYPES))


def _extract_body(payload: dict) -> str | None:
    """Extract body text, preferring plain text over HTML.

    The first readable candidate part of each type wins, including nested parts.
    An unreadable part does not hide readable children or siblings.

    Args:
        payload: The Gmail message payload to read.

    Returns:
        The decoded body text, or None if there is no body data.

    Raises:
        ValueError: If body data is present but no part can be decoded.
    """
    plain_text: str | None = None
    html_text: str | None = None
    decode_failed = False

    for part in _body_candidates(payload):
        part_data = part.get("body", {}).get("data", "")
        if not part_data:
            continue
        try:
            text = _decode_body_data(part_data, _declared_charset(part))
        except ValueError:
            decode_failed = True
            continue

        if _mime_type(part) == "text/html":
            if html_text is None:
                html_text = text
        elif plain_text is None:
            plain_text = text

    if plain_text is not None:
        return plain_text
    if html_text is not None:
        return html_text
    if decode_failed:
        raise ValueError("Could not decode email body")
    return None


def _parse_raw_message(raw: str) -> EmailMessage:
    """Parse a base64url-encoded email message from the Gmail API, writing each header it holds back as it was read.

    NOTE: A header that carries raw 8-bit bytes is written back as an encoded word of an unknown character set,
    because the bytes themselves name no character set.

    Raises:
        ValueError: If ``raw`` cannot be decoded.
    """
    return email.message_from_bytes(_decode_base64url(raw), policy=_DRAFT_POLICY)


def _attached_files(part: MIMEPart, *, in_related: bool) -> Iterator[MIMEPart]:
    """Yield the parts of a message that hold an attached file, from any depth of its MIME tree.

    A part is yielded whole, so an attached email or an attached group of parts keeps the parts it holds.

    Args:
        part: The message or the message part to read.
        in_related: True when a multipart/related part holds ``part`` directly, which makes an inline ``part`` a
            piece of the HTML of that message rather than a file of its own.

    Yields:
        Each part that holds an attached file.
    """
    if part.is_attachment():
        yield part
        return
    if part.get_content_maintype() == "multipart":
        holds_inline_parts = part.get_content_type() == "multipart/related"
        for child in part.iter_parts():
            yield from _attached_files(child, in_related=holds_inline_parts)
        return
    # The HTML of a multipart/related message names each inline part of it by content ID or by content location, so
    # such a part is no file.
    if in_related and (part["Content-ID"] or part["Content-Location"]):
        return
    # A text part holds body text unless it names a file, so only those two kinds of part are files here.
    if part.get_filename() or part.get_content_type() not in _BODY_MEDIA_TYPES:
        yield part


def _holds_body_text(message: MIMEPart) -> bool:
    """Report whether a message holds a text part of its own, which an edit of the body replaces."""
    in_a_file = {id(part) for file in _attached_files(message, in_related=False) for part in file.walk()}
    return any(part.get_content_type() in _BODY_MEDIA_TYPES and id(part) not in in_a_file for part in message.walk())


def _content_only(message: EmailMessage) -> MIMEPart:
    """Copy a message into a part that carries only its content headers and its content.

    An envelope header inside a part reads as body text, and a copy of a Bcc address there would reach every
    recipient of the message.
    """
    part = copy.deepcopy(message)
    for name, _ in message.items():
        if not name.lower().startswith("content-"):
            del part[name]
    return part


def _replace_body(message: EmailMessage, body: str) -> None:
    """Replace the text and HTML of a message with a plain-text body, keeping its attached files."""
    # A message that is itself one attached file is copied, because the clearing below would empty it.
    attachments = [
        _content_only(part) if part is message else part for part in _attached_files(message, in_related=False)
    ]
    # NOTE: Some mail programs name the body part of a message. Such a part holds the body where the draft holds no
    # other text, so the new body takes its place instead of standing beside it.
    if not _holds_body_text(message):
        named_body = next(
            (part for part in attachments if not part.is_attachment() and part.get_content_type() in _BODY_MEDIA_TYPES),
            None,
        )
        if named_body is not None:
            attachments.remove(named_body)
    message.clear_content()
    # NOTE: The draft keeps the policy that read it, which allows 8-bit content and does not wrap a long line, so
    # the new body names an encoding of its own. A part that the edit does not write keeps the encoding it came with.
    # An 8-bit part of the draft therefore stays 8-bit, which keeps the content of the draft exactly as it was.
    lines = _LINE_BREAK_PATTERN.split(body)
    plain_ascii = body.isascii() and all(len(line) <= _MAX_LINE_OCTETS for line in lines)
    message.set_content(body, cte="7bit" if plain_ascii else "quoted-printable")
    if attachments:
        message.make_mixed()
        for attachment in attachments:
            message.attach(attachment)


def _replace_headers(message: EmailMessage, params: EditDraftParams) -> None:
    """Replace each header that ``params`` gives a value for, and remove a header whose value is empty.

    Raises:
        ValueError: If a value contains a line break.
    """
    for name, value in (("To", params.to), ("Subject", params.subject), ("Cc", params.cc), ("Bcc", params.bcc)):
        if value is not None:
            del message[name]
            if value:
                message[name] = value


def _addresses_are_ascii(*values: str | None) -> bool:
    """Report whether every address in the given recipient values holds only ASCII characters.

    NOTE: An email carries an address outside ASCII only where both servers support it, and the Gmail API takes no
    such address. The display name of an address is free to hold any character.
    """
    for value in values:
        if not value:
            continue
        # NOTE: getaddresses() reads no address at all from a value it cannot parse. Such a value is measured whole,
        # because the part of it that is a display name is unknown.
        addresses = [address for _, address in getaddresses([value]) if address]
        if not all(part.isascii() for part in addresses or [value]):
            return False
    return True


def _values_are_one_line(*values: str | None) -> bool:
    """Report whether every given header value holds a single line.

    NOTE: A header store divides a value on every character that str.splitlines() divides on, so a page break counts
    here as well. A break at the end of a value is written as an encoded word, which hides a broken address.
    """
    return all(value.splitlines() == [value] for value in values if value)


def _build_raw_message(
    to: str,
    subject: str,
    body: str,
    *,
    cc: str | None = None,
    bcc: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    """Construct a base64url-encoded MIME message for the Gmail send API.

    Raises:
        ValueError: If a header value contains a line break, or a value cannot be written to an email.
    """
    # NOTE: A 7-bit message holds no 8-bit bytes, which every mail server carries. An edited draft keeps the
    # encoding of each part that the edit does not write, so an edit never rewrites content that it did not change.
    message = EmailMessage(policy=policy.SMTP.clone(cte_type="7bit"))
    message["To"] = to
    message["Subject"] = subject
    if cc:
        message["Cc"] = cc
    if bcc:
        message["Bcc"] = bcc
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")


@tool(
    scopes=SCOPES["gmail_list_emails"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list",
    provider="google",
    service="gmail",
)
async def gmail_list_emails(
    params: ListEmailsParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ListEmailsResult:
    """List Gmail messages matching a search query."""
    query_params: dict[str, str | int] = {"maxResults": params.max_results}
    if params.query:
        query_params["q"] = params.query

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/messages",
                headers=_headers(token),
                params=query_params,
            )

            if not resp.is_success:
                return ListEmailsResult(
                    success=False,
                    error=f"Gmail API error {resp.status_code}: {resp.text}",
                )

            data = resp.json()
            messages = data.get("messages", [])
            if not messages:
                return ListEmailsResult(success=True, emails=[])

            # Fetch metadata for each message to build summaries.
            emails: list[EmailSummary] = []
            for msg_stub in messages:
                msg_id = msg_stub.get("id") or ""
                if not msg_id:
                    continue
                detail_resp = await client.get(
                    f"{base_url}/messages/{quote_path_segment(msg_id)}",
                    headers=_headers(token),
                    params={
                        "format": "metadata",
                        "metadataHeaders": ["From", "To", "Subject", "Date"],
                    },
                )
                if not detail_resp.is_success:
                    continue
                msg_data = detail_resp.json()
                hdrs = msg_data.get("payload", {}).get("headers", [])
                emails.append(
                    EmailSummary(
                        id=msg_id,
                        thread_id=msg_data.get("threadId", ""),  # ty: ignore[unknown-argument]
                        subject=_extract_header(hdrs, "Subject"),
                        from_address=_extract_header(hdrs, "From"),
                        to_address=_extract_header(hdrs, "To"),
                        date=_extract_header(hdrs, "Date"),
                        snippet=msg_data.get("snippet", ""),
                    )
                )

            return ListEmailsResult(success=True, emails=emails)
    except httpx.HTTPError as exc:
        return ListEmailsResult(success=False, error=str(exc))


@tool(
    scopes=SCOPES["gmail_read_email"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get",
    provider="google",
    service="gmail",
)
async def gmail_read_email(
    params: ReadEmailParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ReadEmailResult:
    """Read the full content of a Gmail message."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/messages/{quote_path_segment(params.message_id)}",
                headers=_headers(token),
                params={"format": "full"},
            )
    except httpx.HTTPError as exc:
        return ReadEmailResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadEmailResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    payload = data.get("payload", {})
    hdrs = payload.get("headers", [])

    try:
        body = _extract_body(payload)
    except ValueError:
        body = _BODY_DECODE_FAILED
    else:
        if body is None:
            body = _BODY_NOT_FOUND

    return ReadEmailResult(
        success=True,
        id=data.get("id", ""),
        thread_id=data.get("threadId", ""),
        subject=_extract_header(hdrs, "Subject"),
        from_address=_extract_header(hdrs, "From"),
        to_address=_extract_header(hdrs, "To"),
        cc=_extract_header(hdrs, "Cc"),
        date=_extract_header(hdrs, "Date"),
        body=body,
        label_ids=data.get("labelIds", []),
    )


@tool(
    scopes=SCOPES["gmail_get_attachment"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get",
    provider="google",
    service="gmail",
)
async def gmail_get_attachment(
    params: GetAttachmentParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> GetAttachmentResult:
    """Download a Gmail message attachment as raw bytes for cross-tool upload.

    Gmail returns the attachment base64url-encoded with a size field but
    no filename or MIME type; the bytes are decoded here so callers get
    raw content, and filename/MIME type fall back to the caller-supplied
    hints (or generic defaults) since the endpoint does not provide them.
    """
    path = f"messages/{quote_path_segment(params.message_id)}/attachments/{quote_path_segment(params.attachment_id)}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/{path}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetAttachmentResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetAttachmentResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    try:
        encoded = resp.json().get("data", "")
    except ValueError:
        return GetAttachmentResult(success=False, error="Gmail response was not valid JSON.")

    if not encoded:
        return GetAttachmentResult(success=False, error="Attachment contained no data.")

    try:
        raw = _decode_base64url(encoded)
    except ValueError:
        return GetAttachmentResult(success=False, error="Could not decode attachment data.")

    return GetAttachmentResult(
        success=True,
        data=base64.b64encode(raw),
        filename=params.filename or "attachment",
        mime_type=params.mime_type or "application/octet-stream",
        size=len(raw),
    )


@tool(
    scopes=SCOPES["gmail_send_email"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send",
    provider="google",
    service="gmail",
)
async def gmail_send_email(
    params: SendEmailParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> SendEmailResult:
    """Send an email via Gmail."""
    if not _addresses_are_ascii(params.to, params.cc, params.bcc):
        return SendEmailResult(success=False, error=_NON_ASCII_ADDRESS_ERROR)

    if not _values_are_one_line(params.to, params.subject, params.cc, params.bcc):
        return SendEmailResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

    try:
        raw = _build_raw_message(
            params.to,
            params.subject,
            params.body,
            cc=params.cc,
            bcc=params.bcc,
        )
    except ValueError:
        return SendEmailResult(success=False, error=_UNWRITABLE_VALUE_ERROR)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/messages/send",
                headers=_headers(token, content_type=True),
                json={"raw": raw},
            )
    except httpx.HTTPError as exc:
        return SendEmailResult(success=False, error=str(exc))

    if not resp.is_success:
        return SendEmailResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return SendEmailResult(
        success=True,
        id=data.get("id", ""),
        thread_id=data.get("threadId", ""),
    )


@tool(
    scopes=SCOPES["gmail_create_draft"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/create",
    provider="google",
    service="gmail",
)
async def gmail_create_draft(
    params: CreateDraftParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> CreateDraftResult:
    """Create an email draft in Gmail."""
    if not _addresses_are_ascii(params.to, params.cc, params.bcc):
        return CreateDraftResult(success=False, error=_NON_ASCII_ADDRESS_ERROR)

    if not _values_are_one_line(params.to, params.subject, params.cc, params.bcc):
        return CreateDraftResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

    try:
        raw = _build_raw_message(
            params.to,
            params.subject,
            params.body,
            cc=params.cc,
            bcc=params.bcc,
        )
    except ValueError:
        return CreateDraftResult(success=False, error=_UNWRITABLE_VALUE_ERROR)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/drafts",
                headers=_headers(token, content_type=True),
                json={"message": {"raw": raw}},
            )
    except httpx.HTTPError as exc:
        return CreateDraftResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateDraftResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    return CreateDraftResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["gmail_edit_draft"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/update",
    provider="google",
    service="gmail",
)
async def gmail_edit_draft(
    params: EditDraftParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> EditDraftResult:
    """Edit the To, Subject, Cc, Bcc or body of a Gmail draft. Everything the call does not give stays as it is."""
    draft_url = f"{base_url}/drafts/{quote_path_segment(params.draft_id)}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            get_resp = await client.get(
                draft_url,
                headers=_headers(token),
                params={"format": "raw"},
            )

            if not get_resp.is_success:
                return EditDraftResult(
                    success=False,
                    error=f"Gmail API error {get_resp.status_code}: {get_resp.text}",
                )

            try:
                draft_message = get_resp.json()["message"]
                message = _parse_raw_message(draft_message["raw"])
            except (KeyError, TypeError, ValueError):
                return EditDraftResult(success=False, error="The existing draft could not be read.")

            if not _addresses_are_ascii(params.to, params.cc, params.bcc):
                return EditDraftResult(success=False, error=_NON_ASCII_ADDRESS_ERROR)

            if not _values_are_one_line(params.to, params.subject, params.cc, params.bcc):
                return EditDraftResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

            original_subject = message.get("Subject", "")
            try:
                _replace_headers(message, params)
                if params.body is not None:
                    _replace_body(message, params.body)
                edited_raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            except ValueError:
                return EditDraftResult(success=False, error=_UNWRITABLE_VALUE_ERROR)

            update: dict[str, str] = {"raw": edited_raw}
            thread_id = draft_message.get("threadId")
            is_reply = "In-Reply-To" in message or "References" in message
            # Gmail keeps a message in a thread only when it has reply headers and the same subject.
            if thread_id and is_reply and message.get("Subject", "") == original_subject:
                update["threadId"] = thread_id

            put_resp = await client.put(
                draft_url,
                headers=_headers(token, content_type=True),
                json={"message": update},
            )
    except httpx.HTTPError as exc:
        return EditDraftResult(success=False, error=str(exc))

    if not put_resp.is_success:
        return EditDraftResult(
            success=False,
            error=f"Gmail API error {put_resp.status_code}: {put_resp.text}",
        )

    return EditDraftResult.model_validate(put_resp.json())


@tool(
    scopes=SCOPES["gmail_reply_to_email"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send",
    provider="google",
    service="gmail",
)
async def gmail_reply_to_email(
    params: ReplyToEmailParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ReplyToEmailResult:
    """Reply to an email, keeping it in the same thread."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the original message to obtain threading headers.
            orig_resp = await client.get(
                f"{base_url}/messages/{quote_path_segment(params.message_id)}",
                headers=_headers(token),
                params={
                    "format": "metadata",
                    "metadataHeaders": ["From", "Reply-To", "To", "Subject", "Message-ID", "References"],
                },
            )

            if not orig_resp.is_success:
                return ReplyToEmailResult(
                    success=False,
                    error=f"Gmail API error {orig_resp.status_code}: {orig_resp.text}",
                )

            orig_data = orig_resp.json()
            thread_id = orig_data.get("threadId", "")
            hdrs = orig_data.get("payload", {}).get("headers", [])

            orig_from = _extract_header(hdrs, "From")
            orig_reply_to = _extract_header(hdrs, "Reply-To")
            orig_subject = _extract_header(hdrs, "Subject")
            orig_message_id = _extract_header(hdrs, "Message-ID")
            orig_references = _extract_header(hdrs, "References")

            reply_subject = orig_subject
            if not reply_subject.lower().startswith("re:"):
                reply_subject = f"Re: {reply_subject}"

            references = orig_references
            if orig_message_id:
                references = f"{references} {orig_message_id}" if references else orig_message_id

            if not _addresses_are_ascii(orig_reply_to or orig_from):
                return ReplyToEmailResult(success=False, error=_NON_ASCII_SENDER_ERROR)

            if not _addresses_are_ascii(params.cc, params.bcc):
                return ReplyToEmailResult(success=False, error=_NON_ASCII_ADDRESS_ERROR)

            if not _values_are_one_line(params.cc, params.bcc):
                return ReplyToEmailResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

            try:
                raw = _build_raw_message(
                    orig_reply_to or orig_from,
                    reply_subject,
                    params.body,
                    cc=params.cc,
                    bcc=params.bcc,
                    in_reply_to=orig_message_id or None,
                    references=references or None,
                )
            except ValueError:
                return ReplyToEmailResult(success=False, error=_UNWRITABLE_VALUE_ERROR)

            send_resp = await client.post(
                f"{base_url}/messages/send",
                headers=_headers(token, content_type=True),
                json={"raw": raw, "threadId": thread_id},
            )
    except httpx.HTTPError as exc:
        return ReplyToEmailResult(success=False, error=str(exc))

    if not send_resp.is_success:
        return ReplyToEmailResult(
            success=False,
            error=f"Gmail API error {send_resp.status_code}: {send_resp.text}",
        )

    send_data = send_resp.json()
    return ReplyToEmailResult(
        success=True,
        id=send_data.get("id", ""),
        thread_id=send_data.get("threadId", ""),
    )


@tool(
    scopes=SCOPES["gmail_get_thread_replies"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads/get",
    provider="google",
    service="gmail",
)
async def gmail_get_thread_replies(
    params: GetThreadRepliesParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> GetThreadRepliesResult:
    """Get all messages in a Gmail thread."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/threads/{quote_path_segment(params.thread_id)}",
                headers=_headers(token),
                params={
                    "format": "metadata",
                    "metadataHeaders": ["From", "To", "Subject", "Date"],
                },
            )
    except httpx.HTTPError as exc:
        return GetThreadRepliesResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetThreadRepliesResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    raw_messages = data.get("messages", [])

    subject = ""
    if raw_messages:
        first_hdrs = raw_messages[0].get("payload", {}).get("headers", [])
        subject = _extract_header(first_hdrs, "Subject")

    thread_messages: list[ThreadMessage] = []
    for msg in raw_messages:
        msg_hdrs = msg.get("payload", {}).get("headers", [])
        thread_messages.append(
            ThreadMessage(
                id=msg.get("id", ""),
                from_address=_extract_header(msg_hdrs, "From"),
                to_address=_extract_header(msg_hdrs, "To"),
                date=_extract_header(msg_hdrs, "Date"),
                snippet=msg.get("snippet", ""),
            )
        )

    return GetThreadRepliesResult(
        success=True,
        thread_id=data.get("id", ""),
        subject=subject,
        messages=thread_messages,
    )


@tool(
    scopes=SCOPES["gmail_list_labels"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels/list",
    provider="google",
    service="gmail",
)
async def gmail_list_labels(
    params: ListLabelsParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ListLabelsResult:
    """List all Gmail labels."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/labels",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ListLabelsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListLabelsResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    labels = [GmailLabel.model_validate(lbl) for lbl in data.get("labels", [])]
    return ListLabelsResult(success=True, labels=labels)


async def _modify_message_labels(
    client: httpx.AsyncClient,
    base_url: str,
    token: str,
    message_id: str,
    add_label_ids: list[str],
    remove_label_ids: list[str],
) -> ModifyLabelsItem:
    """Send a single Gmail messages.modify request and shape the per-item outcome."""
    try:
        resp = await client.post(
            f"{base_url}/messages/{quote_path_segment(message_id)}/modify",
            headers=_headers(token, content_type=True),
            json={"addLabelIds": add_label_ids, "removeLabelIds": remove_label_ids},
        )
    except httpx.HTTPError as exc:
        return ModifyLabelsItem(message_id=message_id, success=False, error=str(exc))

    if not resp.is_success:
        return ModifyLabelsItem(
            message_id=message_id,
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return ModifyLabelsItem(
        message_id=data.get("id", message_id),
        label_ids=list(data.get("labelIds", [])),
        success=True,
    )


@tool(
    scopes=SCOPES["gmail_add_labels_to_emails"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/modify",
    provider="google",
    service="gmail",
)
async def gmail_add_labels_to_emails(
    params: AddLabelsToEmailsParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ModifyLabelsResult:
    """Add one or more labels to one or more Gmail messages."""
    message_ids = parse_csv_ids(params.message_ids)
    label_ids = parse_csv_ids(params.label_ids)
    if not message_ids:
        return ModifyLabelsResult(success=False, error="No message IDs provided.")
    if not label_ids:
        return ModifyLabelsResult(success=False, error="No label IDs provided.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        items = [await _modify_message_labels(client, base_url, token, msg_id, label_ids, []) for msg_id in message_ids]

    return ModifyLabelsResult(success=True, items=items)


@tool(
    scopes=SCOPES["gmail_remove_labels_from_emails"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/modify",
    provider="google",
    service="gmail",
)
async def gmail_remove_labels_from_emails(
    params: RemoveLabelsFromEmailsParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> ModifyLabelsResult:
    """Remove one or more labels from one or more Gmail messages."""
    message_ids = parse_csv_ids(params.message_ids)
    label_ids = parse_csv_ids(params.label_ids)
    if not message_ids:
        return ModifyLabelsResult(success=False, error="No message IDs provided.")
    if not label_ids:
        return ModifyLabelsResult(success=False, error="No label IDs provided.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        items = [await _modify_message_labels(client, base_url, token, msg_id, [], label_ids) for msg_id in message_ids]

    return ModifyLabelsResult(success=True, items=items)


@tool(
    scopes=SCOPES["gmail_create_label"],
    api_docs="https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.labels/create",
    provider="google",
    service="gmail",
)
async def gmail_create_label(
    params: CreateLabelParams,
    *,
    token: str,
    base_url: str = _GMAIL_BASE_URL,
) -> CreateLabelResult:
    """Create a new user-defined Gmail label.

    Gmail treats "/" as a display-nesting separator, so passing
    "Projects/Acme" creates a single label that appears nested under
    "Projects" in the Gmail UI. Label names must be unique per user.
    """
    label_name = params.name.strip()
    if not label_name:
        return CreateLabelResult(
            success=False,
            error="Label name must not be empty.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/labels",
                headers=_headers(token, content_type=True),
                json={"name": label_name},
            )
    except httpx.HTTPError as exc:
        return CreateLabelResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateLabelResult(
            success=False,
            error=f"Gmail API error {resp.status_code}: {resp.text}",
        )

    return CreateLabelResult.model_validate(resp.json())
