"""OAuth scope definitions for Google Sheets tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GoogleSheetsScope(Scope):
    """OAuth scopes for Google Sheets and Drive API access."""

    SPREADSHEETS = (
        "https://www.googleapis.com/auth/spreadsheets",
        "Full Spreadsheet Access",
        "View, edit, create, and delete all Google Sheets",
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


SCOPES: dict[str, list[GoogleSheetsScope]] = {
    "google_sheets_list_spreadsheets": [GoogleSheetsScope.DRIVE],
    "google_sheets_create_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "google_sheets_copy_spreadsheet": [GoogleSheetsScope.DRIVE],
    "google_sheets_read_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "google_sheets_update_spreadsheet": [GoogleSheetsScope.SPREADSHEETS],
    "google_sheets_append_row": [GoogleSheetsScope.SPREADSHEETS],
    "google_sheets_add_sheet": [GoogleSheetsScope.SPREADSHEETS],
    "google_sheets_find_row": [GoogleSheetsScope.SPREADSHEETS],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_sheets",
    display_name="Google Sheets",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
