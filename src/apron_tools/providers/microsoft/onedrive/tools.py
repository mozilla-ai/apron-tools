"""Microsoft OneDrive tool functions backed by the Microsoft Graph API."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from apron_tools.providers.microsoft.onedrive.types import (
    CreateFolderParams,
    CreateFolderResult,
    DriveItemSummary,
    FileInfo,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileOutcome,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0
_MAX_LIMIT = 100


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _children_endpoint(base_url: str, path: str) -> str:
    """Resolve the children endpoint for a root or nested folder path."""
    clean = path.strip("/")
    if not clean:
        return f"{base_url}/me/drive/root/children"
    return f"{base_url}/me/drive/root:/{quote(clean, safe='/')}:/children"


@tool(
    scopes=SCOPES["microsoft_onedrive_list_files"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-list-children",
    provider="microsoft",
    service="microsoft_onedrive",
)
async def microsoft_onedrive_list_files(
    params: ListFilesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListFilesResult:
    """List files and folders in the user's OneDrive."""
    limit = min(params.limit, _MAX_LIMIT)
    endpoint = _children_endpoint(base_url, params.folder_path)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                endpoint,
                headers=_headers(token),
                params={
                    "$top": limit,
                    "$orderby": "name",
                    "$select": "id,name,file,folder,webUrl",
                },
            )
    except httpx.HTTPError as exc:
        return ListFilesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListFilesResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    payload = resp.json()
    items = [DriveItemSummary.model_validate(i) for i in payload.get("value", [])]
    has_more = bool(payload.get("@odata.nextLink"))

    return ListFilesResult(
        success=True,
        folder_path=params.folder_path.strip("/"),
        items=items,
        has_more=has_more,
    )


@tool(
    scopes=SCOPES["microsoft_onedrive_search"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-search",
    provider="microsoft",
    service="microsoft_onedrive",
)
async def microsoft_onedrive_search(
    params: SearchParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SearchResult:
    """Search for files and folders in the user's OneDrive."""
    limit = min(params.limit, _MAX_LIMIT)
    # Escape single quotes per OData before URL-encoding; otherwise the
    # server's percent-decode would allow quotes to break out of the
    # string literal in the search(q='...') expression.
    odata_safe = params.query.replace("'", "''")
    endpoint = f"{base_url}/me/drive/root/search(q='{quote(odata_safe, safe='')}')"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                endpoint,
                headers=_headers(token),
                params={
                    "$top": limit,
                    "$select": "id,name,file,folder,webUrl",
                },
            )
    except httpx.HTTPError as exc:
        return SearchResult(success=False, error=str(exc))

    if not resp.is_success:
        return SearchResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    payload = resp.json()
    items = [DriveItemSummary.model_validate(i) for i in payload.get("value", [])]
    has_more = bool(payload.get("@odata.nextLink"))

    return SearchResult(
        success=True,
        query=params.query,
        items=items,
        has_more=has_more,
    )


@tool(
    scopes=SCOPES["microsoft_onedrive_get_file_info"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-get",
    provider="microsoft",
    service="microsoft_onedrive",
)
async def microsoft_onedrive_get_file_info(
    params: GetFileInfoParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> GetFileInfoResult:
    """Get metadata and a temporary download URL for a file in OneDrive."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/me/drive/items/{params.item_id}",
                headers=_headers(token),
                params={
                    "$select": "id,name,size,lastModifiedDateTime,webUrl,file,@microsoft.graph.downloadUrl",
                },
            )
    except httpx.HTTPError as exc:
        return GetFileInfoResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetFileInfoResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    return GetFileInfoResult(success=True, file=FileInfo.model_validate(resp.json()))


@tool(
    scopes=SCOPES["microsoft_onedrive_create_folder"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-post-children",
    provider="microsoft",
    service="microsoft_onedrive",
)
async def microsoft_onedrive_create_folder(
    params: CreateFolderParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreateFolderResult:
    """Create a new folder in OneDrive."""
    endpoint = _children_endpoint(base_url, params.parent_path)
    body = {
        "name": params.folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                endpoint,
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateFolderResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateFolderResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return CreateFolderResult(
        success=True,
        folder_id=data.get("id", ""),
        name=data.get("name", params.folder_name),
        web_url=data.get("webUrl", ""),
    )


@tool(
    scopes=SCOPES["microsoft_onedrive_move_files"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-update",
    provider="microsoft",
    service="microsoft_onedrive",
)
async def microsoft_onedrive_move_files(
    params: MoveFilesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> MoveFilesResult:
    """Move one or more files or folders to a different location in OneDrive."""
    if not params.destination_folder_id.strip():
        return MoveFilesResult(
            success=False,
            error="destination_folder_id is required and cannot be empty.",
        )

    if not params.item_ids:
        return MoveFilesResult(success=False, error="At least one item_id is required.")

    outcomes: list[MoveFileOutcome] = []
    apply_new_name = params.new_name is not None and len(params.item_ids) == 1

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for item_id in params.item_ids:
            outcomes.append(
                await _move_single_item(
                    client,
                    token,
                    item_id,
                    params.destination_folder_id,
                    params.new_name if apply_new_name else None,
                    base_url=base_url,
                )
            )

    return MoveFilesResult(success=True, outcomes=outcomes)


async def _move_single_item(
    client: httpx.AsyncClient,
    token: str,
    item_id: str,
    destination_folder_id: str,
    new_name: str | None,
    *,
    base_url: str,
) -> MoveFileOutcome:
    """Move a single OneDrive item and return its per-item outcome."""
    try:
        get_resp = await client.get(
            f"{base_url}/me/drive/items/{item_id}",
            headers=_headers(token),
            params={"$select": "id,name"},
        )
    except httpx.HTTPError as exc:
        return MoveFileOutcome(item_id=item_id, success=False, error=str(exc))

    if not get_resp.is_success:
        return MoveFileOutcome(
            item_id=item_id,
            success=False,
            error=f"Graph API error {get_resp.status_code}: {get_resp.text}",
        )

    original_name = get_resp.json().get("name", "")

    body: dict = {"parentReference": {"id": destination_folder_id}}
    if new_name:
        body["name"] = new_name

    try:
        patch_resp = await client.patch(
            f"{base_url}/me/drive/items/{item_id}",
            headers=_headers(token, content_type=True),
            json=body,
        )
    except httpx.HTTPError as exc:
        return MoveFileOutcome(
            item_id=item_id,
            success=False,
            name=original_name,
            error=str(exc),
        )

    if not patch_resp.is_success:
        return MoveFileOutcome(
            item_id=item_id,
            success=False,
            name=original_name,
            error=f"Graph API error {patch_resp.status_code}: {patch_resp.text}",
        )

    moved = patch_resp.json()
    return MoveFileOutcome(
        item_id=item_id,
        success=True,
        name=moved.get("name", new_name or original_name),
        web_url=moved.get("webUrl", ""),
    )
