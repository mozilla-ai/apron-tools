"""Tests for Microsoft Excel provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.microsoft.excel.types import (
    AddWorksheetParams,
    AddWorksheetResult,
    AppendRowParams,
    AppendRowResult,
    CreateWorkbookParams,
    CreateWorkbookResult,
    DriveItem,
    GetWorkbookInfoParams,
    GetWorkbookInfoResult,
    ListWorkbooksParams,
    ListWorkbooksResult,
    RangeData,
    ReadWorksheetParams,
    ReadWorksheetResult,
    UpdateWorksheetParams,
    UpdateWorksheetResult,
    WorksheetSummary,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListWorkbooksParams:
    def test_defaults(self):
        params = ListWorkbooksParams()
        assert params.max_results == 20

    def test_custom(self):
        params = ListWorkbooksParams(max_results=5)
        assert params.max_results == 5


class TestGetWorkbookInfoParams:
    def test_required(self):
        params = GetWorkbookInfoParams(item_id="item-001")
        assert params.item_id == "item-001"


class TestReadWorksheetParams:
    def test_defaults(self):
        params = ReadWorksheetParams(item_id="item-001")
        assert params.item_id == "item-001"
        assert params.worksheet_name == "Sheet1"
        assert params.range_address == ""

    def test_custom(self):
        params = ReadWorksheetParams(
            item_id="item-001",
            worksheet_name="Data",
            range_address="A1:D10",
        )
        assert params.worksheet_name == "Data"
        assert params.range_address == "A1:D10"


class TestUpdateWorksheetParams:
    def test_required(self):
        params = UpdateWorksheetParams(
            item_id="item-001",
            worksheet_name="Sheet1",
            range_address="A1:B2",
            values=[["a", "b"], ["c", "d"]],
        )
        assert params.item_id == "item-001"
        assert params.worksheet_name == "Sheet1"
        assert params.range_address == "A1:B2"
        assert params.values == [["a", "b"], ["c", "d"]]


class TestAppendRowParams:
    def test_required(self):
        params = AppendRowParams(
            item_id="item-001",
            worksheet_name="Sheet1",
            values=[["x", "y"]],
        )
        assert params.item_id == "item-001"
        assert params.worksheet_name == "Sheet1"
        assert params.values == [["x", "y"]]


class TestCreateWorkbookParams:
    def test_defaults(self):
        params = CreateWorkbookParams(name="Budget")
        assert params.name == "Budget"
        assert params.folder_path == "root"

    def test_custom_folder(self):
        params = CreateWorkbookParams(name="Budget", folder_path="Documents/Projects")
        assert params.folder_path == "Documents/Projects"


class TestAddWorksheetParams:
    def test_required(self):
        params = AddWorksheetParams(item_id="item-001", name="Summary")
        assert params.item_id == "item-001"
        assert params.name == "Summary"


# ---------------------------------------------------------------------------
# DriveItem
# ---------------------------------------------------------------------------


class TestDriveItem:
    def test_parse_with_aliases(self):
        data = _load_json("get_workbook_item.json")
        item = DriveItem.model_validate(data)

        assert item.id == "item-001"
        assert item.name == "Budget.xlsx"
        assert item.size == 12345
        assert item.web_url == "https://contoso.sharepoint.com/sites/team/Documents/Budget.xlsx"
        assert item.last_modified_date_time == "2024-03-10T14:22:00Z"
        assert item.created_date_time == "2024-01-15T10:00:00Z"

    def test_ignores_extra_fields(self):
        data = _load_json("get_workbook_item.json")
        item = DriveItem.model_validate(data)
        assert not hasattr(item, "file")
        assert not hasattr(item, "parentReference")


# ---------------------------------------------------------------------------
# WorksheetSummary
# ---------------------------------------------------------------------------


class TestWorksheetSummary:
    def test_parse(self):
        data = _load_json("get_workbook_worksheets.json")
        ws = WorksheetSummary.model_validate(data["value"][0])

        assert ws.id == "ws-001"
        assert ws.position == 0
        assert ws.name == "Sheet1"
        assert ws.visibility == "Visible"


# ---------------------------------------------------------------------------
# RangeData
# ---------------------------------------------------------------------------


class TestRangeData:
    def test_parse_with_aliases(self):
        data = _load_json("read_worksheet.json")
        rd = RangeData.model_validate(data)

        assert rd.address == "Sheet1!A1:D5"
        assert rd.cell_count == 20
        assert rd.column_count == 4
        assert rd.row_count == 5
        assert len(rd.values) == 5
        assert rd.values[0] == ["Name", "Age", "City", "Score"]


# ---------------------------------------------------------------------------
# ListWorkbooksResult
# ---------------------------------------------------------------------------


class TestListWorkbooksResult:
    def test_success(self):
        data = _load_json("list_workbooks.json")
        items = [DriveItem.model_validate(v) for v in data["value"] if v["name"].endswith(".xlsx")]
        result = ListWorkbooksResult(success=True, workbooks=items)

        assert result.success is True
        assert len(result.workbooks) == 2

    def test_str_output(self):
        data = _load_json("list_workbooks.json")
        items = [DriveItem.model_validate(v) for v in data["value"] if v["name"].endswith(".xlsx")]
        result = ListWorkbooksResult(success=True, workbooks=items)
        text = str(result)

        assert "2 workbook(s)" in text
        assert "Budget.xlsx" in text
        assert "Expenses.xlsx" in text

    def test_str_empty(self):
        result = ListWorkbooksResult(success=True, workbooks=[])
        assert str(result) == "No workbooks found."

    def test_str_on_error(self):
        result = ListWorkbooksResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# GetWorkbookInfoResult
# ---------------------------------------------------------------------------


class TestGetWorkbookInfoResult:
    def test_success(self):
        item = DriveItem.model_validate(_load_json("get_workbook_item.json"))
        ws_data = _load_json("get_workbook_worksheets.json")
        worksheets = [WorksheetSummary.model_validate(ws) for ws in ws_data["value"]]
        result = GetWorkbookInfoResult(success=True, item=item, worksheets=worksheets)

        assert result.success is True
        assert result.item.name == "Budget.xlsx"
        assert len(result.worksheets) == 2

    def test_str_output(self):
        item = DriveItem.model_validate(_load_json("get_workbook_item.json"))
        ws_data = _load_json("get_workbook_worksheets.json")
        worksheets = [WorksheetSummary.model_validate(ws) for ws in ws_data["value"]]
        result = GetWorkbookInfoResult(success=True, item=item, worksheets=worksheets)
        text = str(result)

        assert "Budget.xlsx" in text
        assert "Sheet1" in text
        assert "Data" in text
        assert "item-001" in text

    def test_str_on_error(self):
        result = GetWorkbookInfoResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_no_item(self):
        result = GetWorkbookInfoResult(success=True, item=None)
        assert str(result) == "No workbook info available."


# ---------------------------------------------------------------------------
# ReadWorksheetResult
# ---------------------------------------------------------------------------


class TestReadWorksheetResult:
    def test_success(self):
        rd = RangeData.model_validate(_load_json("read_worksheet.json"))
        result = ReadWorksheetResult(success=True, range_data=rd)

        assert result.success is True
        assert result.range_data.row_count == 5
        assert result.range_data.column_count == 4

    def test_str_output(self):
        rd = RangeData.model_validate(_load_json("read_worksheet.json"))
        result = ReadWorksheetResult(success=True, range_data=rd)
        text = str(result)

        assert "Sheet1!A1:D5" in text
        assert "5 row(s)" in text
        assert "4 column(s)" in text

    def test_str_empty(self):
        result = ReadWorksheetResult(success=True, range_data=None)
        assert "No data" in str(result)

    def test_str_on_error(self):
        result = ReadWorksheetResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# UpdateWorksheetResult
# ---------------------------------------------------------------------------


class TestUpdateWorksheetResult:
    def test_success(self):
        rd = RangeData.model_validate(_load_json("update_worksheet.json"))
        result = UpdateWorksheetResult(success=True, range_data=rd)

        assert result.success is True
        assert result.range_data.address == "Sheet1!A6:D6"

    def test_str_output(self):
        rd = RangeData.model_validate(_load_json("update_worksheet.json"))
        result = UpdateWorksheetResult(success=True, range_data=rd)
        text = str(result)

        assert "Sheet1!A6:D6" in text
        assert "Rows: 1" in text
        assert "Columns: 4" in text

    def test_str_on_error(self):
        result = UpdateWorksheetResult(success=False, error="Bad range")
        assert str(result) == "Error: Bad range"

    def test_str_no_range_data(self):
        result = UpdateWorksheetResult(success=True, range_data=None)
        assert str(result) == "Update completed."


# ---------------------------------------------------------------------------
# AppendRowResult
# ---------------------------------------------------------------------------


class TestAppendRowResult:
    def test_success(self):
        rd = RangeData.model_validate(_load_json("append_row_result.json"))
        result = AppendRowResult(success=True, range_data=rd)

        assert result.success is True
        assert result.range_data.address == "Sheet1!A6:D6"

    def test_str_output(self):
        rd = RangeData.model_validate(_load_json("append_row_result.json"))
        result = AppendRowResult(success=True, range_data=rd)
        text = str(result)

        assert "1 row(s)" in text
        assert "Sheet1!A6:D6" in text

    def test_str_on_error(self):
        result = AppendRowResult(success=False, error="Sheet not found")
        assert str(result) == "Error: Sheet not found"

    def test_str_no_range_data(self):
        result = AppendRowResult(success=True, range_data=None)
        assert str(result) == "Append completed."


# ---------------------------------------------------------------------------
# CreateWorkbookResult
# ---------------------------------------------------------------------------


class TestCreateWorkbookResult:
    def test_success(self):
        item = DriveItem.model_validate(_load_json("create_workbook_item.json"))
        result = CreateWorkbookResult(success=True, item=item)

        assert result.success is True
        assert result.item.name == "NewWorkbook.xlsx"
        assert result.item.id == "item-new-001"

    def test_str_output(self):
        item = DriveItem.model_validate(_load_json("create_workbook_item.json"))
        result = CreateWorkbookResult(success=True, item=item)
        text = str(result)

        assert "NewWorkbook.xlsx" in text
        assert "item-new-001" in text
        assert "contoso.sharepoint.com" in text

    def test_str_on_error(self):
        result = CreateWorkbookResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"

    def test_str_no_item(self):
        result = CreateWorkbookResult(success=True, item=None)
        assert str(result) == "Workbook created."


# ---------------------------------------------------------------------------
# AddWorksheetResult
# ---------------------------------------------------------------------------


class TestAddWorksheetResult:
    def test_success(self):
        ws = WorksheetSummary.model_validate(_load_json("add_worksheet.json"))
        result = AddWorksheetResult(success=True, worksheet=ws)

        assert result.success is True
        assert result.worksheet.name == "NewSheet"
        assert result.worksheet.id == "ws-003"

    def test_str_output(self):
        ws = WorksheetSummary.model_validate(_load_json("add_worksheet.json"))
        result = AddWorksheetResult(success=True, worksheet=ws)
        text = str(result)

        assert "NewSheet" in text
        assert "ws-003" in text

    def test_str_on_error(self):
        result = AddWorksheetResult(success=False, error="Duplicate name")
        assert str(result) == "Error: Duplicate name"

    def test_str_no_worksheet(self):
        result = AddWorksheetResult(success=True, worksheet=None)
        assert str(result) == "Worksheet added."
