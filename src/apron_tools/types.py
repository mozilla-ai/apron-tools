"""Core types for apron-tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import Base64Bytes, BaseModel, Field, HttpUrl


class ToolResult(BaseModel):
    """Base for all tool outputs.

    Subclasses define provider-specific fields and implement ``__str__``
    for LLM-readable output. Consumers choose their access level:

    - ``str(result)`` for text (what the LLM reads).
    - ``result.field`` for typed attribute access.
    - ``result.model_dump()`` for dict.
    - ``result.model_dump_json()`` for JSON.
    """

    success: bool
    error: str | None = None

    def __str__(self) -> str:
        """Return a human/LLM-readable string representation."""
        raise NotImplementedError("Subclasses must implement __str__.")


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata for a single tool, used by any-identity's registry."""

    name: str
    """Tool name, e.g. ``typeform_list_forms``."""

    provider: str
    """OAuth provider / company, e.g. ``google``, ``atlassian``, ``slack``."""

    service: str
    """Specific product, e.g. ``google_sheets``, ``atlassian_jira``, ``slack``."""

    integration: str
    """Same as service. Kept for Octonous compatibility."""

    description: str
    """Human-readable description of what the tool does."""

    input_schema: dict[str, Any]
    """JSON Schema for the tool's input parameters."""

    output_schema: dict[str, Any]
    """JSON Schema for the tool's output."""

    scopes: list[str]
    """OAuth scopes required to call this tool."""

    api_docs_url: str
    """URL to the provider's API documentation for this endpoint."""


@dataclass(frozen=True)
class CapabilityGroup:
    """Provider-level metadata for the tool registry.

    Represents an integration that can be connected via OAuth,
    with the aggregate scopes required across all its tools.
    """

    provider: str
    """Provider identifier, e.g. ``typeform``."""

    display_name: str
    """Human-readable name, e.g. ``Typeform``."""

    scopes: list[str]
    """Union of all OAuth scopes required by this provider's tools."""


# ---------------------------------------------------------------------------
# File input types for upload tools
# ---------------------------------------------------------------------------


class FileFromBytes(BaseModel):
    """File provided as raw bytes.

    For programmatic callers that already have file data in memory.
    Data is base64-encoded when serialised to JSON, ensuring binary
    content round-trips safely across language boundaries.
    """

    type: Literal["bytes"] = "bytes"
    data: Base64Bytes
    """File content. Accepts base64 strings (JSON callers) or raw bytes (Python callers)."""

    filename: str
    """Filename for the uploaded file."""

    mime_type: str
    """MIME type of the file content."""


class FileFromUrl(BaseModel):
    """File to be fetched from a URL.

    The tool function downloads the file before uploading to the provider.
    Filename and MIME type are inferred from the HTTP response when not provided.
    """

    type: Literal["url"] = "url"
    url: HttpUrl
    """HTTP(S) URL to fetch the file from."""

    filename: str | None = None
    """Override filename. Inferred from the URL or Content-Disposition header if not provided."""

    mime_type: str | None = None
    """Override MIME type. Inferred from the Content-Type header if not provided."""


FileInput = Annotated[
    FileFromBytes | FileFromUrl,
    Field(discriminator="type"),
]
"""File input for upload tools.

A discriminated union: provide either a URL to fetch from or raw bytes.
LLM callers typically use ``FileFromUrl``; programmatic callers may use either.
"""
