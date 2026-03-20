"""Typeform tool functions for interacting with the Typeform API."""

from __future__ import annotations

from typing import Any

import httpx

from apron_tools.providers.typeform.types import (
    CreateFormParams,
    CreateFormResult,
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetFormDetailsParams,
    GetFormDetailsResult,
    GetFormResponsesParams,
    GetFormResponsesResult,
    UpdateFormParams,
    UpdateFormResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_BASE_URL = "https://api.typeform.com"
_TIMEOUT = 30.0

_FORM_PAYLOAD_KEYS = frozenset(
    {
        "title",
        "type",
        "welcome_screens",
        "thankyou_screens",
        "fields",
        "hidden",
        "logic",
        "theme",
        "workspace",
        "settings",
        "variables",
    }
)


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers for a Typeform API request."""
    return {"Authorization": f"Bearer {token}"}


@tool(
    scopes=SCOPES["typeform_explore_workspace"],
    api_docs="https://www.typeform.com/developers/create/reference/retrieve-forms/",
    provider="typeform",
)
async def typeform_explore_workspace(
    params: ExploreWorkspaceParams, *, token: str, base_url: str = _BASE_URL
) -> ExploreWorkspaceResult:
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
        return ExploreWorkspaceResult(success=False, error=str(exc))

    if not response.is_success:
        return ExploreWorkspaceResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return ExploreWorkspaceResult.model_validate(response.json())


@tool(
    scopes=SCOPES["typeform_get_form_details"],
    api_docs="https://www.typeform.com/developers/create/reference/retrieve-form/",
    provider="typeform",
)
async def typeform_get_form_details(
    params: GetFormDetailsParams, *, token: str, base_url: str = _BASE_URL
) -> GetFormDetailsResult:
    """Retrieve details of a single Typeform form."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/forms/{params.form_id}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetFormDetailsResult(success=False, error=str(exc))

    if not response.is_success:
        return GetFormDetailsResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return GetFormDetailsResult.model_validate(response.json())


@tool(
    scopes=SCOPES["typeform_create_form"],
    api_docs="https://www.typeform.com/developers/create/reference/create-form/",
    provider="typeform",
)
async def typeform_create_form(params: CreateFormParams, *, token: str, base_url: str = _BASE_URL) -> CreateFormResult:
    """Create a new Typeform form."""
    payload: dict[str, Any] = {
        "title": params.title,
        "fields": params.fields,
        "settings": {"language": params.language},
    }
    if params.workspace_id:
        payload["workspace"] = {"href": f"{base_url}/workspaces/{params.workspace_id}"}
    if params.welcome_screens:
        payload["welcome_screens"] = params.welcome_screens
    if params.thankyou_screens:
        payload["thankyou_screens"] = params.thankyou_screens
    if params.settings:
        payload["settings"].update(params.settings)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/forms",
                headers={**_headers(token), "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        return CreateFormResult(success=False, error=str(exc))

    if not response.is_success:
        return CreateFormResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return CreateFormResult.model_validate(response.json())


@tool(
    scopes=SCOPES["typeform_update_form"],
    api_docs="https://www.typeform.com/developers/create/reference/update-form/",
    provider="typeform",
)
async def typeform_update_form(params: UpdateFormParams, *, token: str, base_url: str = _BASE_URL) -> UpdateFormResult:
    """Update an existing Typeform form via read-modify-write."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch existing form.
            get_resp = await client.get(
                f"{base_url}/forms/{params.form_id}",
                headers=_headers(token),
            )
            if not get_resp.is_success:
                return UpdateFormResult(
                    success=False,
                    error=f"Typeform API error {get_resp.status_code}: {get_resp.text}",
                )

            existing = get_resp.json()

            # Sanitise to only whitelisted keys for the PUT payload.
            payload = {k: v for k, v in existing.items() if k in _FORM_PAYLOAD_KEYS}

            # Merge caller overrides.
            if params.title is not None:
                payload["title"] = params.title
            if params.fields is not None:
                payload["fields"] = params.fields
            if params.welcome_screens is not None:
                payload["welcome_screens"] = params.welcome_screens
            if params.thankyou_screens is not None:
                payload["thankyou_screens"] = params.thankyou_screens
            if params.workspace_id is not None:
                payload["workspace"] = {"href": f"{base_url}/workspaces/{params.workspace_id}"}
            if params.language is not None:
                settings = payload.get("settings", {}) or {}
                settings["language"] = params.language
                payload["settings"] = settings
            if params.settings is not None:
                settings = payload.get("settings", {}) or {}
                settings.update(params.settings)
                payload["settings"] = settings

            put_resp = await client.put(
                f"{base_url}/forms/{params.form_id}",
                headers={**_headers(token), "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        return UpdateFormResult(success=False, error=str(exc))

    if not put_resp.is_success:
        return UpdateFormResult(
            success=False,
            error=f"Typeform API error {put_resp.status_code}: {put_resp.text}",
        )

    return UpdateFormResult.model_validate(put_resp.json())


@tool(
    scopes=SCOPES["typeform_get_form_responses"],
    api_docs="https://www.typeform.com/developers/responses/reference/retrieve-responses/",
    provider="typeform",
)
async def typeform_get_form_responses(
    params: GetFormResponsesParams, *, token: str, base_url: str = _BASE_URL
) -> GetFormResponsesResult:
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
        return GetFormResponsesResult(success=False, error=str(exc))

    if not response.is_success:
        return GetFormResponsesResult(
            success=False,
            error=f"Typeform API error {response.status_code}: {response.text}",
        )

    return GetFormResponsesResult.model_validate(response.json())
