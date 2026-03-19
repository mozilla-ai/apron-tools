"""OAuth scope definitions for Salesforce tools."""

from __future__ import annotations

from enum import StrEnum

from apron_tools.types import CapabilityGroup


class SalesforceScope(StrEnum):
    """OAuth scopes for Salesforce API access."""

    API = "api"
    FULL = "full"
    REFRESH_TOKEN = "refresh_token"


SCOPES: dict[str, list[SalesforceScope]] = {
    "salesforce_explore_org": [SalesforceScope.API],
    "salesforce_query_records": [SalesforceScope.API],
    "salesforce_get_record": [SalesforceScope.API],
    "salesforce_create_record": [SalesforceScope.API],
    "salesforce_update_record": [SalesforceScope.API],
    "salesforce_search_records": [SalesforceScope.API],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="salesforce",
    display_name="Salesforce",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
