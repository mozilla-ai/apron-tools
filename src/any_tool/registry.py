"""Convention-based tool discovery across provider subpackages."""

from __future__ import annotations

import importlib
import pkgutil

import any_tool.providers as _providers_pkg
from any_tool.types import ToolDefinition


def discover_tools() -> list[ToolDefinition]:
    """Discover all registered tool definitions across providers.

    Scans ``any_tool.providers.*`` subpackages. For each subpackage,
    imports it and collects ``_tool_definition`` from all exported
    callables decorated with ``@tool``.
    """
    tools: list[ToolDefinition] = []
    for _importer, module_name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
        if not is_pkg:
            continue
        module = importlib.import_module(f"any_tool.providers.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, "_tool_definition"):
                tools.append(attr._tool_definition)
    return tools


def get_tools_for_provider(provider: str) -> list[ToolDefinition]:
    """Get all tools for an OAuth provider (e.g. 'google' returns Sheets + Gmail + Drive + ...).

    Args:
        provider: OAuth provider / company name to filter by.
    """
    return [td for td in discover_tools() if td.provider == provider]


def get_tools_for_service(service: str) -> list[ToolDefinition]:
    """Get tools for a specific service (e.g. 'google_sheets' returns just Sheets tools).

    Args:
        service: Service name to filter by.
    """
    return [td for td in discover_tools() if td.service == service]
