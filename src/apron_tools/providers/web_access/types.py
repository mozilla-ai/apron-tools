"""Pydantic models for web_access tool inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from apron_tools.types import ToolResult


class ResearchParams(BaseModel):
    """Parameters for a Tabstack research request."""

    query: str = Field(..., description="The research question or topic to investigate.")
    mode: Literal["fast", "balanced"] = Field(
        default="fast",
        description="Research mode: 'fast' for quick answers, 'balanced' for deeper multi-iteration research.",
    )


class ExtractJsonParams(BaseModel):
    """Parameters for a Tabstack extract_json request."""

    url: str = Field(..., description="The URL of the web page to extract data from.")
    json_schema: str = Field(
        ...,
        description=(
            "A JSON Schema string describing the structure of the data to extract. "
            'Example: \'{"type":"object","properties":{"title":{"type":"string"}}}\'.'
        ),
    )
    effort: Literal["min", "standard", "max"] = Field(
        default="standard",
        description=(
            "Fetch effort level. 'min' is fastest (1-5s, no fallback). 'standard' is "
            "balanced with enhanced reliability (3-15s, default). 'max' performs full "
            "browser rendering for JS-heavy sites (15-60s)."
        ),
    )


class ResearchResult(ToolResult):
    """Result of a Tabstack research request."""

    report: str = ""
    """The synthesised research report text (may include citations)."""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the research result."""
        if not self.success:
            return f"Error: {self.error}"
        return self.report or "No research results found."


class ExtractJsonResult(ToolResult):
    """Result of a Tabstack extract_json request."""

    data: str = ""
    """Extracted structured data serialised as a JSON string."""

    def __str__(self) -> str:
        """Return an LLM-readable summary of the extracted data."""
        if not self.success:
            return f"Error: {self.error}"
        return self.data or "{}"
