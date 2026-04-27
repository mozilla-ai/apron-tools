"""apron-tools: Agent-ready provider API wrappers.

Curated tool definitions with typed schemas, OAuth scope mappings,
and provider SDK wrappers for LLM function calling.
"""

from apron_tools.fileio import resolve_file_input
from apron_tools.registry import (
    discover_capability_groups,
    discover_tools,
    get_tools_for_provider,
    get_tools_for_service,
)
from apron_tools.tool import tool
from apron_tools.types import (
    AccessType,
    CapabilityGroup,
    FileFromBytes,
    FileFromUrl,
    FileInput,
    Scope,
    ScopeMetadata,
    ToolDefinition,
    ToolResult,
)

__all__ = [
    "AccessType",
    "CapabilityGroup",
    "FileFromBytes",
    "FileFromUrl",
    "FileInput",
    "Scope",
    "ScopeMetadata",
    "ToolDefinition",
    "ToolResult",
    "discover_capability_groups",
    "discover_tools",
    "get_tools_for_provider",
    "get_tools_for_service",
    "resolve_file_input",
    "tool",
]
