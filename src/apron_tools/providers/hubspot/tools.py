"""HubSpot tool functions for interacting with the HubSpot CRM API."""

from __future__ import annotations

from typing import Any

import httpx

from apron_tools.providers.hubspot.types import (
    Association,
    CreateCompanyParams,
    CreateContactParams,
    CreateDealParams,
    CreateNoteParams,
    CreateResult,
    CreateTaskParams,
    CrmRecord,
    SearchCompaniesParams,
    SearchContactsParams,
    SearchDealsParams,
    SearchNotesParams,
    SearchResult,
    SearchTasksParams,
    UpdateCompanyParams,
    UpdateContactParams,
    UpdateDealParams,
    UpdateNoteParams,
    UpdateResult,
    UpdateTaskParams,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.hubapi.com"
_TIMEOUT = 30.0


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers for a HubSpot API request."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def _search_objects(
    object_type: str,
    query: str,
    limit: int,
    properties: list[str],
    *,
    token: str,
    base_url: str,
) -> SearchResult:
    """Execute a CRM Search API query and return a typed SearchResult."""
    payload: dict[str, Any] = {
        "query": query,
        "limit": max(1, min(limit, 100)),
        "properties": properties,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/crm/v3/objects/{object_type}/search",
                headers=_headers(token),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return SearchResult(success=False, error=str(exc))

    if not response.is_success:
        return SearchResult(
            success=False,
            error=f"HubSpot API error {response.status_code}: {response.text}",
        )

    data = response.json()
    records = [CrmRecord.model_validate(r) for r in data.get("results", [])]
    total = data.get("total") if isinstance(data.get("total"), int) else None
    has_more = bool(data.get("paging")) or (total is not None and total > len(records))
    return SearchResult(success=True, results=records, total=total, has_more=has_more)


async def _create_object(
    object_type: str,
    properties: dict[str, Any],
    associations: list[Association] | None,
    *,
    token: str,
    base_url: str,
) -> CreateResult:
    """Create a CRM record and return a typed CreateResult."""
    body: dict[str, Any] = {"properties": properties}
    if associations:
        body["associations"] = [a.model_dump(exclude_none=True) for a in associations]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/crm/v3/objects/{object_type}",
                headers=_headers(token),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateResult(success=False, error=str(exc))

    if not response.is_success:
        return CreateResult(
            success=False,
            error=f"HubSpot API error {response.status_code}: {response.text}",
        )

    data = response.json()
    return CreateResult(
        success=True,
        id=str(data.get("id", "")),
        properties=data.get("properties", {}) or {},
    )


async def _update_object(
    object_type: str,
    record_id: str,
    properties: dict[str, Any],
    *,
    token: str,
    base_url: str,
) -> UpdateResult:
    """Update a CRM record and return a typed UpdateResult."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.patch(
                f"{base_url}/crm/v3/objects/{object_type}/{record_id}",
                headers=_headers(token),
                json={"properties": properties},
            )
    except httpx.HTTPError as exc:
        return UpdateResult(success=False, error=str(exc))

    if not response.is_success:
        return UpdateResult(
            success=False,
            error=f"HubSpot API error {response.status_code}: {response.text}",
        )

    data = response.json() if response.content else {}
    return UpdateResult(success=True, id=str(data.get("id", record_id)))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["hubspot_search_contacts"],
    api_docs="https://developers.hubspot.com/docs/api/crm/search",
    provider="hubspot",
)
async def hubspot_search_contacts(
    params: SearchContactsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchResult:
    """Search for contacts in HubSpot using a text query."""
    return await _search_objects(
        "contacts",
        params.query,
        params.limit,
        params.properties,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_create_contact"],
    api_docs="https://developers.hubspot.com/docs/api/crm/contacts",
    provider="hubspot",
)
async def hubspot_create_contact(
    params: CreateContactParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateResult:
    """Create a new contact in HubSpot."""
    return await _create_object(
        "contacts",
        params.properties,
        params.associations,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_update_contact"],
    api_docs="https://developers.hubspot.com/docs/api/crm/contacts",
    provider="hubspot",
)
async def hubspot_update_contact(
    params: UpdateContactParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateResult:
    """Update an existing contact in HubSpot."""
    return await _update_object(
        "contacts",
        params.record_id,
        params.properties,
        token=token,
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["hubspot_search_companies"],
    api_docs="https://developers.hubspot.com/docs/api/crm/search",
    provider="hubspot",
)
async def hubspot_search_companies(
    params: SearchCompaniesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchResult:
    """Search for companies in HubSpot using a text query."""
    return await _search_objects(
        "companies",
        params.query,
        params.limit,
        params.properties,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_create_company"],
    api_docs="https://developers.hubspot.com/docs/api/crm/companies",
    provider="hubspot",
)
async def hubspot_create_company(
    params: CreateCompanyParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateResult:
    """Create a new company in HubSpot."""
    return await _create_object(
        "companies",
        params.properties,
        params.associations,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_update_company"],
    api_docs="https://developers.hubspot.com/docs/api/crm/companies",
    provider="hubspot",
)
async def hubspot_update_company(
    params: UpdateCompanyParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateResult:
    """Update an existing company in HubSpot."""
    return await _update_object(
        "companies",
        params.record_id,
        params.properties,
        token=token,
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["hubspot_search_deals"],
    api_docs="https://developers.hubspot.com/docs/api/crm/search",
    provider="hubspot",
)
async def hubspot_search_deals(
    params: SearchDealsParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchResult:
    """Search for deals in HubSpot using a text query."""
    return await _search_objects(
        "deals",
        params.query,
        params.limit,
        params.properties,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_create_deal"],
    api_docs="https://developers.hubspot.com/docs/api/crm/deals",
    provider="hubspot",
)
async def hubspot_create_deal(
    params: CreateDealParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateResult:
    """Create a new deal in HubSpot."""
    return await _create_object(
        "deals",
        params.properties,
        params.associations,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_update_deal"],
    api_docs="https://developers.hubspot.com/docs/api/crm/deals",
    provider="hubspot",
)
async def hubspot_update_deal(
    params: UpdateDealParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateResult:
    """Update an existing deal in HubSpot."""
    return await _update_object(
        "deals",
        params.record_id,
        params.properties,
        token=token,
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["hubspot_search_notes"],
    api_docs="https://developers.hubspot.com/docs/api/crm/search",
    provider="hubspot",
)
async def hubspot_search_notes(
    params: SearchNotesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchResult:
    """Search for note engagements in HubSpot using a text query."""
    return await _search_objects(
        "notes",
        params.query,
        params.limit,
        params.properties,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_create_note"],
    api_docs="https://developers.hubspot.com/docs/api/crm/notes",
    provider="hubspot",
)
async def hubspot_create_note(
    params: CreateNoteParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateResult:
    """Create a note engagement in HubSpot."""
    return await _create_object(
        "notes",
        params.properties,
        params.associations,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_update_note"],
    api_docs="https://developers.hubspot.com/docs/api/crm/notes",
    provider="hubspot",
)
async def hubspot_update_note(
    params: UpdateNoteParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateResult:
    """Update an existing note engagement in HubSpot."""
    return await _update_object(
        "notes",
        params.record_id,
        params.properties,
        token=token,
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["hubspot_search_tasks"],
    api_docs="https://developers.hubspot.com/docs/api/crm/search",
    provider="hubspot",
)
async def hubspot_search_tasks(
    params: SearchTasksParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchResult:
    """Search for task engagements in HubSpot using a text query."""
    return await _search_objects(
        "tasks",
        params.query,
        params.limit,
        params.properties,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_create_task"],
    api_docs="https://developers.hubspot.com/docs/api/crm/tasks",
    provider="hubspot",
)
async def hubspot_create_task(
    params: CreateTaskParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreateResult:
    """Create a task engagement in HubSpot."""
    return await _create_object(
        "tasks",
        params.properties,
        params.associations,
        token=token,
        base_url=base_url,
    )


@tool(
    scopes=SCOPES["hubspot_update_task"],
    api_docs="https://developers.hubspot.com/docs/api/crm/tasks",
    provider="hubspot",
)
async def hubspot_update_task(
    params: UpdateTaskParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdateResult:
    """Update an existing task engagement in HubSpot."""
    return await _update_object(
        "tasks",
        params.record_id,
        params.properties,
        token=token,
        base_url=base_url,
    )
