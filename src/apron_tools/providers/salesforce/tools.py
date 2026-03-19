"""Salesforce tool functions for interacting with the Salesforce REST API."""

from __future__ import annotations

from typing import Any

import httpx

from apron_tools.providers.salesforce.types import (
    CreateRecordParams,
    CreateRecordResult,
    ExploreOrgParams,
    ExploreOrgResult,
    GetRecordParams,
    GetRecordResult,
    QueryRecordsParams,
    QueryRecordsResult,
    SearchRecordsParams,
    SearchRecordsResult,
    SObjectSummary,
    UpdateRecordParams,
    UpdateRecordResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_USERINFO_URL = "https://login.salesforce.com/services/oauth2/userinfo"
_API_VERSION = "v62.0"
_TIMEOUT = 30.0

# Module-level cache keyed by token to avoid repeated userinfo lookups.
_instance_url_cache: dict[str, str] = {}


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers for a Salesforce API request."""
    return {"Authorization": f"Bearer {token}"}


async def _resolve_instance_url(token: str, *, userinfo_url: str = _USERINFO_URL) -> str:
    """Resolve the Salesforce instance URL via the OAuth userinfo endpoint.

    Args:
        token: OAuth access token for authentication.
        userinfo_url: URL of the userinfo endpoint (overridable for testing).

    Returns:
        The instance URL (e.g. ``https://mycompany.my.salesforce.com``).

    Raises:
        RuntimeError: When the instance URL cannot be determined.
    """
    if token in _instance_url_cache:
        return _instance_url_cache[token]

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(userinfo_url, headers=_headers(token))

    if not response.is_success:
        msg = f"Failed to resolve instance URL: userinfo returned {response.status_code}"
        raise RuntimeError(msg)

    data = response.json()

    instance_url = data.get("urls", {}).get("custom_domain")
    if isinstance(instance_url, str) and instance_url.startswith("https://"):
        _instance_url_cache[token] = instance_url
        return instance_url

    msg = "Failed to resolve instance URL: no custom_domain in userinfo response"
    raise RuntimeError(msg)


def _api_url(instance_url: str, path: str) -> str:
    """Build a versioned Salesforce REST API URL."""
    return f"{instance_url}/services/data/{_API_VERSION}{path}"


# ---------------------------------------------------------------------------
# salesforce_explore_org
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_explore_org"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_describeGlobal.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_explore_org(
    params: ExploreOrgParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> ExploreOrgResult:
    """List all SObject types available in the connected Salesforce org."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return ExploreOrgResult(success=False, error=str(exc))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                _api_url(instance_url, "/sobjects"),
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ExploreOrgResult(success=False, error=str(exc))

    if not response.is_success:
        return ExploreOrgResult(
            success=False,
            error=f"Salesforce API error {response.status_code}: {response.text}",
        )

    data = response.json()
    raw_objects: list[dict[str, Any]] = data.get("sobjects", [])
    sobjects = [SObjectSummary.model_validate(obj) for obj in raw_objects]
    return ExploreOrgResult(success=True, sobjects=sobjects)


# ---------------------------------------------------------------------------
# salesforce_query_records
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_query_records"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_query.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_query_records(
    params: QueryRecordsParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> QueryRecordsResult:
    """Run a SOQL query against the connected Salesforce org."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return QueryRecordsResult(success=False, error=str(exc))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                _api_url(instance_url, "/query"),
                headers=_headers(token),
                params={"q": params.soql},
            )
    except httpx.HTTPError as exc:
        return QueryRecordsResult(success=False, error=str(exc))

    if not response.is_success:
        return QueryRecordsResult(
            success=False,
            error=f"Salesforce API error {response.status_code}: {response.text}",
        )

    data = response.json()
    return QueryRecordsResult(
        success=True,
        total_size=data.get("totalSize", 0),
        done=data.get("done", True),
        records=data.get("records", []),
    )


# ---------------------------------------------------------------------------
# salesforce_get_record
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_get_record"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_get_field_values.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_get_record(
    params: GetRecordParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> GetRecordResult:
    """Retrieve a single Salesforce record by object type and ID."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return GetRecordResult(success=False, error=str(exc))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                _api_url(instance_url, f"/sobjects/{params.object_type}/{params.record_id}"),
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetRecordResult(success=False, error=str(exc))

    if not response.is_success:
        return GetRecordResult(
            success=False,
            error=f"Salesforce API error {response.status_code}: {response.text}",
        )

    return GetRecordResult(success=True, record=response.json())


# ---------------------------------------------------------------------------
# salesforce_create_record
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_create_record"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_create_record(
    params: CreateRecordParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> CreateRecordResult:
    """Create a new record in Salesforce."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return CreateRecordResult(success=False, error=str(exc))

    headers = {**_headers(token), "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                _api_url(instance_url, f"/sobjects/{params.object_type}"),
                headers=headers,
                json=params.fields,
            )
    except httpx.HTTPError as exc:
        return CreateRecordResult(success=False, error=str(exc))

    if not response.is_success:
        return CreateRecordResult(
            success=False,
            error=f"Salesforce API error {response.status_code}: {response.text}",
        )

    data = response.json()
    return CreateRecordResult(
        success=data.get("success", True),
        id=data.get("id", ""),
        errors=data.get("errors", []),
    )


# ---------------------------------------------------------------------------
# salesforce_update_record
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_update_record"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_retrieve.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_update_record(
    params: UpdateRecordParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> UpdateRecordResult:
    """Update an existing Salesforce record."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return UpdateRecordResult(success=False, error=str(exc))

    headers = {**_headers(token), "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.patch(
                _api_url(instance_url, f"/sobjects/{params.object_type}/{params.record_id}"),
                headers=headers,
                json=params.fields,
            )
    except httpx.HTTPError as exc:
        return UpdateRecordResult(success=False, error=str(exc))

    # Salesforce returns 204 No Content on success.
    if response.status_code == 204:
        return UpdateRecordResult(success=True)

    return UpdateRecordResult(
        success=False,
        error=f"Salesforce API error {response.status_code}: {response.text}",
    )


# ---------------------------------------------------------------------------
# salesforce_search_records
# ---------------------------------------------------------------------------


@tool(
    scopes=SCOPES["salesforce_search_records"],
    api_docs="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_search.htm",
    provider="salesforce",
    service="salesforce",
)
async def salesforce_search_records(
    params: SearchRecordsParams,
    *,
    token: str,
    userinfo_url: str = _USERINFO_URL,
) -> SearchRecordsResult:
    """Search for records across Salesforce objects using SOSL."""
    try:
        instance_url = await _resolve_instance_url(token, userinfo_url=userinfo_url)
    except RuntimeError as exc:
        return SearchRecordsResult(success=False, error=str(exc))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                _api_url(instance_url, "/search"),
                headers=_headers(token),
                params={"q": params.sosl},
            )
    except httpx.HTTPError as exc:
        return SearchRecordsResult(success=False, error=str(exc))

    if not response.is_success:
        return SearchRecordsResult(
            success=False,
            error=f"Salesforce API error {response.status_code}: {response.text}",
        )

    data = response.json()
    return SearchRecordsResult(
        success=True,
        search_records=data.get("searchRecords", []),
    )
