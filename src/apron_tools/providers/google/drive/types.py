"""Pydantic models for Google Drive API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

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


class MoveFilesParams(BaseModel):
    """Parameters for moving one or more files to a destination folder.

    ``file_ids`` accepts a comma-separated list of file IDs to support bulk
    operations. ``destination_folder_id`` is applied to every file.
    """

    file_ids: str
    destination_folder_id: str


class SearchParams(BaseModel):
    """Parameters for searching files in Google Drive."""

    query: str
    max_results: int = 20


class ShareFilesParams(BaseModel):
    """Parameters for sharing one or more files with another user.

    ``file_ids`` accepts a comma-separated list of file IDs to support bulk
    operations. ``email`` and ``role`` are applied to every file.
    """

    file_ids: str
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


class MoveFileItem(BaseModel):
    """Per-file outcome of a bulk Drive move call."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    file_id: str
    success: bool = True
    error: str | None = None
    name: str = ""
    parents: list[str] = []


class MoveFilesResult(ToolResult):
    """Result of moving one or more files in Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    destination_folder_id: str = ""
    items: list[MoveFileItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk move."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No files processed."
        lines: list[str] = []
        for item in self.items:
            if item.success:
                label = f"'{item.name}'" if item.name else item.file_id
                lines.append(f"- File {label} moved to folder {self.destination_folder_id}.")
            else:
                lines.append(f"- {item.file_id}: Failed: {item.error}")
        return "\n".join(lines)


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


class ShareFileItem(BaseModel):
    """Per-file outcome of a bulk Drive share call."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    file_id: str
    success: bool = True
    error: str | None = None
    permission_id: str = ""
    type: str = ""
    role: str = ""
    email_address: str = Field(default="", alias="emailAddress")
    display_name: str = Field(default="", alias="displayName")


class ShareFilesResult(ToolResult):
    """Result of sharing one or more files in Drive."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email: str = ""
    role: str = ""
    items: list[ShareFileItem] = []

    def __str__(self) -> str:
        """Return an LLM-readable summary of the bulk share."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.items:
            return "No files processed."
        lines: list[str] = []
        for item in self.items:
            if item.success:
                lines.append(f"- File {item.file_id} shared with {self.email} as {self.role}.")
            else:
                lines.append(f"- {item.file_id}: Failed: {item.error}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# google_drive_upload_file
# ---------------------------------------------------------------------------


class UploadFileParams(BaseModel):
    """Parameters for uploading a file to Google Drive."""

    file: FileInput
    """File to upload — either a URL to fetch or raw bytes."""

    name: str | None = None
    """Filename override. Uses the inferred filename if not provided."""

    folder_id: str | None = None
    """Optional parent folder ID. Uploads to root if not provided."""


class UploadFileResult(ToolResult):
    """Result of uploading a file to Google Drive."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    name: str = ""
    web_view_link: str = Field(default="", alias="webViewLink")
    mime_type: str = Field(default="", alias="mimeType")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the upload result."""
        if not self.success:
            return f"Error: {self.error}"
        return f"File uploaded: {self.name} (id={self.id})\nURL: {self.web_view_link}"


# ---------------------------------------------------------------------------
# google_drive_read_text_file
# ---------------------------------------------------------------------------


class ReadTextFileParams(BaseModel):
    """Parameters for reading a plain text file from Google Drive."""

    file_id: str
    """The Drive file ID to read."""


class ReadTextFileResult(ToolResult):
    """Result of reading a text file from Google Drive."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    content: str = ""

    def __str__(self) -> str:
        """Return the file content with the filename as a header."""
        if not self.success:
            return f"Error: {self.error}"
        body = self.content if self.content.strip() else "(File is empty)"
        return f"# {self.name}\n\n{body}"
