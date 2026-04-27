"""OAuth scope definitions for Gmail tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GmailScope(Scope):
    """OAuth scopes for Gmail API access."""

    READONLY = (
        "https://www.googleapis.com/auth/gmail.readonly",
        "Read Emails",
        "View and search your Gmail messages",
        "read",
        False,
    )
    COMPOSE = (
        "https://www.googleapis.com/auth/gmail.compose",
        "Compose, Send & Manage Drafts",
        (
            "Create, edit, and delete drafts, and send messages or drafts "
            "(narrower than Full Email Management — no label or trash management)"
        ),
        "write",
        False,
    )
    # gmail.modify implies read access; the description leads with that
    # implication so the consent-screen wording matches what the user
    # will see at Google.
    MODIFY = (
        "https://www.googleapis.com/auth/gmail.modify",
        "Full Email Management",
        "Read and manage all emails including drafts, labels, and trash",
        "write",
        False,
    )
    # gmail.labels covers listing / creating / updating / deleting labels
    # themselves — it does not cover applying labels to existing messages
    # (that requires gmail.modify, which implies labels access).
    LABELS = (
        "https://www.googleapis.com/auth/gmail.labels",
        "Manage Labels",
        "See and edit your email labels",
        "write",
        False,
    )


SCOPES: dict[str, list[GmailScope]] = {
    "gmail_list_emails": [GmailScope.READONLY],
    "gmail_read_email": [GmailScope.READONLY],
    "gmail_send_email": [GmailScope.COMPOSE],
    "gmail_create_draft": [GmailScope.COMPOSE],
    "gmail_edit_draft": [GmailScope.COMPOSE],
    "gmail_reply_to_email": [GmailScope.COMPOSE],
    "gmail_get_thread_replies": [GmailScope.READONLY],
    "gmail_list_labels": [GmailScope.READONLY],
    "gmail_add_labels_to_emails": [GmailScope.MODIFY],
    "gmail_remove_labels_from_emails": [GmailScope.MODIFY],
    # Creating a label only needs gmail.labels, which is narrower than
    # gmail.modify. Existing installations that already hold gmail.modify
    # remain covered at the API level since modify implies labels access.
    "gmail_create_label": [GmailScope.LABELS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="gmail",
    display_name="Gmail",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
