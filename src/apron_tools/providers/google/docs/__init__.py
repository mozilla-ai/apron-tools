"""Google Docs provider.

API docs:
  - Docs: https://developers.google.com/workspace/docs/api/reference/rest
  - Drive: https://developers.google.com/drive/api/reference/rest/v3
"""

from .tools import (
    google_docs_copy_document,
    google_docs_create_document,
    google_docs_insert_image,
    google_docs_list_documents,
    google_docs_read_document,
    google_docs_replace_text,
    google_docs_update_document,
)

__all__ = [
    "google_docs_copy_document",
    "google_docs_create_document",
    "google_docs_insert_image",
    "google_docs_list_documents",
    "google_docs_read_document",
    "google_docs_replace_text",
    "google_docs_update_document",
]
