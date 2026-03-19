"""apron-tools: Agent-ready provider API wrappers.

Curated tool definitions with typed schemas, OAuth scope mappings,
and provider SDK wrappers for LLM function calling.
"""

from apron_tools.registry import discover_tools, get_tools_for_provider, get_tools_for_service
from apron_tools.tool import tool
from apron_tools.types import CapabilityGroup, FileFromBytes, FileFromUrl, FileInput, ToolDefinition, ToolResult

__all__ = [
    "CapabilityGroup",
    "FileFromBytes",
    "FileFromUrl",
    "FileInput",
    "ToolDefinition",
    "ToolResult",
    "discover_tools",
    "get_tools_for_provider",
    "get_tools_for_service",
    "tool",
]
