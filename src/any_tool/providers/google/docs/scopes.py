"""OAuth scope definitions for Google Docs tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GoogleDocsScope(StrEnum):
    """OAuth scopes for Google Docs and Drive API access."""

    DOCUMENTS = "https://www.googleapis.com/auth/documents"
    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleDocsScope]] = {
    "list_documents": [GoogleDocsScope.DRIVE],
    "create_document": [GoogleDocsScope.DOCUMENTS],
    "read_document": [GoogleDocsScope.DOCUMENTS],
    "update_document": [GoogleDocsScope.DOCUMENTS],
    "copy_document": [GoogleDocsScope.DRIVE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_docs",
    display_name="Google Docs",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
