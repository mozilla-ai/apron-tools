"""Microsoft SharePoint tool functions for interacting with the Microsoft Graph API."""

from __future__ import annotations

import httpx

from apron_tools._utils import parse_csv_ids
from apron_tools.providers.microsoft.sharepoint.types import (
    CreateFolderParams,
    CreateFolderResult,
    DriveInfo,
    DriveItem,
    ExploreDriveParams,
    ExploreDriveResult,
    ListDrivesParams,
    ListDrivesResult,
    ListSitesParams,
    ListSitesResult,
    MoveFileItem,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
    SiteInfo,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


@tool(
    scopes=SCOPES["microsoft_sharepoint_list_sites"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/site-list",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_list_sites(
    params: ListSitesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListSitesResult:
    """List available SharePoint sites."""
    limit = min(params.limit, 100)
    search = params.query if params.query else "*"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/sites",
                headers=_headers(token),
                params={"search": search, "$top": limit},
            )
    except httpx.HTTPError as exc:
        return ListSitesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListSitesResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    sites = [SiteInfo.model_validate(s) for s in resp.json().get("value", [])]
    return ListSitesResult(success=True, sites=sites)


@tool(
    scopes=SCOPES["microsoft_sharepoint_list_drives"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/drive-list",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_list_drives(
    params: ListDrivesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ListDrivesResult:
    """List document libraries (drives) in a SharePoint site."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/sites/{params.site_id}/drives",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return ListDrivesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListDrivesResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    drives = [DriveInfo.model_validate(d) for d in resp.json().get("value", [])]
    return ListDrivesResult(success=True, drives=drives)


@tool(
    scopes=SCOPES["microsoft_sharepoint_explore_drive"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-list-children",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_explore_drive(
    params: ExploreDriveParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> ExploreDriveResult:
    """Explore files and folders in a SharePoint document library."""
    limit = min(params.limit, 100)
    if params.folder_path:
        clean_path = params.folder_path.strip("/")
        endpoint = f"{base_url}/drives/{params.drive_id}/root:/{clean_path}:/children"
    else:
        endpoint = f"{base_url}/drives/{params.drive_id}/root/children"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                endpoint,
                headers=_headers(token),
                params={"$top": limit, "$orderby": "name"},
            )
    except httpx.HTTPError as exc:
        return ExploreDriveResult(success=False, error=str(exc))

    if not resp.is_success:
        return ExploreDriveResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    items = [DriveItem.model_validate(i) for i in resp.json().get("value", [])]
    return ExploreDriveResult(success=True, items=items)


@tool(
    scopes=SCOPES["microsoft_sharepoint_create_folder"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-post-children",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_create_folder(
    params: CreateFolderParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> CreateFolderResult:
    """Create a new folder in a SharePoint document library."""
    if params.parent_path:
        clean_path = params.parent_path.strip("/")
        endpoint = f"{base_url}/drives/{params.drive_id}/root:/{clean_path}:/children"
    else:
        endpoint = f"{base_url}/drives/{params.drive_id}/root/children"

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

    folder = DriveItem.model_validate(resp.json())
    return CreateFolderResult(success=True, folder=folder)


@tool(
    scopes=SCOPES["microsoft_sharepoint_search"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-search",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_search(
    params: SearchParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> SearchResult:
    """Search for files in a SharePoint document library."""
    limit = min(params.limit, 100)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/drives/{params.drive_id}/root/search(q='{params.query}')",
                headers=_headers(token),
                params={"$top": limit},
            )
    except httpx.HTTPError as exc:
        return SearchResult(success=False, error=str(exc))

    if not resp.is_success:
        return SearchResult(
            success=False,
            error=f"Graph API error {resp.status_code}: {resp.text}",
        )

    items = [DriveItem.model_validate(i) for i in resp.json().get("value", [])]
    return SearchResult(success=True, items=items)


async def _move_one_item(
    drive_id: str,
    item_id: str,
    destination_folder_id: str,
    token: str,
    base_url: str,
    client: httpx.AsyncClient,
) -> MoveFileItem:
    """Move a single SharePoint drive item and shape the per-item outcome."""
    try:
        get_resp = await client.get(
            f"{base_url}/drives/{drive_id}/items/{item_id}",
            headers=_headers(token),
            params={"$select": "id,name"},
        )
        if not get_resp.is_success:
            return MoveFileItem(
                item_id=item_id,
                success=False,
                error=f"Graph API error {get_resp.status_code}: {get_resp.text}",
            )

        patch_resp = await client.patch(
            f"{base_url}/drives/{drive_id}/items/{item_id}",
            headers=_headers(token, content_type=True),
            json={"parentReference": {"id": destination_folder_id}},
        )
        if not patch_resp.is_success:
            return MoveFileItem(
                item_id=item_id,
                success=False,
                error=f"Graph API error {patch_resp.status_code}: {patch_resp.text}",
            )

    except httpx.HTTPError as exc:
        return MoveFileItem(item_id=item_id, success=False, error=str(exc))

    return MoveFileItem(
        item_id=item_id,
        success=True,
        item=DriveItem.model_validate(patch_resp.json()),
    )


@tool(
    scopes=SCOPES["microsoft_sharepoint_move_files"],
    api_docs="https://learn.microsoft.com/en-us/graph/api/driveitem-update",
    provider="microsoft",
    service="microsoft_sharepoint",
)
async def microsoft_sharepoint_move_files(
    params: MoveFilesParams,
    *,
    token: str,
    base_url: str = _GRAPH_BASE_URL,
) -> MoveFilesResult:
    """Move one or more files or folders to a destination folder in a drive.

    ``destination_folder_id`` is applied to every item in the call. Per-item
    outcomes are returned in ``items`` so partial failures surface without
    aborting the whole bulk call.
    """
    item_ids = parse_csv_ids(params.item_ids)
    if not item_ids:
        return MoveFilesResult(success=False, error="No item IDs provided.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        items = [
            await _move_one_item(params.drive_id, item_id, params.destination_folder_id, token, base_url, client)
            for item_id in item_ids
        ]
    return MoveFilesResult(
        success=True,
        destination_folder_id=params.destination_folder_id,
        items=items,
    )
