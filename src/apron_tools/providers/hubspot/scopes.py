"""OAuth scope definitions for HubSpot tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class HubSpotScope(Scope):
    """OAuth scopes for HubSpot CRM API access."""

    CONTACTS_READ = (
        "crm.objects.contacts.read",
        "Read Contacts",
        "View contacts in your HubSpot CRM",
        "read",
        False,
    )
    CONTACTS_WRITE = (
        "crm.objects.contacts.write",
        "Write Contacts",
        "Create and modify contacts in your HubSpot CRM",
        "write",
        False,
    )
    COMPANIES_READ = (
        "crm.objects.companies.read",
        "Read Companies",
        "View companies in your HubSpot CRM",
        "read",
        False,
    )
    COMPANIES_WRITE = (
        "crm.objects.companies.write",
        "Write Companies",
        "Create and modify companies in your HubSpot CRM",
        "write",
        False,
    )
    DEALS_READ = (
        "crm.objects.deals.read",
        "Read Deals",
        "View deals in your HubSpot CRM",
        "read",
        False,
    )
    DEALS_WRITE = (
        "crm.objects.deals.write",
        "Write Deals",
        "Create and modify deals in your HubSpot CRM",
        "write",
        False,
    )
    OWNERS_READ = (
        "crm.objects.owners.read",
        "Read Owners",
        "View record owners in your HubSpot CRM",
        "read",
        False,
    )


# Engagements (notes, tasks, calls, emails, meetings) share the contacts scope
# on HubSpot; HubSpot does not expose dedicated engagement scopes, so CRM access
# to engagement records is gated via the contacts scope family.
SCOPES: dict[str, list[HubSpotScope]] = {
    "hubspot_search_contacts": [HubSpotScope.CONTACTS_READ],
    "hubspot_create_contact": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_update_contact": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_search_companies": [HubSpotScope.COMPANIES_READ],
    "hubspot_create_company": [HubSpotScope.COMPANIES_WRITE],
    "hubspot_update_company": [HubSpotScope.COMPANIES_WRITE],
    "hubspot_search_deals": [HubSpotScope.DEALS_READ],
    "hubspot_create_deal": [HubSpotScope.DEALS_WRITE],
    "hubspot_update_deal": [HubSpotScope.DEALS_WRITE],
    "hubspot_search_notes": [HubSpotScope.CONTACTS_READ],
    "hubspot_create_note": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_update_note": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_search_tasks": [HubSpotScope.CONTACTS_READ],
    "hubspot_create_task": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_update_task": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_search_calls": [HubSpotScope.CONTACTS_READ],
    "hubspot_search_emails": [HubSpotScope.CONTACTS_READ],
    "hubspot_search_meetings": [HubSpotScope.CONTACTS_READ],
    "hubspot_log_activity": [HubSpotScope.CONTACTS_WRITE],
    "hubspot_list_pipelines": [HubSpotScope.DEALS_READ],
    "hubspot_list_owners": [HubSpotScope.OWNERS_READ],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="hubspot",
    display_name="HubSpot",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
