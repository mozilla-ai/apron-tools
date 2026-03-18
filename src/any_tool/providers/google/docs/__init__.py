"""Google Docs provider.

API docs:
  - Docs: https://developers.google.com/workspace/docs/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
"""

from .tools import (
    copy_document,
    create_document,
    list_documents,
    read_document,
    update_document,
)

__all__ = [
    "copy_document",
    "create_document",
    "list_documents",
    "read_document",
    "update_document",
]
