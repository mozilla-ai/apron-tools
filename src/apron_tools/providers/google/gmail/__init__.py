"""Gmail provider.

API docs:
  - Gmail: https://developers.google.com/workspace/gmail/api/reference/rest
"""

from .tools import (
    gmail_add_label_to_email,
    gmail_create_draft,
    gmail_edit_draft,
    gmail_get_thread_replies,
    gmail_list_emails,
    gmail_list_labels,
    gmail_read_email,
    gmail_remove_label_from_email,
    gmail_reply_to_email,
    gmail_send_email,
)

__all__ = [
    "gmail_add_label_to_email",
    "gmail_create_draft",
    "gmail_edit_draft",
    "gmail_get_thread_replies",
    "gmail_list_emails",
    "gmail_list_labels",
    "gmail_read_email",
    "gmail_remove_label_from_email",
    "gmail_reply_to_email",
    "gmail_send_email",
]
