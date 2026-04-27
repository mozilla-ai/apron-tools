"""OAuth scope definitions for Microsoft Word tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftWordScope(Scope):
    """OAuth scopes for Microsoft Graph OneDrive file access."""

    FILES_READ = (
        "Files.Read",
        "View Documents",
        "View your Word documents",
        "read",
        False,
    )
    FILES_READ_WRITE = (
        "Files.ReadWrite",
        "Edit Documents",
        "Create, edit, and manage your Word documents",
        "write",
        False,
    )


SCOPES: dict[str, list[MicrosoftWordScope]] = {
    "microsoft_word_explore_documents": [
        MicrosoftWordScope.FILES_READ,
    ],
    "microsoft_word_read_document": [
        MicrosoftWordScope.FILES_READ,
    ],
    "microsoft_word_create_document": [
        MicrosoftWordScope.FILES_READ_WRITE,
    ],
    "microsoft_word_update_document": [
        MicrosoftWordScope.FILES_READ_WRITE,
    ],
    "microsoft_word_upload_to_onedrive": [
        MicrosoftWordScope.FILES_READ_WRITE,
    ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_word",
    display_name="Microsoft Word",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
