"""OAuth scope definitions for Google Docs tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class GoogleDocsScope(StrEnum):
    """OAuth scopes for Google Docs and Drive API access."""

    DOCUMENTS = "https://www.googleapis.com/auth/documents"
    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleDocsScope]] = {
    "google_docs_list_documents": [GoogleDocsScope.DRIVE],
    "google_docs_create_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_read_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_update_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_copy_document": [GoogleDocsScope.DRIVE],
    "google_docs_replace_text": [GoogleDocsScope.DOCUMENTS],
    "google_docs_insert_image": [GoogleDocsScope.DOCUMENTS, GoogleDocsScope.DRIVE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_docs",
    display_name="Google Docs",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
