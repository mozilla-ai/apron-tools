"""any-tool: Agent-ready provider API wrappers.

Curated tool definitions with typed schemas, OAuth scope mappings,
and provider SDK wrappers for LLM function calling.
"""

from any_tool.registry import discover_tools, get_tools_for_provider
from any_tool.tool import tool
from any_tool.types import CapabilityGroup, ToolDefinition, ToolResult

__all__ = [
    "CapabilityGroup",
    "ToolDefinition",
    "ToolResult",
    "discover_tools",
    "get_tools_for_provider",
    "tool",
]
