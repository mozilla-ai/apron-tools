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
    "linear_whoami": [LinearScope.READ],
    "linear_list_teams": [LinearScope.READ],
    "linear_list_users": [LinearScope.READ, LinearScope.ADMIN],
    "linear_list_issues": [LinearScope.READ],
    "linear_read_issue": [LinearScope.READ],
    "linear_create_issue": [LinearScope.WRITE],
    "linear_update_issue": [LinearScope.WRITE],
    "linear_list_projects": [LinearScope.READ],
    "linear_create_project": [LinearScope.WRITE],
    "linear_update_project": [LinearScope.WRITE],
    "linear_list_cycles": [LinearScope.READ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="linear",
    display_name="Linear",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
