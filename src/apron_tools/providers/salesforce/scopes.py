"""OAuth scope definitions for Salesforce tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class SalesforceScope(Scope):
    """OAuth scopes for Salesforce API access."""

    API = (
        "api",
        "API Access",
        "Access Salesforce REST APIs for data operations (REST, SOQL, SOSL)",
        "write",
        False,
    )
    # `full` grants access to all data the user can access — including
    # admin-level configuration. Reserve for tools that genuinely require
    # administrative scope.
    FULL = (
        "full",
        "Full Access",
        "Access all data the authenticated user can access, including administrative configuration",
        "admin",
        False,
    )
    REFRESH_TOKEN = (
        "refresh_token",
        "Refresh Token",
        "Obtain long-lived refresh tokens for persistent access",
        "read",
        False,
    )


SCOPES: dict[str, list[SalesforceScope]] = {
    "salesforce_explore_org": [SalesforceScope.API],
    "salesforce_query_records": [SalesforceScope.API],
    "salesforce_get_record": [SalesforceScope.API],
    "salesforce_create_record": [SalesforceScope.API],
    "salesforce_update_records": [SalesforceScope.API],
    "salesforce_search_records": [SalesforceScope.API],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="salesforce",
    display_name="Salesforce",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
