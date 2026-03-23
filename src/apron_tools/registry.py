"""Convention-based tool and capability-group discovery across provider subpackages."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Sequence

import apron_tools.providers as _providers_pkg
from apron_tools.types import CapabilityGroup, ToolDefinition

_log = logging.getLogger(__name__)


def _collect_tools(package_path: str, package_fs_path: Sequence[str]) -> list[ToolDefinition]:
    """Collect tool definitions from a provider package.

    Handles both flat providers (tools.py at package root) and hierarchical
    providers (tools.py inside sub-service packages). Catches ModuleNotFoundError
    for optional dependencies (e.g. powerpoint, word) while letting internal
    import errors propagate.
    """
    tools: list[ToolDefinition] = []

    has_tools_module = any(
        name == "tools" and not is_pkg for _imp, name, is_pkg in pkgutil.iter_modules(package_fs_path)
    )

    if has_tools_module:
        try:
            module = importlib.import_module(f"{package_path}.tools")
        except ModuleNotFoundError:
            _log.debug("Skipping %s.tools — optional dependency not installed.", package_path)
            return tools
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, "_tool_definition"):
                tools.append(attr._tool_definition)
        return tools

    for _imp, sub_name, is_pkg in pkgutil.iter_modules(package_fs_path):
        if not is_pkg:
            continue
        sub_path = f"{package_path}.{sub_name}"
        sub_pkg = importlib.import_module(sub_path)
        tools.extend(_collect_tools(sub_path, sub_pkg.__path__))

    return tools


def _collect_capability_groups(
    package_path: str,
    package_fs_path: Sequence[str],
) -> list[CapabilityGroup]:
    """Collect capability groups from a provider package.

    Handles both flat providers (scopes.py at package root) and hierarchical
    providers (scopes.py inside sub-service packages).
    """
    groups: list[CapabilityGroup] = []

    has_scopes_module = any(
        name == "scopes" and not is_pkg for _imp, name, is_pkg in pkgutil.iter_modules(package_fs_path)
    )

    if has_scopes_module:
        module = importlib.import_module(f"{package_path}.scopes")
        cg = getattr(module, "CAPABILITY_GROUP", None)
        if isinstance(cg, CapabilityGroup):
            groups.append(cg)
        return groups

    for _imp, sub_name, is_pkg in pkgutil.iter_modules(package_fs_path):
        if not is_pkg:
            continue
        sub_path = f"{package_path}.{sub_name}"
        sub_pkg = importlib.import_module(sub_path)
        groups.extend(_collect_capability_groups(sub_path, sub_pkg.__path__))

    return groups


def discover_capability_groups() -> list[CapabilityGroup]:
    """Discover all capability groups across providers.

    Scans ``apron_tools.providers.*`` subpackages and collects
    ``CAPABILITY_GROUP`` from each provider's ``scopes`` module.
    This is lightweight — it only loads scope definitions, never
    tool implementations or their SDK dependencies.
    """
    groups: list[CapabilityGroup] = []
    for _imp, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
        if not is_pkg:
            continue
        pkg = importlib.import_module(f"apron_tools.providers.{name}")
        groups.extend(
            _collect_capability_groups(f"apron_tools.providers.{name}", pkg.__path__),
        )
    return groups


def discover_tools() -> list[ToolDefinition]:
    """Discover all registered tool definitions across providers.

    Scans ``apron_tools.providers.*`` subpackages. For each subpackage,
    imports its ``tools`` module (flat providers) or recurses into
    sub-service packages (hierarchical providers) and collects
    ``_tool_definition`` from all callables decorated with ``@tool``.
    """
    tools: list[ToolDefinition] = []
    for _imp, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
        if not is_pkg:
            continue
        pkg = importlib.import_module(f"apron_tools.providers.{name}")
        tools.extend(_collect_tools(f"apron_tools.providers.{name}", pkg.__path__))
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
