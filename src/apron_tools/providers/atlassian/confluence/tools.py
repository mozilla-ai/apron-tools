"""Atlassian Confluence tool functions for interacting with the Confluence REST API."""

from __future__ import annotations

import httpx

from apron_tools.providers.atlassian.confluence.types import (
    ChildPageSummary,
    CreatePageParams,
    CreatePageResult,
    ExploreSpacesParams,
    ExploreSpacesResult,
    GetChildPagesParams,
    GetChildPagesResult,
    GetPageContentParams,
    GetPageContentResult,
    PageSummary,
    SearchContentParams,
    SearchContentResult,
    SearchResult,
    SpaceSummary,
    UpdatePageParams,
    UpdatePageResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.atlassian.com"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Confluence API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


async def _resolve_cloud_id(token: str, base_url: str) -> str | None:
    """Resolve the Confluence cloud ID for the authenticated user.

    Atlassian cloud APIs require a cloud ID to construct API URLs. This
    calls the accessible-resources endpoint to retrieve it.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/oauth/token/accessible-resources",
                headers=_headers(token),
            )
            if resp.is_success:
                resources = resp.json()
                if resources:
                    return resources[0].get("id")
    except httpx.HTTPError:
        pass
    return None


def _api_v2_url(cloud_id: str, path: str, *, base_url: str) -> str:
    """Build a Confluence REST API v2 URL."""
    return f"{base_url}/ex/confluence/{cloud_id}/wiki/api/v2{path}"


def _api_v1_url(cloud_id: str, path: str, *, base_url: str) -> str:
    """Build a Confluence REST API v1 URL."""
    return f"{base_url}/ex/confluence/{cloud_id}/wiki/rest/api{path}"


@tool(
    scopes=SCOPES["atlassian_confluence_explore_spaces"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-space/#api-wiki-api-v2-spaces-get",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_explore_spaces(
    params: ExploreSpacesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> ExploreSpacesResult:
    """List all Confluence spaces accessible to the authenticated user."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return ExploreSpacesResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_v2_url(cloud_id, "/spaces", base_url=base_url),
                headers=_headers(token),
                params={"limit": params.max_results},
            )
    except httpx.HTTPError as exc:
        return ExploreSpacesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ExploreSpacesResult(
            success=False,
            error=f"Confluence API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    spaces = [SpaceSummary.model_validate(s) for s in data.get("results", [])]
    return ExploreSpacesResult(success=True, spaces=spaces)


@tool(
    scopes=SCOPES["atlassian_confluence_get_page_content"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-wiki-api-v2-pages-id-get",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_get_page_content(
    params: GetPageContentParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetPageContentResult:
    """Retrieve a Confluence page by ID, including its storage-format body."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return GetPageContentResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_v2_url(cloud_id, f"/pages/{params.page_id}", base_url=base_url),
                headers=_headers(token),
                params={"body-format": "storage"},
            )
    except httpx.HTTPError as exc:
        return GetPageContentResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetPageContentResult(
            success=False,
            error=f"Confluence API error {resp.status_code}: {resp.text}",
        )

    page = PageSummary.model_validate(resp.json())
    return GetPageContentResult(success=True, page=page)


@tool(
    scopes=SCOPES["atlassian_confluence_create_page"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-wiki-api-v2-pages-post",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_create_page(
    params: CreatePageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> CreatePageResult:
    """Create a new Confluence page."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return CreatePageResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    payload: dict = {
        "spaceId": params.space_id,
        "status": params.status,
        "title": params.title,
        "body": {
            "representation": "storage",
            "value": params.body,
        },
    }
    if params.parent_id:
        payload["parentId"] = params.parent_id

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                _api_v2_url(cloud_id, "/pages", base_url=base_url),
                headers=_headers(token, content_type=True),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return CreatePageResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreatePageResult(
            success=False,
            error=f"Confluence API error {resp.status_code}: {resp.text}",
        )

    page = PageSummary.model_validate(resp.json())
    return CreatePageResult(success=True, page=page)


@tool(
    scopes=SCOPES["atlassian_confluence_update_page"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-wiki-api-v2-pages-id-get",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_update_page(
    params: UpdatePageParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> UpdatePageResult:
    """Update an existing Confluence page.

    Fetches the current version number first, then sends the update with
    version incremented by one.
    """
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return UpdatePageResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    # Fetch current page to get the version number.
    page_url = _api_v2_url(cloud_id, f"/pages/{params.page_id}", base_url=base_url)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            get_resp = await client.get(
                page_url,
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return UpdatePageResult(success=False, error=str(exc))

    if not get_resp.is_success:
        return UpdatePageResult(
            success=False,
            error=f"Confluence API error {get_resp.status_code}: {get_resp.text}",
        )

    current_data = get_resp.json()
    current_version = current_data.get("version", {}).get("number", 0)

    payload = {
        "id": params.page_id,
        "status": params.status,
        "title": params.title,
        "body": {
            "representation": "storage",
            "value": params.body,
        },
        "version": {
            "number": current_version + 1,
            "message": "",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            put_resp = await client.put(
                page_url,
                headers=_headers(token, content_type=True),
                json=payload,
            )
    except httpx.HTTPError as exc:
        return UpdatePageResult(success=False, error=str(exc))

    if not put_resp.is_success:
        return UpdatePageResult(
            success=False,
            error=f"Confluence API error {put_resp.status_code}: {put_resp.text}",
        )

    page = PageSummary.model_validate(put_resp.json())
    return UpdatePageResult(success=True, page=page)


@tool(
    scopes=SCOPES["atlassian_confluence_search_content"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-search/#api-wiki-rest-api-search-get",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_search_content(
    params: SearchContentParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> SearchContentResult:
    """Search Confluence content using CQL (Confluence Query Language)."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return SearchContentResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_v1_url(cloud_id, "/search", base_url=base_url),
                headers=_headers(token),
                params={"cql": params.cql, "limit": params.limit},
            )
    except httpx.HTTPError as exc:
        return SearchContentResult(success=False, error=str(exc))

    if not resp.is_success:
        return SearchContentResult(
            success=False,
            error=f"Confluence API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    results = [SearchResult.model_validate(r) for r in data.get("results", [])]
    return SearchContentResult(
        success=True,
        results=results,
        total_size=data.get("totalSize", len(results)),
        cql_query=data.get("cqlQuery", params.cql),
    )


@tool(
    scopes=SCOPES["atlassian_confluence_get_child_pages"],
    api_docs="https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-children/#api-pages-id-direct-children-get",
    provider="atlassian",
    service="atlassian_confluence",
)
async def atlassian_confluence_get_child_pages(
    params: GetChildPagesParams,
    *,
    token: str,
    base_url: str = _BASE_URL,
) -> GetChildPagesResult:
    """List direct child pages of a Confluence page."""
    cloud_id = await _resolve_cloud_id(token, base_url)
    if not cloud_id:
        return GetChildPagesResult(
            success=False,
            error="Failed to resolve Confluence cloud ID. Ensure you have access to a Confluence site.",
        )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _api_v2_url(
                    cloud_id,
                    f"/pages/{params.page_id}/direct-children",
                    base_url=base_url,
                ),
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetChildPagesResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetChildPagesResult(
            success=False,
            error=f"Confluence API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    children = [ChildPageSummary.model_validate(c) for c in data.get("results", [])]
    return GetChildPagesResult(success=True, children=children)
