"""Pydantic models for Google Sheets API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListSpreadsheetsParams(BaseModel):
    """Parameters for listing Google Sheets spreadsheets."""

    max_results: int = 20


class CreateSpreadsheetParams(BaseModel):
    """Parameters for creating a new spreadsheet."""

    title: str
    sheet_names: list[str] | None = None


class CopySpreadsheetParams(BaseModel):
    """Parameters for copying an existing spreadsheet."""

    spreadsheet_id: str
    new_title: str


class ReadSpreadsheetParams(BaseModel):
    """Parameters for reading spreadsheet data."""

    spreadsheet_id: str
    range: str = ""
    include_metadata: bool = False


class UpdateSpreadsheetParams(BaseModel):
    """Parameters for updating spreadsheet values."""

    spreadsheet_id: str
    range: str
    values: list[list[str]]


class AppendRowParams(BaseModel):
    """Parameters for appending rows to a spreadsheet."""

    spreadsheet_id: str
    range: str
    values: list[list[str]]


class AddSheetParams(BaseModel):
    """Parameters for adding a sheet tab to a spreadsheet."""

    spreadsheet_id: str
    title: str


class FindRowParams(BaseModel):
    """Parameters for finding a row by column value."""

    spreadsheet_id: str
    sheet: str
    column: str
    value: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class SpreadsheetFile(BaseModel):
    """A spreadsheet file from the Drive API listing."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")


class SheetProperties(BaseModel):
    """Properties of a single sheet tab."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sheet_id: int = Field(default=0, alias="sheetId")
    title: str = "Sheet1"
    index: int = 0


class SheetEntry(BaseModel):
    """A sheet tab containing its properties."""

    model_config = ConfigDict(extra="ignore")

    properties: SheetProperties = SheetProperties()


class SpreadsheetProperties(BaseModel):
    """Top-level properties of a spreadsheet."""

    model_config = ConfigDict(extra="ignore")

    title: str = "Untitled"


class AddSheetReplyProperties(BaseModel):
    """Properties returned in an addSheet reply."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sheet_id: int = Field(default=0, alias="sheetId")
    title: str = ""
    index: int = 0


class AddSheetReply(BaseModel):
    """A single addSheet reply entry."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    add_sheet: AddSheetReplyProperties = Field(
        default_factory=AddSheetReplyProperties,
        alias="addSheet",
    )


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListSpreadsheetsResult(ToolResult):
    """Result of listing spreadsheets from Drive."""

    model_config = ConfigDict(extra="ignore")

    files: list[SpreadsheetFile] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the spreadsheets."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.files:
            return "No spreadsheets found."
        lines = [f"Found {len(self.files)} spreadsheet(s):"]
        for f in self.files:
            lines.append(f"  - {f.name} (id={f.id})")
        return "\n".join(lines)


class CreateSpreadsheetResult(ToolResult):
    """Result of creating a new spreadsheet."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    spreadsheet_id: str = Field(default="", alias="spreadsheetId")
    spreadsheet_url: str = Field(default="", alias="spreadsheetUrl")
    properties: SpreadsheetProperties = SpreadsheetProperties()
    sheets: list[SheetEntry] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created spreadsheet."""
        if not self.success:
            return f"Error: {self.error}"
        title = self.properties.title
        sheet_names = [s.properties.title for s in self.sheets]
        sheets_str = ", ".join(sheet_names) if sheet_names else "none"
        return (
            f"Spreadsheet '{title}' created.\n"
            f"ID: {self.spreadsheet_id}\n"
            f"URL: {self.spreadsheet_url}\n"
            f"Sheets: {sheets_str}"
        )


class CopySpreadsheetResult(ToolResult):
    """Result of copying a spreadsheet."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""
    original_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the copied spreadsheet."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/spreadsheets/d/{self.id}"
        return f"Spreadsheet copied.\nOriginal: '{self.original_name}'\nCopy: '{self.name}'\nID: {self.id}\nURL: {url}"


class ReadSpreadsheetResult(ToolResult):
    """Result of reading spreadsheet data."""

    model_config = ConfigDict(extra="ignore")

    range: str = ""
    values: list[list[str]] = []
    title: str = ""
    sheet_names: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the spreadsheet data."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.values:
            return f"No data in range '{self.range}'."
        row_count = len(self.values)
        col_count = max(len(row) for row in self.values) if self.values else 0
        header = ""
        if self.title:
            header = f"Spreadsheet: {self.title}\n"
        if self.sheet_names:
            header += f"Sheets: {', '.join(self.sheet_names)}\n"
        return f"{header}Range: {self.range}\nData: {row_count} row(s) x {col_count} column(s)"


class UpdateSpreadsheetResult(ToolResult):
    """Result of updating spreadsheet values."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    spreadsheet_id: str = Field(default="", alias="spreadsheetId")
    updated_range: str = Field(default="", alias="updatedRange")
    updated_rows: int = Field(default=0, alias="updatedRows")
    updated_columns: int = Field(default=0, alias="updatedColumns")
    updated_cells: int = Field(default=0, alias="updatedCells")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the update."""
        if not self.success:
            return f"Error: {self.error}"
        return (
            f"Updated {self.updated_cells} cell(s) in '{self.updated_range}'.\n"
            f"Rows: {self.updated_rows}, Columns: {self.updated_columns}"
        )


class AppendRowResult(ToolResult):
    """Result of appending rows to a spreadsheet."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    spreadsheet_id: str = Field(default="", alias="spreadsheetId")
    table_range: str = Field(default="", alias="tableRange")
    updated_range: str = ""
    updated_rows: int = 0
    updated_cells: int = 0

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            updates = data.get("updates", {})
            data["updated_range"] = updates.get("updatedRange", "")
            data["updated_rows"] = updates.get("updatedRows", 0)
            data["updated_cells"] = updates.get("updatedCells", 0)
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the append."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Appended {self.updated_cells} cell(s).\nUpdated range: '{self.updated_range}'"


class AddSheetResult(ToolResult):
    """Result of adding a new sheet tab."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    spreadsheet_id: str = Field(default="", alias="spreadsheetId")
    sheet_id: int = 0
    title: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            replies = data.get("replies", [])
            if replies:
                props = replies[0].get("addSheet", {}).get("properties", {})
                data["sheet_id"] = props.get("sheetId", 0)
                data["title"] = props.get("title", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the added sheet."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Sheet '{self.title}' added (sheetId={self.sheet_id})."


class FindRowResult(ToolResult):
    """Result of finding a row by column value."""

    model_config = ConfigDict(extra="ignore")

    row_number: int = 0
    sheet: str = ""
    column: str = ""
    value: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the found row."""
        if not self.success:
            return f"Error: {self.error}"
        if self.row_number == 0:
            return f"No row found where column {self.column} equals '{self.value}'."
        return f"Row {self.row_number} (column {self.column} = '{self.value}')."
