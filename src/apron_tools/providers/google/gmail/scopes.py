"""OAuth scope definitions for Gmail tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class GmailScope(StrEnum):
    """OAuth scopes for Gmail API access."""

    READONLY = "https://www.googleapis.com/auth/gmail.readonly"
    COMPOSE = "https://www.googleapis.com/auth/gmail.compose"
    MODIFY = "https://www.googleapis.com/auth/gmail.modify"


SCOPES: dict[str, list[GmailScope]] = {
    "gmail_list_emails": [GmailScope.READONLY],
    "gmail_read_email": [GmailScope.READONLY],
    "gmail_send_email": [GmailScope.COMPOSE],
    "gmail_create_draft": [GmailScope.COMPOSE],
    "gmail_edit_draft": [GmailScope.COMPOSE],
    "gmail_reply_to_email": [GmailScope.COMPOSE],
    "gmail_get_thread_replies": [GmailScope.READONLY],
    "gmail_list_labels": [GmailScope.READONLY],
    "gmail_add_label_to_email": [GmailScope.MODIFY],
    "gmail_remove_label_from_email": [GmailScope.MODIFY],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="gmail",
    display_name="Gmail",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
