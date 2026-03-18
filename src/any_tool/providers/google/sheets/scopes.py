"""OAuth scope definitions for Google Sheets tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GoogleSheetsScope(StrEnum):
    """OAuth scopes for Google Sheets and Drive API access."""

    SPREADSHEETS = "https://www.googleapis.com/auth/spreadsheets"
    DRIVE = "https://www.googleapis.com/auth/drive"


SCOPES: dict[str, list[GoogleSheetsScope]] = {
    "list_spreadsheets": [GoogleSheetsScope.DRIVE],
    "create_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "copy_spreadsheet": [GoogleSheetsScope.DRIVE],
    "read_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "update_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "append_row": [GoogleSheetsScope.SPREADSHEETS],
    "add_sheet": [GoogleSheetsScope.SPREADSHEETS],
    "find_row": [GoogleSheetsScope.SPREADSHEETS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_sheets",
    display_name="Google Sheets",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
