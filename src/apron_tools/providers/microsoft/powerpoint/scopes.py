"""OAuth scope definitions for Microsoft PowerPoint tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class MicrosoftPowerPointScope(Scope):
    """OAuth scopes for Microsoft Graph OneDrive file access."""

    FILES_READ = (
        "Files.Read",
        "View Presentations",
        "View your PowerPoint presentations",
        "read",
        False,
    )
    FILES_READ_WRITE = (
        "Files.ReadWrite",
        "Edit Presentations",
        "Create, edit, and manage your PowerPoint presentations",
        "write",
        False,
    )


SCOPES: dict[str, list[MicrosoftPowerPointScope]] = {
    "microsoft_powerpoint_explore_presentations": [
        MicrosoftPowerPointScope.FILES_READ,
    ],
    "microsoft_powerpoint_read_presentation": [
        MicrosoftPowerPointScope.FILES_READ,
    ],
    "microsoft_powerpoint_create_presentation": [
        MicrosoftPowerPointScope.FILES_READ_WRITE,
    ],
    "microsoft_powerpoint_add_slide": [
        MicrosoftPowerPointScope.FILES_READ_WRITE,
    ],
    "microsoft_powerpoint_update_slide_text": [
        MicrosoftPowerPointScope.FILES_READ_WRITE,
    ],
    "microsoft_powerpoint_upload_to_onedrive": [
        MicrosoftPowerPointScope.FILES_READ_WRITE,
    ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_powerpoint",
    display_name="Microsoft PowerPoint",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
