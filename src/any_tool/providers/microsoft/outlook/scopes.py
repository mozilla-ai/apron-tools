"""OAuth scope definitions for Microsoft Outlook tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class MicrosoftOutlookScope(StrEnum):
    """OAuth scopes for Microsoft Graph Mail API access."""

    MAIL_READ = "Mail.Read"
    MAIL_SEND = "Mail.Send"
    MAIL_READ_WRITE = "Mail.ReadWrite"


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
