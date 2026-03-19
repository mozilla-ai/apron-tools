"""Capability-based scope definitions for Linear tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class LinearScope(StrEnum):
    """Capability scopes for Linear API access."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


SCOPES: dict[str, list[LinearScope]] = {
    "whoami": [LinearScope.READ],
    "list_teams": [LinearScope.READ],
    "list_users": [LinearScope.READ, LinearScope.ADMIN],
    "list_issues": [LinearScope.READ],
    "read_issue": [LinearScope.READ],
    "create_issue": [LinearScope.WRITE],
    "update_issue": [LinearScope.WRITE],
    "list_projects": [LinearScope.READ],
    "create_project": [LinearScope.WRITE],
    "update_project": [LinearScope.WRITE],
    "list_cycles": [LinearScope.READ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="linear",
    display_name="Linear",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
