"""OAuth scope definitions for Microsoft Excel tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class MicrosoftExcelScope(StrEnum):
    """OAuth scopes for Microsoft Graph Excel API access."""

    FILES_READ = "Files.Read"
    FILES_READ_WRITE = "Files.ReadWrite"


SCOPES: dict[str, list[MicrosoftExcelScope]] = {
    "microsoft_excel_list_workbooks": [MicrosoftExcelScope.FILES_READ],
    "microsoft_excel_get_workbook_info": [MicrosoftExcelScope.FILES_READ],
    "microsoft_excel_read_worksheet": [MicrosoftExcelScope.FILES_READ],
    "microsoft_excel_update_worksheet": [MicrosoftExcelScope.FILES_READ_WRITE],
    "microsoft_excel_append_row": [MicrosoftExcelScope.FILES_READ_WRITE],
    "microsoft_excel_create_workbook": [MicrosoftExcelScope.FILES_READ_WRITE],
    "microsoft_excel_add_worksheet": [MicrosoftExcelScope.FILES_READ_WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="microsoft_excel",
    display_name="Microsoft Excel",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
