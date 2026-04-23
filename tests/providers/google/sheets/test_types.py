"""Tests for Google Sheets provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

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
    SpreadsheetFile,
    UpdateSpreadsheetParams,
    UpdateSpreadsheetResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListSpreadsheetsParams:
    def test_defaults(self):
        params = ListSpreadsheetsParams()
        assert params.max_results == 20

    def test_custom(self):
        params = ListSpreadsheetsParams(max_results=5)
        assert params.max_results == 5


class TestCreateSpreadsheetParams:
    def test_required(self):
        params = CreateSpreadsheetParams(title="Budget 2024")
        assert params.title == "Budget 2024"
        assert params.sheet_names is None

    def test_with_sheets(self):
        params = CreateSpreadsheetParams(title="Budget", sheet_names=["Income", "Expenses"])
        assert params.sheet_names == ["Income", "Expenses"]


class TestCopySpreadsheetParams:
    def test_required(self):
        params = CopySpreadsheetParams(spreadsheet_id="abc123", new_title="Copy")
        assert params.spreadsheet_id == "abc123"
        assert params.new_title == "Copy"


class TestReadSpreadsheetParams:
    def test_required(self):
        params = ReadSpreadsheetParams(spreadsheet_id="abc123")
        assert params.spreadsheet_id == "abc123"
        assert params.range == ""
        assert params.include_metadata is False

    def test_custom(self):
        params = ReadSpreadsheetParams(
            spreadsheet_id="abc123",
            range="Sheet1!A1:D10",
            include_metadata=True,
        )
        assert params.range == "Sheet1!A1:D10"
        assert params.include_metadata is True


class TestUpdateSpreadsheetParams:
    def test_required(self):
        params = UpdateSpreadsheetParams(
            spreadsheet_id="abc123",
            range="Sheet1!A1:B2",
            values=[["a", "b"], ["c", "d"]],
        )
        assert params.spreadsheet_id == "abc123"
        assert params.range == "Sheet1!A1:B2"
        assert params.values == [["a", "b"], ["c", "d"]]


class TestAppendRowParams:
    def test_required(self):
        params = AppendRowParams(
            spreadsheet_id="abc123",
            range="Sheet1",
            values=[["x", "y"]],
        )
        assert params.spreadsheet_id == "abc123"
        assert params.range == "Sheet1"
        assert params.values == [["x", "y"]]


class TestAddSheetParams:
    def test_required(self):
        params = AddSheetParams(spreadsheet_id="abc123", title="Summary")
        assert params.spreadsheet_id == "abc123"
        assert params.title == "Summary"


class TestFindRowParams:
    def test_required(self):
        params = FindRowParams(
            spreadsheet_id="abc123",
            sheet="Sheet1",
            column="A",
            value="Alice",
        )
        assert params.spreadsheet_id == "abc123"
        assert params.sheet == "Sheet1"
        assert params.column == "A"
        assert params.value == "Alice"


# ---------------------------------------------------------------------------
# ListSpreadsheetsResult
# ---------------------------------------------------------------------------


class TestListSpreadsheetsResult:
    def test_parse_files(self):
        data = _load_json("list_spreadsheets.json")
        files = [SpreadsheetFile.model_validate(f) for f in data["files"]]
        result = ListSpreadsheetsResult(success=True, files=files)

        assert result.success is True
        assert len(result.files) == 2

    def test_file_fields(self):
        data = _load_json("list_spreadsheets.json")
        f = SpreadsheetFile.model_validate(data["files"][0])

        assert f.id == "spreadsheet-id-001"
        assert f.name == "Budget 2024"
        assert f.created_time == "2024-01-15T10:30:00Z"
        assert f.modified_time == "2024-03-10T14:22:00Z"

    def test_str_output(self):
        data = _load_json("list_spreadsheets.json")
        files = [SpreadsheetFile.model_validate(f) for f in data["files"]]
        result = ListSpreadsheetsResult(success=True, files=files)
        text = str(result)

        assert "2 spreadsheet(s)" in text
        assert "Budget 2024" in text
        assert "Project Tracker" in text

    def test_str_on_error(self):
        result = ListSpreadsheetsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListSpreadsheetsResult(success=True, files=[])
        assert str(result) == "No spreadsheets found."


# ---------------------------------------------------------------------------
# CreateSpreadsheetResult
# ---------------------------------------------------------------------------


class TestCreateSpreadsheetResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_spreadsheet.json")
        result = CreateSpreadsheetResult.model_validate(data)

        assert result.success is True
        assert result.spreadsheet_id == "spreadsheet-id-001"
        assert "edit" in result.spreadsheet_url
        assert result.properties.title == "Budget 2024"
        assert len(result.sheets) == 1
        assert result.sheets[0].properties.title == "Sheet1"

    def test_str_output(self):
        data = _load_json("create_spreadsheet.json")
        result = CreateSpreadsheetResult.model_validate(data)
        text = str(result)

        assert "Budget 2024" in text
        assert "spreadsheet-id-001" in text
        assert "Sheet1" in text

    def test_str_on_error(self):
        result = CreateSpreadsheetResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# CopySpreadsheetResult
# ---------------------------------------------------------------------------


class TestCopySpreadsheetResult:
    def test_success(self):
        result = CopySpreadsheetResult(
            success=True,
            id="spreadsheet-id-003",
            name="Copy of Budget 2024",
            original_name="Budget 2024",
        )

        assert result.success is True
        assert result.id == "spreadsheet-id-003"
        assert result.name == "Copy of Budget 2024"
        assert result.original_name == "Budget 2024"

    def test_str_output(self):
        result = CopySpreadsheetResult(
            success=True,
            id="spreadsheet-id-003",
            name="Copy of Budget 2024",
            original_name="Budget 2024",
        )
        text = str(result)

        assert "copied" in text
        assert "Budget 2024" in text
        assert "Copy of Budget 2024" in text
        assert "spreadsheet-id-003" in text

    def test_str_on_error(self):
        result = CopySpreadsheetResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ReadSpreadsheetResult
# ---------------------------------------------------------------------------


class TestReadSpreadsheetResult:
    def test_parse_values(self):
        data = _load_json("read_spreadsheet_values.json")
        result = ReadSpreadsheetResult(
            success=True,
            range=data["range"],
            values=data["values"],
        )

        assert result.success is True
        assert result.range == "Sheet1!A1:D5"
        assert len(result.values) == 4
        assert result.values[0] == ["Name", "Age", "City", "Score"]

    def test_str_output_is_parseable_json(self):
        """``str(result)`` must round-trip through ``json.loads``.

        Downstream agents parse the read-spreadsheet output as JSON.
        Any non-JSON prefix breaks them — see issue #92.
        """
        data = _load_json("read_spreadsheet_values.json")
        result = ReadSpreadsheetResult(
            success=True,
            range=data["range"],
            values=data["values"],
        )

        parsed = json.loads(str(result))

        assert isinstance(parsed, list)
        assert len(parsed) == 4
        assert parsed[0] == {"row": 1, "A": "Name", "B": "Age", "C": "City", "D": "Score"}
        assert parsed[1] == {"row": 2, "A": "Alice", "B": "30", "C": "New York", "D": "95"}

    def test_str_output_with_metadata_is_parseable_json(self):
        """With metadata, the output is a JSON object wrapping rows and metadata."""
        data = _load_json("read_spreadsheet_values.json")
        result = ReadSpreadsheetResult(
            success=True,
            range=data["range"],
            values=data["values"],
            title="Budget 2024",
            sheet_names=["Sheet1"],
        )

        parsed = json.loads(str(result))

        assert parsed["metadata"] == {"title": "Budget 2024", "sheets": ["Sheet1"]}
        assert parsed["range"] == "Sheet1!A1:D5"
        assert isinstance(parsed["rows"], list)
        assert len(parsed["rows"]) == 4
        assert parsed["rows"][0] == {
            "row": 1,
            "A": "Name",
            "B": "Age",
            "C": "City",
            "D": "Score",
        }

    def test_str_output_honors_range_offset(self):
        """Row numbers and column letters must reflect the returned range's origin."""
        result = ReadSpreadsheetResult(
            success=True,
            range="Sheet1!B2:C3",
            values=[["x", "y"], ["z", "w"]],
        )

        parsed = json.loads(str(result))

        assert parsed[0] == {"row": 2, "B": "x", "C": "y"}
        assert parsed[1] == {"row": 3, "B": "z", "C": "w"}

    def test_str_output_omits_empty_trailing_cells(self):
        """Sheets API returns ragged rows; only present cells should appear."""
        result = ReadSpreadsheetResult(
            success=True,
            range="Sheet1!A1:C2",
            values=[["Name", "Age", "City"], ["Alice"]],
        )

        parsed = json.loads(str(result))

        assert parsed[0] == {"row": 1, "A": "Name", "B": "Age", "C": "City"}
        assert parsed[1] == {"row": 2, "A": "Alice"}

    def test_str_empty(self):
        """An empty range serialises as an empty JSON list."""
        result = ReadSpreadsheetResult(success=True, range="Sheet1!A1:D5", values=[])

        parsed = json.loads(str(result))

        assert parsed == []

    def test_str_empty_with_metadata(self):
        """An empty range with metadata serialises to the wrapped JSON object."""
        result = ReadSpreadsheetResult(
            success=True,
            range="Sheet1!A1:D5",
            values=[],
            title="Budget 2024",
            sheet_names=["Sheet1"],
        )

        parsed = json.loads(str(result))

        assert parsed == {
            "metadata": {"title": "Budget 2024", "sheets": ["Sheet1"]},
            "range": "Sheet1!A1:D5",
            "rows": [],
        }

    def test_str_on_error(self):
        result = ReadSpreadsheetResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# UpdateSpreadsheetResult
# ---------------------------------------------------------------------------


class TestUpdateSpreadsheetResult:
    def test_parse_real_api_response(self):
        data = _load_json("update_spreadsheet.json")
        result = UpdateSpreadsheetResult.model_validate(data)

        assert result.success is True
        assert result.spreadsheet_id == "spreadsheet-id-001"
        assert result.updated_range == "Sheet1!A1:D5"
        assert result.updated_rows == 4
        assert result.updated_columns == 4
        assert result.updated_cells == 16

    def test_str_output(self):
        data = _load_json("update_spreadsheet.json")
        result = UpdateSpreadsheetResult.model_validate(data)
        text = str(result)

        assert "16 cell(s)" in text
        assert "Sheet1!A1:D5" in text
        assert "Rows: 4" in text

    def test_str_on_error(self):
        result = UpdateSpreadsheetResult(success=False, error="Range invalid")
        assert str(result) == "Error: Range invalid"


# ---------------------------------------------------------------------------
# AppendRowResult
# ---------------------------------------------------------------------------


class TestAppendRowResult:
    def test_parse_real_api_response(self):
        data = _load_json("append_row.json")
        result = AppendRowResult.model_validate(data)

        assert result.success is True
        assert result.spreadsheet_id == "spreadsheet-id-001"
        assert result.table_range == "Sheet1!A1:D4"
        assert result.updated_range == "Sheet1!A5:D5"
        assert result.updated_rows == 1
        assert result.updated_cells == 4

    def test_str_output(self):
        data = _load_json("append_row.json")
        result = AppendRowResult.model_validate(data)
        text = str(result)

        assert "4 cell(s)" in text
        assert "Sheet1!A5:D5" in text

    def test_str_on_error(self):
        result = AppendRowResult(success=False, error="Sheet not found")
        assert str(result) == "Error: Sheet not found"


# ---------------------------------------------------------------------------
# AddSheetResult
# ---------------------------------------------------------------------------


class TestAddSheetResult:
    def test_parse_real_api_response(self):
        data = _load_json("add_sheet.json")
        result = AddSheetResult.model_validate(data)

        assert result.success is True
        assert result.spreadsheet_id == "spreadsheet-id-001"
        assert result.sheet_id == 123456
        assert result.title == "New Sheet"

    def test_str_output(self):
        data = _load_json("add_sheet.json")
        result = AddSheetResult.model_validate(data)
        text = str(result)

        assert "New Sheet" in text
        assert "123456" in text

    def test_str_on_error(self):
        result = AddSheetResult(success=False, error="Duplicate title")
        assert str(result) == "Error: Duplicate title"


# ---------------------------------------------------------------------------
# FindRowResult
# ---------------------------------------------------------------------------


class TestFindRowResult:
    def test_found(self):
        result = FindRowResult(
            success=True,
            row_number=3,
            sheet="Sheet1",
            column="A",
            value="Bob",
        )

        assert result.success is True
        assert result.row_number == 3

    def test_str_found_is_parseable_json_integer(self):
        """Found-row output must round-trip as a JSON integer so agents can parse it."""
        result = FindRowResult(
            success=True,
            row_number=3,
            sheet="Sheet1",
            column="A",
            value="Bob",
        )

        assert json.loads(str(result)) == 3

    def test_str_not_found(self):
        result = FindRowResult(
            success=True,
            row_number=0,
            sheet="Sheet1",
            column="A",
            value="Zara",
        )
        text = str(result)

        assert "No row found" in text
        assert "Zara" in text

    def test_str_on_error(self):
        result = FindRowResult(success=False, error="API error")
        assert str(result) == "Error: API error"
