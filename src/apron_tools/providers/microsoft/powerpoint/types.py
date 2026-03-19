"""Pydantic models for Microsoft PowerPoint tool inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import FileInput, ToolResult

# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ExplorePresentationsParams(BaseModel):
    """Parameters for exploring OneDrive for PowerPoint files."""

    max_results: int = 20


class ReadPresentationParams(BaseModel):
    """Parameters for reading a presentation's slide content."""

    presentation_id: str
    include_notes: bool = False


class CreatePresentationParams(BaseModel):
    """Parameters for creating a new presentation."""

    name: str
    title: str = ""
    folder_path: str = "root"


class AddSlideParams(BaseModel):
    """Parameters for adding a slide to an existing presentation."""

    presentation_id: str
    layout: str = "blank"
    title: str = ""
    content: str = ""


class UpdateSlideTextParams(BaseModel):
    """Parameters for updating text on a specific slide."""

    presentation_id: str
    slide_number: int
    text: str
    shape_index: int = 0


class UploadToOnedriveParams(BaseModel):
    """Parameters for uploading a file to OneDrive."""

    file: FileInput
    folder_path: str = "root"
    name: str = ""


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class PresentationInfo(BaseModel):
    """Metadata for a single OneDrive presentation file."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    name: str = ""
    web_url: str = Field(default="", alias="webUrl")
    last_modified: str = Field(default="", alias="lastModifiedDateTime")
    size: int | None = None


class SlideInfo(BaseModel):
    """Structured text content of a single slide."""

    number: int
    title: str = ""
    texts: list[str] = []
    notes: str = ""


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ExplorePresentationsResult(ToolResult):
    """Result of exploring OneDrive for PowerPoint presentations."""

    model_config = ConfigDict(extra="ignore")

    presentations: list[PresentationInfo] = []
    method: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of found presentations."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.presentations:
            return "No PowerPoint presentations found."
        lines = [f"Found {len(self.presentations)} presentation(s):"]
        for p in self.presentations:
            parts = [f"  - {p.name} (id={p.id})"]
            if p.web_url:
                parts.append(f"    URL: {p.web_url}")
            if p.last_modified:
                parts.append(f"    Modified: {p.last_modified}")
            lines.extend(parts)
        return "\n".join(lines)


class ReadPresentationResult(ToolResult):
    """Result of reading a presentation's slide content."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
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
        lines = [f"{self.name} ({len(self.slides)} slides)"]
        for s in self.slides:
            header = f"  Slide {s.number}"
            if s.title:
                header += f": {s.title}"
            lines.append(header)
            for t in s.texts:
                lines.append(f"    - {t}")
            if s.notes:
                lines.append(f"    Notes: {s.notes}")
        return "\n".join(lines)


class CreatePresentationResult(ToolResult):
    """Result of creating a new presentation."""

    model_config = ConfigDict(extra="ignore")

    presentation_id: str = ""
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
        """Return an LLM-readable confirmation of the created presentation."""
        if not self.success:
            return f"Error: {self.error}"
        lines = [f"Created '{self.name}' (id={self.presentation_id})"]
        if self.web_url:
            lines.append(f"URL: {self.web_url}")
        return "\n".join(lines)


class AddSlideResult(ToolResult):
    """Result of adding a slide to a presentation."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    layout: str = ""
    slide_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the added slide."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Added slide to '{self.name}' (layout={self.layout}, total={self.slide_count})"


class UpdateSlideTextResult(ToolResult):
    """Result of updating text on a slide."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    slide_number: int = 0
    shape_name: str = ""

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable confirmation of the text update."""
        if not self.success:
            return f"Error: {self.error}"
        return f"Updated slide {self.slide_number} in '{self.name}' (shape={self.shape_name})"


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
