"""Pydantic models for Google Docs API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from any_tool.types import ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListDocumentsParams(BaseModel):
    """Parameters for listing Google Docs documents."""

    max_results: int = 20


class CreateDocumentParams(BaseModel):
    """Parameters for creating a new document."""

    title: str
    content: str = ""


class ReadDocumentParams(BaseModel):
    """Parameters for reading a document."""

    document_id: str
    include_metadata: bool = False


class UpdateDocumentParams(BaseModel):
    """Parameters for updating a document via batchUpdate."""

    document_id: str
    requests: list[dict[str, Any]]


class CopyDocumentParams(BaseModel):
    """Parameters for copying an existing document."""

    document_id: str
    new_title: str


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class DocumentFile(BaseModel):
    """A document file from the Drive API listing."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")


class TextRun(BaseModel):
    """A run of text within a paragraph element."""

    model_config = ConfigDict(extra="ignore")

    content: str = ""
    text_style: dict[str, Any] = Field(default_factory=dict, alias="textStyle")


class ParagraphElement(BaseModel):
    """An element within a paragraph."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    start_index: int = Field(default=0, alias="startIndex")
    end_index: int = Field(default=0, alias="endIndex")
    text_run: TextRun | None = Field(default=None, alias="textRun")


class ParagraphStyle(BaseModel):
    """Style applied to a paragraph."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    named_style_type: str = Field(default="NORMAL_TEXT", alias="namedStyleType")


class Paragraph(BaseModel):
    """A paragraph within the document body."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    elements: list[ParagraphElement] = []
    paragraph_style: ParagraphStyle = Field(default_factory=ParagraphStyle, alias="paragraphStyle")


class StructuralElement(BaseModel):
    """A structural element in the document body content array."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    start_index: int = Field(default=0, alias="startIndex")
    end_index: int = Field(default=0, alias="endIndex")
    paragraph: Paragraph | None = None
    section_break: dict[str, Any] | None = Field(default=None, alias="sectionBreak")


class Body(BaseModel):
    """The document body containing structural elements."""

    model_config = ConfigDict(extra="ignore")

    content: list[StructuralElement] = []


class WriteControl(BaseModel):
    """Write control metadata from a batchUpdate response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    required_revision_id: str = Field(default="", alias="requiredRevisionId")


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListDocumentsResult(ToolResult):
    """Result of listing documents from Drive."""

    model_config = ConfigDict(extra="ignore")

    files: list[DocumentFile] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the documents."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.files:
            return "No documents found."
        lines = [f"Found {len(self.files)} document(s):"]
        for f in self.files:
            lines.append(f"  - {f.name} (id={f.id})")
        return "\n".join(lines)


class CreateDocumentResult(ToolResult):
    """Result of creating a new document."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_id: str = Field(default="", alias="documentId")
    title: str = ""
    revision_id: str = Field(default="", alias="revisionId")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created document."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/document/d/{self.document_id}/edit"
        return f"Document '{self.title}' created.\nID: {self.document_id}\nURL: {url}"


class ReadDocumentResult(ToolResult):
    """Result of reading a document."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_id: str = Field(default="", alias="documentId")
    title: str = ""
    body: Body = Body()
    revision_id: str = Field(default="", alias="revisionId")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    @property
    def text_content(self) -> str:
        """Extract plain text from the document body."""
        parts: list[str] = []
        for element in self.body.content:
            if element.paragraph is not None:
                for pe in element.paragraph.elements:
                    if pe.text_run is not None:
                        parts.append(pe.text_run.content)
        return "".join(parts)

    def __str__(self) -> str:
        """Return an LLM-readable summary of the document."""
        if not self.success:
            return f"Error: {self.error}"
        text = self.text_content.strip()
        if not text:
            return f"Document '{self.title}' is empty."
        preview = text[:200] + "..." if len(text) > 200 else text
        return f"Document '{self.title}' ({len(text)} chars):\n{preview}"


class UpdateDocumentResult(ToolResult):
    """Result of a batchUpdate on a document."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    document_id: str = Field(default="", alias="documentId")
    replies: list[dict[str, Any]] = []
    write_control: WriteControl = Field(default_factory=WriteControl, alias="writeControl")

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
            f"Document '{self.document_id}' updated.\n"
            f"Replies: {len(self.replies)}\n"
            f"Revision: {self.write_control.required_revision_id}"
        )


class CopyDocumentResult(ToolResult):
    """Result of copying a document."""

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
        """Return an LLM-readable summary of the copied document."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/document/d/{self.id}/edit"
        return f"Document copied.\nOriginal: '{self.original_name}'\nCopy: '{self.name}'\nID: {self.id}\nURL: {url}"


# ---------------------------------------------------------------------------
# google_docs_replace_text
# ---------------------------------------------------------------------------


class ReplaceTextParams(BaseModel):
    """Parameters for finding and replacing text in a Google Doc."""

    document_id: str
    find_text: str
    replace_text: str
    match_case: bool = True


class ReplaceTextResult(ToolResult):
    """Result of a find-and-replace operation."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = ""
    title: str = ""
    occurrences_changed: int = 0

    def __str__(self) -> str:
        """Return an LLM-readable summary."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Replaced {self.occurrences_changed} occurrence(s) in document '{self.title}'."
