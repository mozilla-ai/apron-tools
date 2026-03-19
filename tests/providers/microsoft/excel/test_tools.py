"""Tests for Microsoft Excel tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.microsoft.excel.tools import (
    microsoft_excel_add_worksheet,
    microsoft_excel_append_row,
    microsoft_excel_create_workbook,
    microsoft_excel_get_workbook_info,
    microsoft_excel_list_workbooks,
    microsoft_excel_read_worksheet,
    microsoft_excel_update_worksheet,
)
from any_tool.providers.microsoft.excel.types import (
    AddWorksheetParams,
    AddWorksheetResult,
    AppendRowParams,
    AppendRowResult,
    CreateWorkbookParams,
    CreateWorkbookResult,
    GetWorkbookInfoParams,
    GetWorkbookInfoResult,
    ListWorkbooksParams,
    ListWorkbooksResult,
    ReadWorksheetParams,
    ReadWorksheetResult,
    UpdateWorksheetParams,
    UpdateWorksheetResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_ITEM_ID = "item-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_workbooks
# ---------------------------------------------------------------------------


class TestListWorkbooks:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='xls')",
            json=_load_json("list_workbooks.json"),
        )

        result = await microsoft_excel_list_workbooks(ListWorkbooksParams(), token=_TOKEN)

        assert isinstance(result, ListWorkbooksResult)
        assert result.success is True
        assert len(result.workbooks) == 2
        assert result.workbooks[0].name == "Budget.xlsx"
        assert result.workbooks[1].name == "Expenses.xlsx"

    async def test_filters_non_excel_files(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='xls')",
            json=_load_json("list_workbooks.json"),
        )

        result = await microsoft_excel_list_workbooks(ListWorkbooksParams(), token=_TOKEN)

        names = [w.name for w in result.workbooks]
        assert "README.txt" not in names

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await microsoft_excel_list_workbooks(ListWorkbooksParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_list_workbooks._tool_definition
        assert defn.name == "microsoft_excel_list_workbooks"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# get_workbook_info
# ---------------------------------------------------------------------------


class TestGetWorkbookInfo:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}?%24select=id%2Cname%2Csize%2CwebUrl%2CcreatedDateTime%2ClastModifiedDateTime",
            json=_load_json("get_workbook_item.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets",
            json=_load_json("get_workbook_worksheets.json"),
        )

        result = await microsoft_excel_get_workbook_info(
            GetWorkbookInfoParams(item_id=_ITEM_ID),
            token=_TOKEN,
        )

        assert isinstance(result, GetWorkbookInfoResult)
        assert result.success is True
        assert result.item.name == "Budget.xlsx"
        assert len(result.worksheets) == 2
        assert result.worksheets[0].name == "Sheet1"
        assert result.worksheets[1].name == "Data"

    async def test_item_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_excel_get_workbook_info(
            GetWorkbookInfoParams(item_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_get_workbook_info._tool_definition
        assert defn.name == "microsoft_excel_get_workbook_info"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_worksheet
# ---------------------------------------------------------------------------


class TestReadWorksheet:
    async def test_success_used_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/usedRange",
            json=_load_json("read_worksheet.json"),
        )

        result = await microsoft_excel_read_worksheet(
            ReadWorksheetParams(item_id=_ITEM_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadWorksheetResult)
        assert result.success is True
        assert result.range_data.address == "Sheet1!A1:D5"
        assert result.range_data.row_count == 5
        assert len(result.range_data.values) == 5

    async def test_success_specific_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/range(address='A1:B2')",
            json={
                "address": "Sheet1!A1:B2",
                "cellCount": 4,
                "columnCount": 2,
                "rowCount": 2,
                "values": [["a", "b"], ["c", "d"]],
            },
        )

        result = await microsoft_excel_read_worksheet(
            ReadWorksheetParams(
                item_id=_ITEM_ID,
                worksheet_name="Sheet1",
                range_address="A1:B2",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.range_data.row_count == 2
        assert result.range_data.column_count == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_excel_read_worksheet(
            ReadWorksheetParams(item_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_read_worksheet._tool_definition
        assert defn.name == "microsoft_excel_read_worksheet"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# update_worksheet
# ---------------------------------------------------------------------------


class TestUpdateWorksheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/range(address='A6:D6')",
            json=_load_json("update_worksheet.json"),
        )

        result = await microsoft_excel_update_worksheet(
            UpdateWorksheetParams(
                item_id=_ITEM_ID,
                worksheet_name="Sheet1",
                range_address="A6:D6",
                values=[["Eve", 31, "Berlin", 91]],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateWorksheetResult)
        assert result.success is True
        assert result.range_data.address == "Sheet1!A6:D6"
        assert result.range_data.row_count == 1

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await microsoft_excel_update_worksheet(
            UpdateWorksheetParams(
                item_id="bad-id",
                worksheet_name="Sheet1",
                range_address="A1:B2",
                values=[["a", "b"]],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_update_worksheet._tool_definition
        assert defn.name == "microsoft_excel_update_worksheet"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# append_row
# ---------------------------------------------------------------------------


class TestAppendRow:
    async def test_success_via_used_range(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/tables",
            json=_load_json("append_row_tables.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/usedRange",
            json=_load_json("append_row_used_range.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/range(address='A6:D6')",
            json=_load_json("append_row_result.json"),
        )

        result = await microsoft_excel_append_row(
            AppendRowParams(
                item_id=_ITEM_ID,
                worksheet_name="Sheet1",
                values=[["Eve", 31, "Berlin", 91]],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, AppendRowResult)
        assert result.success is True
        assert result.range_data.address == "Sheet1!A6:D6"

    async def test_empty_values(self) -> None:
        result = await microsoft_excel_append_row(
            AppendRowParams(
                item_id=_ITEM_ID,
                worksheet_name="Sheet1",
                values=[],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "No data" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/tables",
            json=_load_json("append_row_tables.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/usedRange",
            json=_load_json("append_row_used_range.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/Sheet1/range(address='A6:A6')",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_excel_append_row(
            AppendRowParams(
                item_id=_ITEM_ID,
                worksheet_name="Sheet1",
                values=[["x"]],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_append_row._tool_definition
        assert defn.name == "microsoft_excel_append_row"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# create_workbook
# ---------------------------------------------------------------------------


class TestCreateWorkbook:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/NewWorkbook.xlsx:/workbook/createSession",
            json=_load_json("create_workbook_session.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/NewWorkbook.xlsx",
            json=_load_json("create_workbook_item.json"),
        )

        result = await microsoft_excel_create_workbook(
            CreateWorkbookParams(name="NewWorkbook"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateWorkbookResult)
        assert result.success is True
        assert result.item.name == "NewWorkbook.xlsx"
        assert result.item.id == "item-new-001"

    async def test_appends_xlsx_extension(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Test.xlsx:/workbook/createSession",
            json=_load_json("create_workbook_session.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Test.xlsx",
            json=_load_json("create_workbook_item.json"),
        )

        result = await microsoft_excel_create_workbook(
            CreateWorkbookParams(name="Test"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_session_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await microsoft_excel_create_workbook(
            CreateWorkbookParams(name="Fail"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_create_workbook._tool_definition
        assert defn.name == "microsoft_excel_create_workbook"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# add_worksheet
# ---------------------------------------------------------------------------


class TestAddWorksheet:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/workbook/worksheets/add",
            json=_load_json("add_worksheet.json"),
        )

        result = await microsoft_excel_add_worksheet(
            AddWorksheetParams(item_id=_ITEM_ID, name="NewSheet"),
            token=_TOKEN,
        )

        assert isinstance(result, AddWorksheetResult)
        assert result.success is True
        assert result.worksheet.name == "NewSheet"
        assert result.worksheet.id == "ws-003"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Duplicate sheet name")

        result = await microsoft_excel_add_worksheet(
            AddWorksheetParams(item_id="bad-id", name="Sheet1"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_excel_add_worksheet._tool_definition
        assert defn.name == "microsoft_excel_add_worksheet"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_excel"
        assert "Files.ReadWrite" in defn.scopes
