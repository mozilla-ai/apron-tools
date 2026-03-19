"""OAuth scope definitions for Microsoft Excel tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class MicrosoftExcelScope(StrEnum):
    """OAuth scopes for Microsoft Graph Excel API access."""

    FILES_READ = "Files.Read"
    FILES_READ_WRITE = "Files.ReadWrite"


SCOPES: dict[str, list[MicrosoftExcelScope]] = {
    "list_workbooks": [MicrosoftExcelScope.FILES_READ],
    "get_workbook_info": [MicrosoftExcelScope.FILES_READ],
    "read_worksheet": [MicrosoftExcelScope.FILES_READ],
    "update_worksheet": [MicrosoftExcelScope.FILES_READ_WRITE],
    "append_row": [MicrosoftExcelScope.FILES_READ_WRITE],
    "create_workbook": [MicrosoftExcelScope.FILES_READ_WRITE],
    "add_worksheet": [MicrosoftExcelScope.FILES_READ_WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_excel",
    display_name="Microsoft Excel",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
