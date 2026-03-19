"""Microsoft Outlook tool functions for interacting with the Microsoft Graph API."""

from __future__ import annotations

import httpx

from any_tool.providers.microsoft.outlook.types import (
    CreateDraftParams,
    CreateDraftResult,
    EmailMessage,
    ListEmailsParams,
    ListEmailsResult,
    ReadEmailParams,
    ReadEmailResult,
    SendDraftParams,
    SendDraftResult,
    SendEmailParams,
    SendEmailResult,
)
from any_tool.tool import tool

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _build_recipients(addresses: list[str]) -> list[dict[str, dict[str, str]]]:
    """Convert a list of email addresses to the Graph API recipient format."""
    return [{"emailAddress": {"address": addr}} for addr in addresses]


@tool(
    scopes=SCOPES["microsoft_outlook_list_emails"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/user-list-messages",
    provider="microsoft",
    service="microsoft_outlook",
)
async def microsoft_outlook_list_emails(
    params: ListEmailsParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListEmailsResult:
    """List emails from the authenticated user's mailbox with optional OData filtering."""
    limit = min(params.limit, 100)
    query_params: dict[str, str | int] = {
        "$top": limit,
        "$orderby": "receivedDateTime desc",
        "$select": (
            "id,subject,from,toRecipients,ccRecipients,replyTo,"
            "receivedDateTime,sentDateTime,bodyPreview,isRead,isDraft,hasAttachments,importance"
        ),
    }
    if params.query:
        query_params["$filter"] = params.query

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/messages",
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListEmailsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListEmailsResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    emails = [EmailMessage.model_validate(m) for m in resp.json().get("value", [])]
    return ListEmailsResult(success=True, emails=emails)


@tool(
    scopes=SCOPES["microsoft_outlook_read_email"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/message-get",
    provider="microsoft",
    service="microsoft_outlook",
)
async def microsoft_outlook_read_email(
    params: ReadEmailParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ReadEmailResult:
    """Read the full content of an email by its message ID."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/messages/{params.message_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ReadEmailResult(success=False, error=str(exc))

    if not resp.is_success:
        return ReadEmailResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    email = EmailMessage.model_validate(resp.json())
    return ReadEmailResult(success=True, email=email)


@tool(
    scopes=SCOPES["microsoft_outlook_send_email"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/user-sendmail",
    provider="microsoft",
    service="microsoft_outlook",
)
async def microsoft_outlook_send_email(
    params: SendEmailParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SendEmailResult:
    """Send an email from the authenticated user's mailbox."""
    message: dict = {
        "subject": params.subject,
        "body": {
            "contentType": "Text",
            "content": params.body,
        },
        "toRecipients": _build_recipients(params.to),
    }
    if params.cc:
        message["ccRecipients"] = _build_recipients(params.cc)
    if params.bcc:
        message["bccRecipients"] = _build_recipients(params.bcc)

    payload = {
        "message": message,
        "saveToSentItems": True,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/me/sendMail",
                headers=_headers(token, content_type=True),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return SendEmailResult(success=False, error=str(exc))

    if not resp.is_success:
        return SendEmailResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    return SendEmailResult(success=True)


@tool(
    scopes=SCOPES["microsoft_outlook_create_draft"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/user-post-messages",
    provider="microsoft",
    service="microsoft_outlook",
)
async def microsoft_outlook_create_draft(
    params: CreateDraftParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreateDraftResult:
    """Create a draft email in the authenticated user's mailbox."""
    message: dict = {
        "subject": params.subject,
        "body": {
            "contentType": "Text",
            "content": params.body,
        },
        "toRecipients": _build_recipients(params.to),
    }
    if params.cc:
        message["ccRecipients"] = _build_recipients(params.cc)
    if params.bcc:
        message["bccRecipients"] = _build_recipients(params.bcc)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/me/messages",
                headers=_headers(token, content_type=True),
                json=message,
            )
    except httpx.HTTPError as exc:
        return CreateDraftResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateDraftResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    draft = EmailMessage.model_validate(resp.json())
    return CreateDraftResult(success=True, draft=draft)


@tool(
    scopes=SCOPES["microsoft_outlook_send_draft"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/message-send",
    provider="microsoft",
    service="microsoft_outlook",
)
async def microsoft_outlook_send_draft(
    params: SendDraftParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SendDraftResult:
    """Send an existing draft email by its message ID."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/me/messages/{params.message_id}/send",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return SendDraftResult(success=False, error=str(exc))

    if not resp.is_success:
        return SendDraftResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    return SendDraftResult(success=True)
