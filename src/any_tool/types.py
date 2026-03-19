"""Core types for any-tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


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
