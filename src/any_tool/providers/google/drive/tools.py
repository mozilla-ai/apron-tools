"""Google Drive tool functions for interacting with the Drive REST API."""

from __future__ import annotations

import httpx

from any_tool.providers.google.drive.types import (
    CreateFolderParams,
    CreateFolderResult,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileParams,
    MoveFileResult,
    SearchParams,
    SearchResult,
    ShareFileParams,
    ShareFileResult,
)
from any_tool.tool import tool

from .scopes import SCOPES

_DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3/files"
_TIMEOUT = 60.0

_FILE_FIELDS = "id,name,mimeType,createdTime,modifiedTime,parents,webViewLink"
_FILE_DETAIL_FIELDS = (
    "id,name,mimeType,description,starred,trashed,parents,webViewLink,"
    "createdTime,modifiedTime,size,owners(displayName,emailAddress),shared"
)


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Google API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


@tool(
    scopes=SCOPES["google_drive_list_files"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/list",
    provider="google",
    service="google_drive",
)
async def google_drive_list_files(
    params: ListFilesParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> ListFilesResult:
    """List files in Google Drive, optionally filtered to a specific folder."""
    query_parts: list[str] = ["trashed = false"]
    if params.folder_id:
        query_parts.append(f"'{params.folder_id}' in parents")

    query_params: dict[str, str | int] = {
        "q": " and ".join(query_parts),
        "pageSize": params.max_results,
        "fields": f"files({_FILE_FIELDS})",
        "orderBy": "modifiedTime desc",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "corpora": "allDrives",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                base_url,
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListFilesResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListFilesResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return ListFilesResult.model_validate(data)


@tool(
    scopes=SCOPES["google_drive_create_folder"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/create",
    provider="google",
    service="google_drive",
)
async def google_drive_create_folder(
    params: CreateFolderParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> CreateFolderResult:
    """Create a new folder in Google Drive."""
    body: dict = {
        "name": params.name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if params.parent_id:
        body["parents"] = [params.parent_id]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                base_url,
                headers=_headers(token, content_type=True),
                params={"fields": "id,name,webViewLink"},
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateFolderResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateFolderResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return CreateFolderResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_drive_get_file_info"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/get",
    provider="google",
    service="google_drive",
)
async def google_drive_get_file_info(
    params: GetFileInfoParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> GetFileInfoResult:
    """Get detailed metadata about a file in Google Drive."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/{params.file_id}",
                headers=_headers(token),
                params={
                    "fields": _FILE_DETAIL_FIELDS,
                    "supportsAllDrives": "true",
                },
            )
    except httpx.HTTPError as exc:
        return GetFileInfoResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetFileInfoResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return GetFileInfoResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_drive_move_file"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/update",
    provider="google",
    service="google_drive",
)
async def google_drive_move_file(
    params: MoveFileParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> MoveFileResult:
    """Move a file to a different folder in Google Drive."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Fetch the current parents to remove the file from them.
            meta_resp = await client.get(
                f"{base_url}/{params.file_id}",
                headers=_headers(token),
                params={
                    "fields": "parents",
                    "supportsAllDrives": "true",
                },
            )
            if not meta_resp.is_success:
                return MoveFileResult(
                    success=False,
                    error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
                )

            current_parents = meta_resp.json().get("parents", [])
            remove_parents = ",".join(current_parents)

            resp = await client.patch(
                f"{base_url}/{params.file_id}",
                headers=_headers(token, content_type=True),
                params={
                    "addParents": params.destination_folder_id,
                    "removeParents": remove_parents,
                    "fields": "id,name,parents",
                    "supportsAllDrives": "true",
                },
                json={},
            )
    except httpx.HTTPError as exc:
        return MoveFileResult(success=False, error=str(exc))

    if not resp.is_success:
        return MoveFileResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return MoveFileResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_drive_search"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/list",
    provider="google",
    service="google_drive",
)
async def google_drive_search(
    params: SearchParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> SearchResult:
    """Search for files in Google Drive by name."""
    query_params: dict[str, str | int] = {
        "q": f"name contains '{params.query}' and trashed = false",
        "pageSize": params.max_results,
        "fields": f"files({_FILE_FIELDS})",
        "orderBy": "modifiedTime desc",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "corpora": "allDrives",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                base_url,
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return SearchResult(success=False, error=str(exc))

    if not resp.is_success:
        return SearchResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return SearchResult.model_validate(data)


@tool(
    scopes=SCOPES["google_drive_share_file"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/permissions/create",
    provider="google",
    service="google_drive",
)
async def google_drive_share_file(
    params: ShareFileParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> ShareFileResult:
    """Share a file with another user in Google Drive."""
    body = {
        "type": "user",
        "role": params.role,
        "emailAddress": params.email,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/{params.file_id}/permissions",
                headers=_headers(token, content_type=True),
                params={"supportsAllDrives": "true"},
                json=body,
            )
    except httpx.HTTPError as exc:
        return ShareFileResult(success=False, error=str(exc))

    if not resp.is_success:
        return ShareFileResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return ShareFileResult.model_validate(resp.json())
