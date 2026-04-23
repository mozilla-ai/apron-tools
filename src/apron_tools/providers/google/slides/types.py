"""Pydantic models for Google Slides API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListPresentationsParams(BaseModel):
    """Parameters for listing Google Slides presentations."""

    max_results: int = 20


class CreatePresentationParams(BaseModel):
    """Parameters for creating a new presentation."""

    title: str


class CopyPresentationParams(BaseModel):
    """Parameters for copying an existing presentation."""

    presentation_id: str
    new_title: str


class ReadPresentationParams(BaseModel):
    """Parameters for reading presentation content."""

    presentation_id: str
    include_speaker_notes: bool = False


class AddSlideParams(BaseModel):
    """Parameters for adding a slide to a presentation."""

    presentation_id: str
    layout: str = "BLANK"
    insertion_index: int | None = None


class UpdateSlideTextParams(BaseModel):
    """Parameters for updating text in a slide."""

    presentation_id: str
    slide_id: str
    text: str
    shape_id: str | None = None


class DuplicateSlideParams(BaseModel):
    """Parameters for duplicating a slide."""

    presentation_id: str
    slide_id: str
    insertion_index: int | None = None


class InsertElementParams(BaseModel):
    """Parameters for inserting an element into a slide."""

    presentation_id: str
    slide_id: str
    shape_type: str = "TEXT_BOX"
    text: str = ""
    x: float = 100
    y: float = 100
    width: float = 400
    height: float = 300


class UpdateTableCellParams(BaseModel):
    """Parameters for updating text in a table cell."""

    presentation_id: str
    table_id: str
    row: int
    column: int
    text: str


class InsertImageParams(BaseModel):
    """Parameters for inserting an image onto a slide.

    Width and height are in points and control the rendered size. If the
    aspect ratio does not match the source image, the image will be stretched.
    """

    presentation_id: str
    slide_id: str
    file: FileInput
    x: float = 100
    y: float = 100
    width: float = Field(default=300, gt=0)
    height: float = Field(default=200, gt=0)


class FormatTextParams(BaseModel):
    """Parameters for formatting text in a shape or text box."""

    presentation_id: str
    object_id: str
    bold: bool | None = None
    italic: bool | None = None
    font_size: int | None = None
    foreground_color: str | None = None
    start_index: int | None = None
    end_index: int | None = None


class DeleteShapeParams(BaseModel):
    """Parameters for deleting a shape or page element from a slide."""

    presentation_id: str
    slide_id: str
    shape_id: str


class DeleteSlideParams(BaseModel):
    """Parameters for deleting a slide from a presentation."""

    presentation_id: str
    slide_id: str


class UpdateSlideBackgroundParams(BaseModel):
    """Parameters for updating a slide's background fill.

    Exactly one of ``background_color`` or ``theme_color`` must be supplied.
    ``background_color`` is a ``#RRGGBB`` hex string. ``theme_color`` is a
    Slides API ``ThemeColorType`` value (e.g. ``DARK1``, ``ACCENT1``).
    """

    presentation_id: str
    slide_id: str
    background_color: str | None = None
    theme_color: str | None = None

    @model_validator(mode="after")
    def _require_exactly_one_color(self) -> UpdateSlideBackgroundParams:
        """Enforce that exactly one color source is provided."""
        if bool(self.background_color) == bool(self.theme_color):
            raise ValueError("Provide exactly one of background_color or theme_color when updating a slide background.")
        return self


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class PresentationFile(BaseModel):
    """A presentation file from the Drive API listing."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = "Untitled"
    created_time: str | None = Field(default=None, alias="createdTime")
    modified_time: str | None = Field(default=None, alias="modifiedTime")


class SlideInfo(BaseModel):
    """Summary of a single slide within a presentation."""

    model_config = ConfigDict(extra="ignore")

    object_id: str = ""
    index: int = 0
    text_content: list[str] = []


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListPresentationsResult(ToolResult):
    """Result of listing presentations from Drive."""

    model_config = ConfigDict(extra="ignore")

    files: list[PresentationFile] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the presentations."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.files:
            return "No presentations found."
        lines = [f"Found {len(self.files)} presentation(s):"]
        for f in self.files:
            lines.append(f"  - {f.name} (id={f.id})")
        return "\n".join(lines)


class CreatePresentationResult(ToolResult):
    """Result of creating a new presentation."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    title: str = ""
    slide_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            data["title"] = data.get("title", "")
            data["slide_count"] = len(data.get("slides", []))
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created presentation."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/presentation/d/{self.presentation_id}/edit"
        return (
            f"Presentation '{self.title}' created.\nID: {self.presentation_id}\nURL: {url}\nSlides: {self.slide_count}"
        )


class CopyPresentationResult(ToolResult):
    """Result of copying a presentation."""

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
        """Return an LLM-readable summary of the copied presentation."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/presentation/d/{self.id}/edit"
        return f"Presentation copied.\nOriginal: '{self.original_name}'\nCopy: '{self.name}'\nID: {self.id}\nURL: {url}"


class ReadPresentationResult(ToolResult):
    """Result of reading a presentation."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    slide_count: int = 0
    slides: list[SlideInfo] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the presentation content."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Presentation: {self.title}", f"Total slides: {self.slide_count}"]
        for s in self.slides:
            lines.append(f"  Slide {s.index + 1} (id={s.object_id})")
            for text in s.text_content:
                lines.append(f"    - {text}")
        return "\n".join(lines)


class AddSlideResult(ToolResult):
    """Result of adding a slide to a presentation.

    Attributes:
        fallback_reason: Populated when the requested layout could not be
            resolved to a layout object on the presentation and the tool fell
            back to the Slides API's predefined layout enum. ``None`` when the
            requested layout matched a layout object on the presentation, and
            also for the intentional ``BLANK`` predefined-layout fallback
            (``BLANK`` is always available, so the silent fallback carries no
            caller-actionable signal).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    slide_id: str = ""
    fallback_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            replies = data.get("replies", [])
            if replies:
                data["slide_id"] = replies[0].get("createSlide", {}).get("objectId", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the added slide."""
        if not self.success:
            return f"Error: {self.error}"
        summary = f"Slide added (id={self.slide_id})."
        if self.fallback_reason:
            summary += f" Layout fallback: {self.fallback_reason}"
        return summary


class UpdateSlideTextResult(ToolResult):
    """Result of updating text in a slide.

    Attributes:
        fallback_reason: Populated when the caller-supplied ``shape_id`` was
            not found on the slide and the tool created a new text box
            instead. ``None`` when the shape existed (or was never requested).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    shape_id: str = ""
    fallback_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the text update."""
        if not self.success:
            return f"Error: {self.error}"
        summary = f"Text updated in shape {self.shape_id}."
        if self.fallback_reason:
            summary += f" {self.fallback_reason}"
        return summary


class DuplicateSlideResult(ToolResult):
    """Result of duplicating a slide."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    new_slide_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
            replies = data.get("replies", [])
            if replies:
                data["new_slide_id"] = replies[0].get("duplicateObject", {}).get("objectId", "")
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the duplicated slide."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Slide duplicated (new id={self.new_slide_id})."


class InsertElementResult(ToolResult):
    """Result of inserting an element into a slide."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    element_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the inserted element."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Element inserted (id={self.element_id})."


class UpdateTableCellResult(ToolResult):
    """Result of updating a table cell."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    table_id: str = ""
    row: int = 0
    column: int = 0

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the table cell update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Cell (row={self.row}, col={self.column}) updated in table {self.table_id}."


class FormatTextResult(ToolResult):
    """Result of formatting text."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    presentation_id: str = Field(default="", alias="presentationId")
    object_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the text formatting."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Text formatted in object {self.object_id}."


class InsertImageResult(ToolResult):
    """Result of inserting an image onto a slide."""

    model_config = ConfigDict(extra="ignore")

    presentation_id: str = ""
    image_id: str = ""
    filename: str = ""
    drive_file_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the inserted image."""
        if not self.success:
            return f"Error: {self.error}"
        url = f"https://docs.google.com/presentation/d/{self.presentation_id}/edit"
        return f"Image '{self.filename}' inserted (id={self.image_id}).\nPresentation URL: {url}"


class DeleteShapeResult(ToolResult):
    """Result of deleting a shape from a slide."""

    model_config = ConfigDict(extra="ignore")

    presentation_id: str = ""
    slide_id: str = ""
    shape_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the shape deletion."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Shape {self.shape_id} deleted from slide {self.slide_id}."


class DeleteSlideResult(ToolResult):
    """Result of deleting a slide from a presentation."""

    model_config = ConfigDict(extra="ignore")

    presentation_id: str = ""
    slide_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the slide deletion."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Slide {self.slide_id} deleted."


class UpdateSlideBackgroundResult(ToolResult):
    """Result of updating a slide's background fill."""

    model_config = ConfigDict(extra="ignore")

    presentation_id: str = ""
    slide_id: str = ""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the background update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Background updated for slide {self.slide_id}."
