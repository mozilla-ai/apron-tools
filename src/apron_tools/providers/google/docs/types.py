"""Pydantic models for Google Docs API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

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


class InsertImageParams(BaseModel):
    """Parameters for inserting an image into a Google Doc.

    Width and height are in points and control the rendered size. If the
    aspect ratio does not match the source image, the image will be stretched.
    """

    document_id: str
    file: FileInput
    location_index: int = Field(default=1, ge=1)
    width_pt: float = Field(default=300, gt=0)
    height_pt: float = Field(default=200, gt=0)


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


class InsertImageResult(ToolResult):
    """Result of inserting an image into a Google Doc."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = ""
    filename: str = ""
    drive_file_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the inserted image."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/document/d/{self.document_id}/edit"
        return f"Image '{self.filename}' inserted into document.\nDocument URL: {url}"


# ---------------------------------------------------------------------------
# google_docs_update_table_cell
# ---------------------------------------------------------------------------


class UpdateTableCellParams(BaseModel):
    """Parameters for updating a single cell of a native Google Docs table.

    Tables are addressed by their order of appearance in the document body:
    ``table_index=0`` is the first table, ``table_index=1`` the second.
    Nested tables (a table inside another table's cell) are not addressable
    through this tool.
    """

    document_id: str
    table_index: int = Field(ge=0)
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    text: str = ""


class UpdateTableCellResult(ToolResult):
    """Result of updating a single table cell."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = ""
    title: str = ""
    table_index: int = 0
    row: int = 0
    column: int = 0

    def __str__(self) -> str:
        """Return an LLM-readable summary of the cell update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Updated cell (row: {self.row}, column: {self.column}) in table {self.table_index} of '{self.title}'."


# ---------------------------------------------------------------------------
# google_docs_read_comments
# ---------------------------------------------------------------------------


class ReadCommentsParams(BaseModel):
    """Parameters for listing comments on a Google Docs document.

    ``max_results`` is clamped to the Drive Comments API's inclusive range
    of [1, 100]. ``include_resolved`` defaults to False so the LLM sees
    only open, actionable comments by default.
    """

    document_id: str
    max_results: int = 20
    include_resolved: bool = False


class CommentAuthor(BaseModel):
    """Author of a comment or reply as returned by the Drive Comments API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    display_name: str = Field(default="Unknown", alias="displayName")


class CommentReply(BaseModel):
    """A reply to a comment thread."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    content: str = ""
    author: CommentAuthor = Field(default_factory=CommentAuthor)
    created_time: str = Field(default="", alias="createdTime")


class QuotedFileContent(BaseModel):
    """Snippet of document content that a comment is anchored to."""

    model_config = ConfigDict(extra="ignore")

    value: str = ""
    mime_type: str = Field(default="", alias="mimeType")


class Comment(BaseModel):
    """A comment on a Google Docs document, returned by the Drive Comments API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    content: str = ""
    resolved: bool = False
    author: CommentAuthor = Field(default_factory=CommentAuthor)
    created_time: str = Field(default="", alias="createdTime")
    quoted_file_content: QuotedFileContent | None = Field(default=None, alias="quotedFileContent")
    replies: list[CommentReply] = []


class ReadCommentsResult(ToolResult):
    """Result of listing comments on a document."""

    model_config = ConfigDict(extra="ignore")

    document_id: str = ""
    title: str = ""
    comments: list[Comment] = []
    include_resolved: bool = False
    has_more: bool = False

    def __str__(self) -> str:
        """Return a Markdown-formatted list of comments for the LLM."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.comments:
            status = "open " if not self.include_resolved else ""
            return f'No {status}comments found on document "{self.title}".'

        lines: list[str] = [f'## Comments on "{self.title}" ({len(self.comments)} comment(s))\n']
        for i, comment in enumerate(self.comments, 1):
            lines.append("---")
            status_tag = " [RESOLVED]" if comment.resolved else ""
            lines.append(
                f"**Comment #{i}** (id: {comment.id}) by "
                f"{comment.author.display_name} ({comment.created_time}){status_tag}"
            )
            if comment.quoted_file_content and comment.quoted_file_content.value:
                lines.append(f"> {comment.quoted_file_content.value}")
            lines.append(comment.content)
            for reply in comment.replies:
                lines.append(f"\n  **Reply** by {reply.author.display_name} ({reply.created_time})")
                lines.append(f"  {reply.content}")
            lines.append("")

        if self.has_more:
            lines.append(f"*Showing first {len(self.comments)} comments. More comments exist on this document.*")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# google_docs_create_comment
# ---------------------------------------------------------------------------


class CreateCommentParams(BaseModel):
    """Parameters for creating a new comment on a Google Docs document.

    If ``quoted_text`` is provided, the new comment is anchored to that
    text within the document body. When omitted, the comment is a
    standalone top-level comment with no anchor.
    """

    document_id: str
    comment: str
    quoted_text: str = ""


class CreateCommentResult(ToolResult):
    """Result of creating a comment."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    content: str = ""
    author: CommentAuthor = Field(default_factory=CommentAuthor)
    created_time: str = Field(default="", alias="createdTime")
    quoted_file_content: QuotedFileContent | None = Field(default=None, alias="quotedFileContent")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created comment."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [
            "Comment created successfully.",
            f"- **ID:** {self.id}",
            f"- **Author:** {self.author.display_name}",
            f"- **Created:** {self.created_time}",
        ]
        if self.quoted_file_content and self.quoted_file_content.value:
            lines.append(f"- **Anchored to:** {self.quoted_file_content.value}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# google_docs_reply_to_comment
# ---------------------------------------------------------------------------


class ReplyToCommentParams(BaseModel):
    """Parameters for replying to an existing comment thread."""

    document_id: str
    comment_id: str
    reply: str


class ReplyToCommentResult(ToolResult):
    """Result of adding a reply to a comment."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    content: str = ""
    author: CommentAuthor = Field(default_factory=CommentAuthor)
    created_time: str = Field(default="", alias="createdTime")

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the reply."""
        if not self.success:
            return f"Error: {self.error}"
        return (
            "Reply added successfully.\n"
            f"- **ID:** {self.id}\n"
            f"- **Author:** {self.author.display_name}\n"
            f"- **Created:** {self.created_time}"
        )
