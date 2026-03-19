"""OAuth scope definitions for Microsoft PowerPoint tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class MicrosoftPowerPointScope(StrEnum):
    """OAuth scopes for Microsoft Graph OneDrive file access."""

    FILES_READ = "Files.Read"
    FILES_READ_WRITE = "Files.ReadWrite"


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
