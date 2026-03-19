"""Microsoft Outlook provider.

API docs: https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview
"""

from .tools import (
    microsoft_outlook_create_draft,
    microsoft_outlook_list_emails,
    microsoft_outlook_read_email,
    microsoft_outlook_send_draft,
    microsoft_outlook_send_email,
)

__all__ = [
    "microsoft_outlook_create_draft",
    "microsoft_outlook_list_emails",
    "microsoft_outlook_read_email",
    "microsoft_outlook_send_draft",
    "microsoft_outlook_send_email",
]
