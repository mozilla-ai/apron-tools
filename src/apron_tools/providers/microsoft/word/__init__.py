"""Microsoft Word provider.

API docs:
  - OneDrive: https://learn.microsoft.com/en-us/graph/api/resources/onedrive
  - Word: https://learn.microsoft.com/en-us/graph/api/resources/document
"""

from .tools import (
    microsoft_word_create_document,
    microsoft_word_explore_documents,
    microsoft_word_read_document,
    microsoft_word_update_document,
    microsoft_word_upload_to_onedrive,
)

__all__ = [
    "microsoft_word_create_document",
    "microsoft_word_explore_documents",
    "microsoft_word_read_document",
    "microsoft_word_update_document",
    "microsoft_word_upload_to_onedrive",
]
