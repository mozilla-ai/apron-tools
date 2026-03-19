"""Tests for Google Sheets tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.google.sheets.tools import (
    google_sheets_add_sheet,
    google_sheets_append_row,
    google_sheets_copy_spreadsheet,
    google_sheets_create_spreadsheet,
    google_sheets_find_row,
    google_sheets_list_spreadsheets,
    google_sheets_read_spreadsheet,
    google_sheets_update_spreadsheet,
)
from apron_tools.providers.google.sheets.types import (
    AddSheetParams,
    AddSheetResult,
    AppendRowParams,
    AppendRowResult,
    CopySpreadsheetParams,
    CopySpreadsheetResult,
    CreateSpreadsheetParams,
    CreateSpreadsheetResult,
    FindRowParams,
    FindRowResult,
    ListSpreadsheetsParams,
    ListSpreadsheetsResult,
    ReadSpreadsheetParams,
    ReadSpreadsheetResult,
    UpdateSpreadsheetParams,
    UpdateSpreadsheetResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"
_SPREADSHEET_ID = "spreadsheet-id-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_spreadsheets
# ---------------------------------------------------------------------------


class TestListSpreadsheets:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}?q=mimeType%3D%27application%2Fvnd.google-apps.spreadsheet%27&pageSize=20&fields=files%28id%2Cname%2CcreatedTime%2CmodifiedTime%29&orderBy=modifiedTime+desc&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=allDrives",
            json=_load_json("list_spreadsheets.json"),
        )

        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(), token=_TOKEN)

        assert isinstance(result, ListSpreadsheetsResult)
        assert result.success is True
        assert len(result.files) == 2
        assert result.files[0].name == "Budget 2024"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_list_spreadsheets._tool_definition
        assert defn.name == "google_sheets_list_spreadsheets"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# create_spreadsheet
# ---------------------------------------------------------------------------


class TestCreateSpreadsheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=_SHEETS_BASE,
            json=_load_json("create_spreadsheet.json"),
        )

        result = await google_sheets_create_spreadsheet(
            CreateSpreadsheetParams(title="Budget 2024"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateSpreadsheetResult)
        assert result.success is True
        assert result.spreadsheet_id == _SPREADSHEET_ID
        assert result.properties.title == "Budget 2024"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_sheets_create_spreadsheet(
            CreateSpreadsheetParams(title="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_create_spreadsheet._tool_definition
        assert defn.name == "google_sheets_create_spreadsheet"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes


# ---------------------------------------------------------------------------
# copy_spreadsheet
# ---------------------------------------------------------------------------


class TestCopySpreadsheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_SPREADSHEET_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_spreadsheet_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_SPREADSHEET_ID}/copy?supportsAllDrives=true",
            json=_load_json("copy_spreadsheet.json"),
        )

        result = await google_sheets_copy_spreadsheet(
            CopySpreadsheetParams(
                spreadsheet_id=_SPREADSHEET_ID,
                new_title="Copy of Budget 2024",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CopySpreadsheetResult)
        assert result.success is True
        assert result.id == "spreadsheet-id-003"
        assert result.name == "Copy of Budget 2024"
        assert result.original_name == "Budget 2024"

    async def test_meta_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_sheets_copy_spreadsheet(
            CopySpreadsheetParams(spreadsheet_id="bad_id", new_title="Copy"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_copy_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_SPREADSHEET_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_spreadsheet_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_SPREADSHEET_ID}/copy?supportsAllDrives=true",
            status_code=403,
            text="Forbidden",
        )

        result = await google_sheets_copy_spreadsheet(
            CopySpreadsheetParams(
                spreadsheet_id=_SPREADSHEET_ID,
                new_title="Copy",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_copy_spreadsheet._tool_definition
        assert defn.name == "google_sheets_copy_spreadsheet"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# read_spreadsheet
# ---------------------------------------------------------------------------


class TestReadSpreadsheet:
    async def test_success_with_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1%21A1%3AD5",
            json=_load_json("read_spreadsheet_values.json"),
        )

        result = await google_sheets_read_spreadsheet(
            ReadSpreadsheetParams(
                spreadsheet_id=_SPREADSHEET_ID,
                range="Sheet1!A1:D5",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, ReadSpreadsheetResult)
        assert result.success is True
        assert result.range == "Sheet1!A1:D5"
        assert len(result.values) == 4
        assert result.values[0] == ["Name", "Age", "City", "Score"]

    async def test_success_no_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}?fields=properties.title%2Csheets.properties",
            json=_load_json("read_spreadsheet_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1",
            json=_load_json("read_spreadsheet_values.json"),
        )

        result = await google_sheets_read_spreadsheet(
            ReadSpreadsheetParams(spreadsheet_id=_SPREADSHEET_ID),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.values) == 4

    async def test_success_with_metadata(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}?fields=properties.title%2Csheets.properties",
            json=_load_json("read_spreadsheet_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1%21A1%3AD5",
            json=_load_json("read_spreadsheet_values.json"),
        )

        result = await google_sheets_read_spreadsheet(
            ReadSpreadsheetParams(
                spreadsheet_id=_SPREADSHEET_ID,
                range="Sheet1!A1:D5",
                include_metadata=True,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.title == "Budget 2024"
        assert result.sheet_names == ["Sheet1"]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_sheets_read_spreadsheet(
            ReadSpreadsheetParams(
                spreadsheet_id="bad_id",
                range="Sheet1!A1:D5",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_read_spreadsheet._tool_definition
        assert defn.name == "google_sheets_read_spreadsheet"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes


# ---------------------------------------------------------------------------
# update_spreadsheet
# ---------------------------------------------------------------------------


class TestUpdateSpreadsheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1%21A1%3AD5?valueInputOption=USER_ENTERED",
            json=_load_json("update_spreadsheet.json"),
        )

        result = await google_sheets_update_spreadsheet(
            UpdateSpreadsheetParams(
                spreadsheet_id=_SPREADSHEET_ID,
                range="Sheet1!A1:D5",
                values=[
                    ["Name", "Age", "City", "Score"],
                    ["Alice", "30", "New York", "95"],
                ],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateSpreadsheetResult)
        assert result.success is True
        assert result.updated_cells == 16
        assert result.updated_range == "Sheet1!A1:D5"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_sheets_update_spreadsheet(
            UpdateSpreadsheetParams(
                spreadsheet_id="bad_id",
                range="Sheet1!A1:B2",
                values=[["a", "b"]],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_update_spreadsheet._tool_definition
        assert defn.name == "google_sheets_update_spreadsheet"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes


# ---------------------------------------------------------------------------
# append_row
# ---------------------------------------------------------------------------


class TestAppendRow:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS",
            json=_load_json("append_row.json"),
        )

        result = await google_sheets_append_row(
            AppendRowParams(
                spreadsheet_id=_SPREADSHEET_ID,
                range="Sheet1",
                values=[["Diana", "28", "Paris", "88"]],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, AppendRowResult)
        assert result.success is True
        assert result.updated_cells == 4
        assert result.updated_range == "Sheet1!A5:D5"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_sheets_append_row(
            AppendRowParams(
                spreadsheet_id="bad_id",
                range="Sheet1",
                values=[["x"]],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_append_row._tool_definition
        assert defn.name == "google_sheets_append_row"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes


# ---------------------------------------------------------------------------
# add_sheet
# ---------------------------------------------------------------------------


class TestAddSheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}:batchUpdate",
            json=_load_json("add_sheet.json"),
        )

        result = await google_sheets_add_sheet(
            AddSheetParams(spreadsheet_id=_SPREADSHEET_ID, title="New Sheet"),
            token=_TOKEN,
        )

        assert isinstance(result, AddSheetResult)
        assert result.success is True
        assert result.sheet_id == 123456
        assert result.title == "New Sheet"
        assert result.spreadsheet_id == _SPREADSHEET_ID

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Duplicate sheet title")

        result = await google_sheets_add_sheet(
            AddSheetParams(spreadsheet_id="bad_id", title="Sheet1"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_add_sheet._tool_definition
        assert defn.name == "google_sheets_add_sheet"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes


# ---------------------------------------------------------------------------
# find_row
# ---------------------------------------------------------------------------


class TestFindRow:
    async def test_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1%21A%3AA",
            json=_load_json("find_row_values.json"),
        )

        result = await google_sheets_find_row(
            FindRowParams(
                spreadsheet_id=_SPREADSHEET_ID,
                sheet="Sheet1",
                column="A",
                value="Bob",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, FindRowResult)
        assert result.success is True
        assert result.row_number == 3

    async def test_not_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SHEETS_BASE}/{_SPREADSHEET_ID}/values/Sheet1%21A%3AA",
            json=_load_json("find_row_values.json"),
        )

        result = await google_sheets_find_row(
            FindRowParams(
                spreadsheet_id=_SPREADSHEET_ID,
                sheet="Sheet1",
                column="A",
                value="Zara",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.row_number == 0

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_sheets_find_row(
            FindRowParams(
                spreadsheet_id="bad_id",
                sheet="Sheet1",
                column="A",
                value="Alice",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_sheets_find_row._tool_definition
        assert defn.name == "google_sheets_find_row"
        assert defn.provider == "google"
        assert defn.service == "google_sheets"
        assert "https://www.googleapis.com/auth/spreadsheets" in defn.scopes
