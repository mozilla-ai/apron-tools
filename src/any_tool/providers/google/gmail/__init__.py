"""Gmail provider.

API docs:
  - Gmail: https://developers.google.com/workspace/gmail/api/reference/rest
"""

from .tools import (
    add_label_to_email,
    create_draft,
    edit_draft,
    get_thread_replies,
    list_emails,
    list_labels,
    read_email,
    remove_label_from_email,
    reply_to_email,
    send_email,
)

__all__ = [
    "add_label_to_email",
    "create_draft",
    "edit_draft",
    "get_thread_replies",
    "list_emails",
    "list_labels",
    "read_email",
    "remove_label_from_email",
    "reply_to_email",
    "send_email",
]
