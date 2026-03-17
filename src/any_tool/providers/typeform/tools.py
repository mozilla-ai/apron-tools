"""Typeform tool functions for interacting with the Typeform API."""

from __future__ import annotations

import httpx

from any_tool.providers.typeform.types import (
    GetFormParams,
    GetFormResult,
    GetResponsesParams,
    GetResponsesResult,
    ListFormsParams,
    ListFormsResult,
)
from any_tool.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.typeform.com"
_TIMEOUT = 30.0


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers for a Typeform API request."""
    return {"Authorization": f"Bearer {token}"}


@tool(
    scopes=SCOPES["list_forms"],
    api_docs="https://www.typeform.com/developers/create/reference/retrieve-forms/",
    provider="typeform",
)
async def list_forms(params: ListFormsParams, *, token: str, base_url: str = _BASE_URL) -> ListFormsResult:
    """List forms in the authenticated Typeform account."""
    query: dict[str, str | int] = {
        "page": params.page,
        "page_size": params.page_size,
    }
    if params.search is not None:
        query["search"] = params.search
    if params.workspace_id is not None:
        query["workspace_id"] = params.workspace_id

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/forms",
                headers=_headers(token),
                params=query,
            )
    except httpx.HTTPError as exc:
        return ListFormsResult(success=False, error=str(exc))

    if not response.is_success:
        return ListFormsResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return ListFormsResult.model_validate(response.json())


@tool(
    scopes=SCOPES["get_form"],
    api_docs="https://www.typeform.com/developers/create/reference/retrieve-form/",
    provider="typeform",
)
async def get_form(params: GetFormParams, *, token: str, base_url: str = _BASE_URL) -> GetFormResult:
    """Retrieve a single Typeform form by its ID."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/forms/{params.form_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetFormResult(success=False, error=str(exc))

    if not response.is_success:
        return GetFormResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return GetFormResult.model_validate(response.json())


@tool(
    scopes=SCOPES["get_responses"],
    api_docs="https://www.typeform.com/developers/responses/reference/retrieve-responses/",
    provider="typeform",
)
async def get_responses(params: GetResponsesParams, *, token: str, base_url: str = _BASE_URL) -> GetResponsesResult:
    """Retrieve responses for a Typeform form."""
    query: dict[str, str | int | bool] = {
        "page_size": params.page_size,
    }
    if params.since is not None:
        query["since"] = params.since
    if params.until is not None:
        query["until"] = params.until
    if params.after is not None:
        query["after"] = params.after
    if params.before is not None:
        query["before"] = params.before
    if params.completed is not None:
        query["completed"] = params.completed

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/forms/{params.form_id}/responses",
                headers=_headers(token),
                params=query,
            )
    except httpx.HTTPError as exc:
        return GetResponsesResult(success=False, error=str(exc))

    if not response.is_success:
        return GetResponsesResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return GetResponsesResult.model_validate(response.json())
