"""Pydantic models for Microsoft OneDrive tool inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListFilesParams(BaseModel):
    """Parameters for listing OneDrive files and folders."""

    folder_path: str = ""
    limit: int = 25


class SearchParams(BaseModel):
    """Parameters for searching OneDrive content."""

    query: str
    limit: int = 25


class GetFileInfoParams(BaseModel):
    """Parameters for retrieving metadata about a OneDrive item."""

    item_id: str


class CreateFolderParams(BaseModel):
    """Parameters for creating a new OneDrive folder."""

    folder_name: str
    parent_path: str = ""


class MoveFilesParams(BaseModel):
    """Parameters for moving one or more OneDrive items to a new folder."""

    item_ids: list[str]
    destination_folder_id: str
    new_name: str | None = None


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class DriveItemSummary(BaseModel):
    """A single OneDrive file or folder entry used in listing/search results."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    web_url: str = Field(default="", alias="webUrl")
    mime_type: str = ""
    is_folder: bool = False
    child_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _from_graph_item(cls, data: Any) -> Any:
        """Flatten Graph API driveItem facets into simple fields."""
        if not isinstance(data, dict):
            return data
        folder = data.get("folder")
        file_ = data.get("file")
        if folder is not None and "is_folder" not in data:
            data["is_folder"] = True
            data["child_count"] = folder.get("childCount", 0) if isinstance(folder, dict) else 0
        if isinstance(file_, dict) and "mime_type" not in data:
            data["mime_type"] = file_.get("mimeType", "")
        return data


class MoveFileOutcome(BaseModel):
    """Outcome of moving a single OneDrive item."""

    model_config = ConfigDict(extra="ignore")

    item_id: str
    success: bool
    name: str = ""
    web_url: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListFilesResult(ToolResult):
    """Result of listing OneDrive files and folders."""

    model_config = ConfigDict(extra="ignore")

    folder_path: str = ""
    items: list[DriveItemSummary] = []
    has_more: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Default success=True when constructed from raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable listing of the folder contents."""
        if not self.success:
            return f"Error: {self.error}"
        location = f"/{self.folder_path}" if self.folder_path else "(root)"
        if not self.items:
            return f"{location}: no files or folders found."
        lines = [f"{location}: {len(self.items)} item(s)"]
        for item in self.items:
            if item.is_folder:
                lines.append(f"  - [folder] {item.name} (id={item.id}, {item.child_count} items)")
            else:
                lines.append(f"  - {item.name} (id={item.id})")
        if self.has_more:
            lines.append("More items available; increase 'limit' to retrieve more.")
        return "\n".join(lines)


class SearchResult(ToolResult):
    """Result of searching OneDrive."""

    model_config = ConfigDict(extra="ignore")

    query: str = ""
    items: list[DriveItemSummary] = []
    has_more: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Default success=True when constructed from raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of search hits."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return f'No files found matching "{self.query}".'
        lines = [f'Results for "{self.query}": {len(self.items)} item(s)']
        for item in self.items:
            label = "[folder] " if item.is_folder else ""
            lines.append(f"  - {label}{item.name} (id={item.id})")
        if self.has_more:
            lines.append("More results available; refine the query or raise 'limit'.")
        return "\n".join(lines)


class FileInfo(BaseModel):
    """Detailed metadata for a OneDrive file returned by get_file_info."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    size: int = 0
    last_modified: str = Field(default="", alias="lastModifiedDateTime")
    web_url: str = Field(default="", alias="webUrl")
    download_url: str = Field(default="", alias="@microsoft.graph.downloadUrl")


class GetFileInfoResult(ToolResult):
    """Result of fetching OneDrive file metadata."""

    model_config = ConfigDict(extra="ignore")

    file: FileInfo | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Default success=True when constructed from raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the file metadata."""
        if not self.success:
            return f"Error: {self.error}"
        if self.file is None:
            return "No file metadata available."
        f = self.file
        lines = [
            f"File: {f.name}",
            f"  id: {f.id}",
            f"  size: {_format_size(f.size)}",
        ]
        if f.last_modified:
            lines.append(f"  last_modified: {f.last_modified}")
        if f.web_url:
            lines.append(f"  url: {f.web_url}")
        if f.download_url:
            lines.append(f"  download_url: {f.download_url}")
        return "\n".join(lines)


class CreateFolderResult(ToolResult):
    """Result of creating a OneDrive folder."""

    model_config = ConfigDict(extra="ignore")

    folder_id: str = ""
    name: str = ""
    web_url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Default success=True when constructed from raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of folder creation."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Created folder '{self.name}' (id={self.folder_id})"]
        if self.web_url:
            lines.append(f"URL: {self.web_url}")
        return "\n".join(lines)


class MoveFilesResult(ToolResult):
    """Result of moving one or more OneDrive items."""

    model_config = ConfigDict(extra="ignore")

    outcomes: list[MoveFileOutcome] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Default success=True when constructed from raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of per-item move outcomes."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.outcomes:
            return "No items were moved."
        lines = []
        for outcome in self.outcomes:
            if outcome.success:
                suffix = f" (url: {outcome.web_url})" if outcome.web_url else ""
                lines.append(f"  - Moved '{outcome.name or outcome.item_id}'{suffix}")
            else:
                lines.append(f"  - Failed '{outcome.item_id}': {outcome.error or 'unknown error'}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_size(size_bytes: int) -> str:
    """Format a byte count as a compact human-readable size string."""
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1_024:
        return f"{size_bytes / 1_024:.1f} KB"
    return f"{size_bytes} bytes"
