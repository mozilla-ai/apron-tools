"""Capability-based scope definitions for Linear tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class LinearScope(Scope):
    """Capability scopes for Linear API access."""

    READ = (
        "read",
        "Read Access",
        "Read issues, projects, and workspace data",
        "read",
        False,
    )
    WRITE = (
        "write",
        "Write Access",
        "Modify issues, projects, and workspace data",
        "write",
        False,
    )
    ADMIN = (
        "admin",
        "Admin Access",
        "Read administrative workspace data such as user account details",
        "admin",
        False,
    )


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
    "linear_upload_file_to_issue": [LinearScope.WRITE],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="linear",
    display_name="Linear",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
