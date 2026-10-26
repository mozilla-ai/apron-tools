"""Gmail tool functions for interacting with the Gmail REST API."""

from __future__ import annotations

import base64
import email
import re
from collections.abc import Iterator
from email import policy
from email.message import EmailMessage, Message, MIMEPart

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
_BODY_NOT_FOUND = "(No email body found)"

_HEADER_FOLD_PATTERN = re.compile(r"\r?\n([ \t])")
_HEADER_LINE_BREAK_ERROR = "A recipient or subject must not contain a line break."
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


def _decode_body_data(data: str, charset: str) -> str:
    """Decode base64url body data as text, as UTF-8 where the bytes hold UTF-8, and in the given character set if not.

    NOTE: A message can declare a character set that its own bytes do not fit, most often us-ascii or a single-byte
    character set for UTF-8 bytes. A single-byte character set reads any byte, so it cannot report the mismatch.
    Bytes outside ASCII that read as UTF-8 are taken as UTF-8, because they are almost never single-byte text.

    Args:
        data: The base64url-encoded body data to decode.
        charset: The character set that the body declares.

    Returns:
        The decoded text.

    Raises:
        ValueError: If the data is not valid base64url, or the bytes fit neither character set.
    """
    decoded = _decode_base64url(data)
    if not decoded.isascii():
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
            return _HEADER_FOLD_PATTERN.sub(r"\1", h.get("value", ""))
    return ""


def _declared_charset(part: dict) -> str:
    """Return the character set that a Gmail payload part declares for its body, or UTF-8 if it declares none."""
    part_headers = Message()
    part_headers["Content-Type"] = _extract_header(part.get("headers", []), "Content-Type")
    return part_headers.get_content_charset() or "utf-8"


def _declares_attachment(part: dict) -> bool:
    """Report whether a Gmail payload part declares itself an attachment."""
    return _extract_header(part.get("headers", []), "Content-Disposition").lower().startswith("attachment")


def _walk_parts(payload: dict) -> Iterator[dict]:
    """Yield the payload and its MIME parts in document order, entering no part that declares itself an attachment."""
    if _declares_attachment(payload):
        return
    yield payload
    for part in payload.get("parts", []):
        yield from _walk_parts(part)


def _body_candidates(payload: dict) -> Iterator[dict]:
    """Yield the parts of a Gmail payload that can hold the body text, the parts that name a file last.

    NOTE: Some mail programs name the body part of a message, so a part that names a file is still a candidate.
    """
    parts = [part for part in _walk_parts(payload) if part.get("mimeType", "") in ("", "text/html", "text/plain")]
    yield from (part for part in parts if not part.get("filename"))
    yield from (part for part in parts if part.get("filename"))


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

        if part.get("mimeType", "") == "text/html":
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
    """Parse a base64url-encoded email message from the Gmail API, keeping its CRLF line endings when written out.

    Raises:
        ValueError: If ``raw`` cannot be decoded.
    """
    return email.message_from_bytes(_decode_base64url(raw), policy=policy.SMTP)


def _attached_files(message: MIMEPart, *, in_related: bool) -> Iterator[MIMEPart]:
    """Yield the parts of a message that hold an attached file, from any depth of its MIME tree.

    A part that is not itself multipart is yielded whole, so an attached email keeps its own parts.

    Args:
        message: The message or message part to read.
        in_related: True when ``message`` is a multipart/related part or sits inside one, which makes each
            inline part below it a piece of the HTML of that part rather than a file.

    Yields:
        Each part that holds an attached file.
    """
    for part in message.iter_parts():
        if part.is_attachment():
            yield part
        elif part.get_content_maintype() == "multipart":
            yield from _attached_files(part, in_related=in_related or part.get_content_type() == "multipart/related")
        # A text part holds body text unless it names a file, so only those two kinds of part are files here.
        elif not in_related and (part.get_filename() or part.get_content_type() not in ("text/html", "text/plain")):
            yield part


def _replace_body(message: EmailMessage, body: str) -> None:
    """Replace the text and HTML of a message with a plain-text body, keeping its attached files."""
    in_related = message.get_content_type() == "multipart/related"
    attachments = list(_attached_files(message, in_related=in_related))
    message.clear_content()
    # NOTE: The draft keeps the policy that read it, which allows 8-bit content, so the new body names a 7-bit
    # encoding of its own. A part that the edit does not write keeps the encoding that it arrived with.
    message.set_content(body, cte="7bit" if body.isascii() else "quoted-printable")
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
    # NOTE: A 7-bit message holds no 8-bit bytes, which is what the API asks for. An edited draft keeps its own
    # encoding instead, so that an edit does not rewrite a part that it did not change.
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
    try:
        raw = _build_raw_message(
            params.to,
            params.subject,
            params.body,
            cc=params.cc,
            bcc=params.bcc,
        )
    except UnicodeEncodeError:
        return SendEmailResult(success=False, error=_UNWRITABLE_VALUE_ERROR)
    except ValueError:
        return SendEmailResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

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
    try:
        raw = _build_raw_message(
            params.to,
            params.subject,
            params.body,
            cc=params.cc,
            bcc=params.bcc,
        )
    except UnicodeEncodeError:
        return CreateDraftResult(success=False, error=_UNWRITABLE_VALUE_ERROR)
    except ValueError:
        return CreateDraftResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

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

            original_subject = message.get("Subject", "")
            try:
                _replace_headers(message, params)
                if params.body is not None:
                    _replace_body(message, params.body)
                edited_raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            except UnicodeEncodeError:
                return EditDraftResult(success=False, error=_UNWRITABLE_VALUE_ERROR)
            except ValueError:
                return EditDraftResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

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
            except UnicodeEncodeError:
                return ReplyToEmailResult(success=False, error=_UNWRITABLE_VALUE_ERROR)
            except ValueError:
                return ReplyToEmailResult(success=False, error=_HEADER_LINE_BREAK_ERROR)

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
