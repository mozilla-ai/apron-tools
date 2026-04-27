"""OAuth scope definitions for Microsoft Outlook tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftOutlookScope(Scope):
    """OAuth scopes for Microsoft Graph Mail API access."""

    MAIL_READ = (
        "Mail.Read",
        "Read Emails",
        "View your Outlook emails and attachments",
        "read",
        False,
    )
    MAIL_SEND = (
        "Mail.Send",
        "Send Emails",
        "Send emails on your behalf",
        "write",
        False,
    )
    MAIL_READ_WRITE = (
        "Mail.ReadWrite",
        "Manage Emails",
        "Create drafts, move, and organize your emails",
        "write",
        False,
    )


SCOPES: dict[str, list[MicrosoftOutlookScope]] = {
    "microsoft_outlook_list_emails": [MicrosoftOutlookScope.MAIL_READ],
    "microsoft_outlook_read_email": [MicrosoftOutlookScope.MAIL_READ],
    "microsoft_outlook_send_email": [MicrosoftOutlookScope.MAIL_SEND],
    "microsoft_outlook_create_draft": [MicrosoftOutlookScope.MAIL_READ_WRITE],
    "microsoft_outlook_send_draft": [MicrosoftOutlookScope.MAIL_SEND],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_outlook",
    display_name="Microsoft Outlook",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
