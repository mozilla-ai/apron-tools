"""Gmail tool functions for interacting with the Gmail REST API."""

from __future__ import annotations

import base64
import contextlib
from email.mime.text import MIMEText

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
    that is already padded. Decoding is lenient and does not validate the
    payload: characters outside the base64url alphabet are discarded rather
    than rejected.

    Args:
        data: The base64url-encoded string to decode, with or without padding.

    Returns:
        The decoded bytes.

    Raises:
        ValueError: If ``data`` cannot be decoded, such as an invalid length
            or non-ASCII input.
    """
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _extract_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a single header value from a Gmail payload headers list."""
    for h in headers:
        if h.get("name") == name:
            return h.get("value", "")
    return ""


def _extract_body(payload: dict) -> str:
    """Extract the plain-text body from a Gmail message payload.

    Handles both single-part and multipart MIME payloads, preferring
    text/plain over text/html. Nested multipart structures are traversed
    recursively.
    """
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        try:
            return _decode_base64url(body_data).decode("utf-8")
        except ValueError:
            return "(Could not decode email body)"

    parts = payload.get("parts", [])
    plain_text: str | None = None
    html_text: str | None = None

    for part in parts:
        mime_type = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data", "")

        if mime_type == "text/plain" and part_data:
            with contextlib.suppress(ValueError):
                plain_text = _decode_base64url(part_data).decode("utf-8")
        elif mime_type == "text/html" and part_data:
            with contextlib.suppress(ValueError):
                html_text = _decode_base64url(part_data).decode("utf-8")
        elif part.get("parts"):
            nested = _extract_body(part)
            if nested and nested != "(No email body found)":
                return nested

    if plain_text:
        return plain_text
    if html_text:
        return html_text
    return "(No email body found)"


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
    """Construct a base64url-encoded MIME message for the Gmail send API."""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
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

    return ReadEmailResult(
        success=True,
        id=data.get("id", ""),
        thread_id=data.get("threadId", ""),
        subject=_extract_header(hdrs, "Subject"),
        from_address=_extract_header(hdrs, "From"),
        to_address=_extract_header(hdrs, "To"),
        cc=_extract_header(hdrs, "Cc"),
        date=_extract_header(hdrs, "Date"),
        body=_extract_body(payload),
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
    raw = _build_raw_message(
        params.to,
        params.subject,
        params.body,
        cc=params.cc,
        bcc=params.bcc,
    )

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
    raw = _build_raw_message(
        params.to,
        params.subject,
        params.body,
        cc=params.cc,
        bcc=params.bcc,
    )

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
    """Edit an existing Gmail draft."""
    draft_url = f"{base_url}/drafts/{quote_path_segment(params.draft_id)}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch existing draft to merge fields.
            get_resp = await client.get(
                draft_url,
                headers=_headers(token),
                params={"format": "full"},
            )

            if not get_resp.is_success:
                return EditDraftResult(
                    success=False,
                    error=f"Gmail API error {get_resp.status_code}: {get_resp.text}",
                )

            draft_data = get_resp.json()
            payload = draft_data.get("message", {}).get("payload", {})
            hdrs = payload.get("headers", [])

            final_to = params.to if params.to is not None else _extract_header(hdrs, "To")
            final_subject = params.subject if params.subject is not None else _extract_header(hdrs, "Subject")
            final_body = params.body if params.body is not None else _extract_body(payload)
            final_cc = params.cc if params.cc is not None else _extract_header(hdrs, "Cc") or None
            final_bcc = params.bcc if params.bcc is not None else _extract_header(hdrs, "Bcc") or None

            raw = _build_raw_message(
                final_to,
                final_subject,
                final_body,
                cc=final_cc,
                bcc=final_bcc,
            )

            put_resp = await client.put(
                draft_url,
                headers=_headers(token, content_type=True),
                json={"message": {"raw": raw}},
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
                    "metadataHeaders": ["From", "To", "Subject", "Message-ID", "References"],
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
            orig_subject = _extract_header(hdrs, "Subject")
            orig_message_id = _extract_header(hdrs, "Message-ID")
            orig_references = _extract_header(hdrs, "References")

            reply_subject = orig_subject
            if not reply_subject.lower().startswith("re:"):
                reply_subject = f"Re: {reply_subject}"

            references = orig_references
            if orig_message_id:
                references = f"{references} {orig_message_id}" if references else orig_message_id

            raw = _build_raw_message(
                orig_from,
                reply_subject,
                params.body,
                cc=params.cc,
                bcc=params.bcc,
                in_reply_to=orig_message_id or None,
                references=references or None,
            )

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
