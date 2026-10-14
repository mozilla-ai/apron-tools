"""Pydantic models for Microsoft Word tool inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apron_tools._ooxml import validate_xml_text
from apron_tools.types import FileInput, ToolResult


def _validate_paragraph_text(text: str) -> str:
    """Check that each line of the text holds only characters that a document can store.

    Each line becomes a paragraph, so the characters that separate lines are not stored.

    Args:
        text: Text whose lines become paragraphs.

    Returns:
        The text, unchanged.

    Raises:
        ValueError: If a line holds a character that a document cannot store.
    """
    for line in text.splitlines():
        validate_xml_text(line)
    return text


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExploreDocumentsParams(BaseModel):
    """Parameters for exploring OneDrive for Word files."""

    max_results: int = 20


class ReadDocumentParams(BaseModel):
    """Parameters for reading a document's text content."""

    document_id: str


class CreateDocumentParams(BaseModel):
    """Parameters for creating a new document."""

    name: str
    content: str = ""
    folder_path: str = "root"

    _validate_content = field_validator("content")(_validate_paragraph_text)


class UpdateDocumentParams(BaseModel):
    """Parameters for appending content to an existing document."""

    document_id: str
    content: str

    _validate_content = field_validator("content")(_validate_paragraph_text)


class UploadToOnedriveParams(BaseModel):
    """Parameters for uploading a file to OneDrive."""

    file: FileInput
    folder_path: str = "root"
    name: str = ""


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class DocumentInfo(BaseModel):
    """Metadata for a single OneDrive Word document file."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    web_url: str = Field(default="", alias="webUrl")
    last_modified: str = Field(default="", alias="lastModifiedDateTime")
    size: int | None = None


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExploreDocumentsResult(ToolResult):
    """Result of exploring OneDrive for Word documents."""

    model_config = ConfigDict(extra="ignore")

    documents: list[DocumentInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of found documents."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.documents:
            return "No Word documents found."
        lines = [f"Found {len(self.documents)} document(s):"]
        for d in self.documents:
            parts = [f"  - {d.name} (id={d.id})"]
            if d.web_url:
                parts.append(f"    URL: {d.web_url}")
            if d.last_modified:
                parts.append(f"    Modified: {d.last_modified}")
            lines.extend(parts)
        return "\n".join(lines)


class ReadDocumentResult(ToolResult):
    """Result of reading a document's text content."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    paragraphs: list[str] = []
    tables: list[list[list[str]]] = []
    truncated: bool = False

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the document content."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"{self.name} ({len(self.paragraphs)} paragraphs)"]
        for p in self.paragraphs:
            lines.append(f"  {p}")
        for i, table in enumerate(self.tables):
            lines.append(f"  Table {i + 1}:")
            for row in table:
                lines.append(f"    | {' | '.join(row)} |")
        if self.truncated:
            lines.append("  Note: The text was truncated because the document is over the length limit.")
        return "\n".join(lines)


class CreateDocumentResult(ToolResult):
    """Result of creating a new document."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = ""
    name: str = ""
    web_url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the created document."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Created '{self.name}' (id={self.document_id})"]
        if self.web_url:
            lines.append(f"URL: {self.web_url}")
        return "\n".join(lines)


class UpdateDocumentResult(ToolResult):
    """Result of updating a document's content."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Updated '{self.name}'"


class UploadToOnedriveResult(ToolResult):
    """Result of uploading a file to OneDrive."""

    model_config = ConfigDict(extra="ignore")

    file_id: str = ""
    name: str = ""
    web_url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the upload."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Uploaded '{self.name}' to OneDrive (id={self.file_id})"]
        if self.web_url:
            lines.append(f"URL: {self.web_url}")
        return "\n".join(lines)
