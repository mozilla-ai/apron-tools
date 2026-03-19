"""Pydantic models for Microsoft Excel (Graph API) inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListWorkbooksParams(BaseModel):
    """Parameters for listing Excel workbooks in OneDrive."""

    max_results: int = 20


class GetWorkbookInfoParams(BaseModel):
    """Parameters for retrieving workbook metadata and worksheets."""

    item_id: str


class ReadWorksheetParams(BaseModel):
    """Parameters for reading data from an Excel worksheet."""

    item_id: str
    worksheet_name: str = "Sheet1"
    range_address: str = ""


class UpdateWorksheetParams(BaseModel):
    """Parameters for updating data in an Excel worksheet."""

    item_id: str
    worksheet_name: str
    range_address: str
    values: list[list[Any]]


class AppendRowParams(BaseModel):
    """Parameters for appending rows to an Excel worksheet."""

    item_id: str
    worksheet_name: str
    values: list[list[Any]]


class CreateWorkbookParams(BaseModel):
    """Parameters for creating a new Excel workbook in OneDrive."""

    name: str
    folder_path: str = "root"


class AddWorksheetParams(BaseModel):
    """Parameters for adding a new worksheet to a workbook."""

    item_id: str
    name: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class DriveItem(BaseModel):
    """A OneDrive file item representing an Excel workbook."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    size: int = 0
    web_url: str = Field(default="", alias="webUrl")
    last_modified_date_time: str = Field(default="", alias="lastModifiedDateTime")
    created_date_time: str = Field(default="", alias="createdDateTime")


class WorksheetSummary(BaseModel):
    """Summary of a single worksheet within a workbook."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    position: int = 0
    name: str = "Sheet1"
    visibility: str = "Visible"


class RangeData(BaseModel):
    """Data from a worksheet range including address and cell values."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    address: str = ""
    cell_count: int = Field(default=0, alias="cellCount")
    column_count: int = Field(default=0, alias="columnCount")
    row_count: int = Field(default=0, alias="rowCount")
    values: list[list[Any]] = []


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListWorkbooksResult(ToolResult):
    """Result of listing Excel workbooks from OneDrive."""

    model_config = ConfigDict(extra="ignore")

    workbooks: list[DriveItem] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the workbooks."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.workbooks:
            return "No workbooks found."
        lines = [f"Found {len(self.workbooks)} workbook(s):"]
        for w in self.workbooks:
            lines.append(f"  - {w.name} (id={w.id})")
        return "\n".join(lines)


class GetWorkbookInfoResult(ToolResult):
    """Result of retrieving workbook metadata and worksheets."""

    model_config = ConfigDict(extra="ignore")

    item: DriveItem | None = None
    worksheets: list[WorksheetSummary] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the workbook info."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.item:
            return "No workbook info available."
        lines = [f"Workbook: {self.item.name} (id={self.item.id})"]
        if self.item.web_url:
            lines.append(f"URL: {self.item.web_url}")
        if self.item.last_modified_date_time:
            lines.append(f"Last modified: {self.item.last_modified_date_time}")
        if self.worksheets:
            lines.append(f"Worksheets ({len(self.worksheets)}):")
            for ws in self.worksheets:
                lines.append(f"  - {ws.name} (id={ws.id})")
        return "\n".join(lines)


class ReadWorksheetResult(ToolResult):
    """Result of reading data from an Excel worksheet."""

    model_config = ConfigDict(extra="ignore")

    range_data: RangeData | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the worksheet data."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.range_data or not self.range_data.values:
            return "No data in the requested range."
        rd = self.range_data
        return f"Range: {rd.address}\nData: {rd.row_count} row(s) x {rd.column_count} column(s)"


class UpdateWorksheetResult(ToolResult):
    """Result of updating data in an Excel worksheet."""

    model_config = ConfigDict(extra="ignore")

    range_data: RangeData | None = None

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
        if not self.range_data:
            return "Update completed."
        rd = self.range_data
        return f"Updated range '{rd.address}'.\nRows: {rd.row_count}, Columns: {rd.column_count}"


class AppendRowResult(ToolResult):
    """Result of appending rows to an Excel worksheet."""

    model_config = ConfigDict(extra="ignore")

    range_data: RangeData | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the append."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.range_data:
            return "Append completed."
        rd = self.range_data
        return f"Appended {rd.row_count} row(s) at '{rd.address}'."


class CreateWorkbookResult(ToolResult):
    """Result of creating a new Excel workbook."""

    model_config = ConfigDict(extra="ignore")

    item: DriveItem | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created workbook."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.item:
            return "Workbook created."
        lines = [f"Workbook '{self.item.name}' created."]
        lines.append(f"ID: {self.item.id}")
        if self.item.web_url:
            lines.append(f"URL: {self.item.web_url}")
        return "\n".join(lines)


class AddWorksheetResult(ToolResult):
    """Result of adding a new worksheet to a workbook."""

    model_config = ConfigDict(extra="ignore")

    worksheet: WorksheetSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the added worksheet."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.worksheet:
            return "Worksheet added."
        return f"Worksheet '{self.worksheet.name}' added (id={self.worksheet.id})."
