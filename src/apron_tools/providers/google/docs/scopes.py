"""OAuth scope definitions for Google Docs tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GoogleDocsScope(Scope):
    """OAuth scopes for Google Docs and Drive API access."""

    DOCUMENTS = (
        "https://www.googleapis.com/auth/documents",
        "Full Document Access",
        "View, edit, create, and delete all Google Docs",
        "write",
        False,
    )
    DRIVE = (
        "https://www.googleapis.com/auth/drive",
        "Full Drive Access",
        "View, edit, create, delete, and share all Google Drive files",
        "write",
        False,
    )


SCOPES: dict[str, list[GoogleDocsScope]] = {
    "google_docs_list_documents": [GoogleDocsScope.DRIVE],
    "google_docs_create_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_read_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_update_document": [GoogleDocsScope.DOCUMENTS],
    "google_docs_copy_document": [GoogleDocsScope.DRIVE],
    "google_docs_replace_text": [GoogleDocsScope.DOCUMENTS],
    "google_docs_insert_image": [GoogleDocsScope.DOCUMENTS, GoogleDocsScope.DRIVE],
    "google_docs_update_table_cell": [GoogleDocsScope.DOCUMENTS],
    "google_docs_read_comments": [GoogleDocsScope.DRIVE],
    "google_docs_create_comment": [GoogleDocsScope.DRIVE],
    "google_docs_reply_to_comment": [GoogleDocsScope.DRIVE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_docs",
    display_name="Google Docs",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
