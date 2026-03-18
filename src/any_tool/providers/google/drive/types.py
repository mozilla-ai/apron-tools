"""Pydantic models for Google Drive API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListFilesParams(BaseModel):
    """Parameters for listing files in Google Drive."""

    max_results: int = 20
    folder_id: str | None = None


class CreateFolderParams(BaseModel):
    """Parameters for creating a folder in Google Drive."""

    name: str
    parent_id: str | None = None


class GetFileInfoParams(BaseModel):
    """Parameters for getting metadata about a file."""

    file_id: str


class MoveFileParams(BaseModel):
    """Parameters for moving a file to a different folder."""

    file_id: str
    destination_folder_id: str


class SearchParams(BaseModel):
    """Parameters for searching files in Google Drive."""

    query: str
    max_results: int = 20


class ShareFileParams(BaseModel):
    """Parameters for sharing a file with another user."""

    file_id: str
    email: str
    role: str = "reader"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class FileOwner(BaseModel):
    """A file owner from the Drive API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="", alias="displayName")
    email_address: str = Field(default="", alias="emailAddress")


class DriveFile(BaseModel):
    """A file resource from the Drive API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    mime_type: str = Field(default="", alias="mimeType")
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")
    parents: list[str] = []
    web_view_link: str = Field(default="", alias="webViewLink")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListFilesResult(ToolResult):
    """Result of listing files from Drive."""

    model_config = ConfigDict(extra="ignore")

    files: list[DriveFile] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the files."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.files:
            return "No files found."
        lines = [f"Found {len(self.files)} file(s):"]
        for f in self.files:
            lines.append(f"  - {f.name} (id={f.id}, type={f.mime_type})")
        return "\n".join(lines)


class CreateFolderResult(ToolResult):
    """Result of creating a folder in Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    name: str = ""
    web_view_link: str = Field(default="", alias="webViewLink")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created folder."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Folder '{self.name}' created.\nID: {self.id}\nURL: {self.web_view_link}"


class GetFileInfoResult(ToolResult):
    """Result of getting file metadata from Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    name: str = ""
    mime_type: str = Field(default="", alias="mimeType")
    description: str = ""
    starred: bool = False
    trashed: bool = False
    parents: list[str] = []
    web_view_link: str = Field(default="", alias="webViewLink")
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")
    size: str = ""
    owners: list[FileOwner] = []
    shared: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the file info."""
        if not self.success:
            return f"Error: {self.error}"
        owner_str = ""
        if self.owners:
            owner_str = f"\nOwner: {self.owners[0].display_name} ({self.owners[0].email_address})"
        return f"File: {self.name}\nID: {self.id}\nType: {self.mime_type}\nURL: {self.web_view_link}{owner_str}"


class MoveFileResult(ToolResult):
    """Result of moving a file in Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    name: str = ""
    parents: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the move."""
        if not self.success:
            return f"Error: {self.error}"
        dest = self.parents[0] if self.parents else "unknown"
        return f"File '{self.name}' moved to folder {dest}."


class SearchResult(ToolResult):
    """Result of searching files in Drive."""

    model_config = ConfigDict(extra="ignore")

    files: list[DriveFile] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of search results."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.files:
            return "No files matched the search."
        lines = [f"Found {len(self.files)} result(s):"]
        for f in self.files:
            lines.append(f"  - {f.name} (id={f.id}, type={f.mime_type})")
        return "\n".join(lines)


class ShareFileResult(ToolResult):
    """Result of sharing a file in Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    type: str = ""
    role: str = ""
    email_address: str = Field(default="", alias="emailAddress")
    display_name: str = Field(default="", alias="displayName")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the sharing result."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Shared with {self.display_name} ({self.email_address}) as {self.role}."
