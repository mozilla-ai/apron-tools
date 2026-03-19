"""OAuth scope definitions for Microsoft Word tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class MicrosoftWordScope(StrEnum):
    """OAuth scopes for Microsoft Graph OneDrive file access."""

    FILES_READ = "Files.Read"
    FILES_READ_WRITE = "Files.ReadWrite"


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
