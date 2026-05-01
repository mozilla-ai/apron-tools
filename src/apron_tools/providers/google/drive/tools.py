"""Google Drive tool functions for interacting with the Drive REST API."""

from __future__ import annotations

import httpx

from apron_tools._utils import parse_csv_ids
from apron_tools.fileio import resolve_file_input
from apron_tools.providers.google.drive.types import (
    CreateFolderParams,
    CreateFolderResult,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileItem,
    MoveFilesParams,
    MoveFilesResult,
    ReadTextFileParams,
    ReadTextFileResult,
    SearchParams,
    SearchResult,
    ShareFileItem,
    ShareFilesParams,
    ShareFilesResult,
    UploadFileParams,
    UploadFileResult,
)
from apron_tools.tool import tool

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


async def _move_one_file(
    file_id: str,
    destination_folder_id: str,
    token: str,
    base_url: str,
    client: httpx.AsyncClient,
) -> MoveFileItem:
    """Move a single Drive file and shape the per-file outcome."""
    try:
        meta_resp = await client.get(
            f"{base_url}/{file_id}",
            headers=_headers(token),
            params={
                "fields": "parents",
                "supportsAllDrives": "true",
            },
        )
        if not meta_resp.is_success:
            return MoveFileItem(
                file_id=file_id,
                success=False,
                error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
            )

        current_parents = meta_resp.json().get("parents", [])
        remove_parents = ",".join(current_parents)

        resp = await client.patch(
            f"{base_url}/{file_id}",
            headers=_headers(token, content_type=True),
            params={
                "addParents": destination_folder_id,
                "removeParents": remove_parents,
                "fields": "id,name,parents",
                "supportsAllDrives": "true",
            },
            json={},
        )
    except httpx.HTTPError as exc:
        return MoveFileItem(file_id=file_id, success=False, error=str(exc))

    if not resp.is_success:
        return MoveFileItem(
            file_id=file_id,
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return MoveFileItem(
        file_id=data.get("id", file_id),
        success=True,
        name=data.get("name", ""),
        parents=data.get("parents", []),
    )


@tool(
    scopes=SCOPES["google_drive_move_files"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/update",
    provider="google",
    service="google_drive",
)
async def google_drive_move_files(
    params: MoveFilesParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> MoveFilesResult:
    """Move one or more files to a destination folder in Google Drive.

    ``destination_folder_id`` is applied to every file in the call. Per-file
    outcomes are returned in ``items`` so partial failures surface without
    aborting the whole bulk call.
    """
    file_ids = parse_csv_ids(params.file_ids)
    if not file_ids:
        return MoveFilesResult(success=False, error="No file IDs provided.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        items = [
            await _move_one_file(file_id, params.destination_folder_id, token, base_url, client) for file_id in file_ids
        ]
    return MoveFilesResult(
        success=True,
        destination_folder_id=params.destination_folder_id,
        items=items,
    )


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


async def _share_one_file(
    file_id: str,
    email: str,
    role: str,
    token: str,
    base_url: str,
    client: httpx.AsyncClient,
) -> ShareFileItem:
    """Create a single Drive permission and shape the per-file outcome."""
    body = {
        "type": "user",
        "role": role,
        "emailAddress": email,
    }

    try:
        resp = await client.post(
            f"{base_url}/{file_id}/permissions",
            headers=_headers(token, content_type=True),
            params={"supportsAllDrives": "true"},
            json=body,
        )
    except httpx.HTTPError as exc:
        return ShareFileItem(file_id=file_id, success=False, error=str(exc))

    if not resp.is_success:
        return ShareFileItem(
            file_id=file_id,
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    return ShareFileItem(
        file_id=file_id,
        success=True,
        permission_id=data.get("id", ""),
        type=data.get("type", ""),
        role=data.get("role", ""),
        emailAddress=data.get("emailAddress", ""),
        displayName=data.get("displayName", ""),
    )


@tool(
    scopes=SCOPES["google_drive_share_files"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/permissions/create",
    provider="google",
    service="google_drive",
)
async def google_drive_share_files(
    params: ShareFilesParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> ShareFilesResult:
    """Share one or more files with another user in Google Drive.

    ``email`` and ``role`` are applied to every file in the call. Per-file
    outcomes are returned in ``items`` so partial failures surface without
    aborting the whole bulk call.
    """
    file_ids = parse_csv_ids(params.file_ids)
    if not file_ids:
        return ShareFilesResult(success=False, error="No file IDs provided.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        items = [
            await _share_one_file(file_id, params.email, params.role, token, base_url, client) for file_id in file_ids
        ]
    return ShareFilesResult(
        success=True,
        email=params.email,
        role=params.role,
        items=items,
    )


_UPLOAD_BASE_URL = "https://www.googleapis.com/upload/drive/v3/files"


@tool(
    scopes=SCOPES["google_drive_upload_file"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/create",
    provider="google",
    service="google_drive",
)
async def google_drive_upload_file(
    params: UploadFileParams,
    *,
    token: str,
    base_url: str = _UPLOAD_BASE_URL,
) -> UploadFileResult:
    """Upload a file to Google Drive."""
    import json
    import uuid

    try:
        data, filename, mime_type = await resolve_file_input(params.file)
    except Exception as exc:
        return UploadFileResult(success=False, error=f"Failed to resolve file: {exc}")

    upload_name = params.name or filename

    # Always use multipart/related upload so metadata (name, parents) is included.
    metadata: dict = {"name": upload_name}
    if params.folder_id:
        metadata["parents"] = [params.folder_id]

    boundary = f"apron_{uuid.uuid4().hex}"
    body = (
        (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode()
        + data
        + f"\r\n--{boundary}--".encode()
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                params={"uploadType": "multipart", "fields": _FILE_FIELDS, "supportsAllDrives": "true"},
                content=body,
            )
    except httpx.HTTPError as exc:
        return UploadFileResult(success=False, error=str(exc))

    if not resp.is_success:
        return UploadFileResult(
            success=False,
            error=f"Drive API error {resp.status_code}: {resp.text}",
        )

    return UploadFileResult.model_validate(resp.json())


@tool(
    scopes=SCOPES["google_drive_read_text_file"],
    api_docs="https://developers.google.com/drive/api/reference/rest/v3/files/get",
    provider="google",
    service="google_drive",
)
async def google_drive_read_text_file(
    params: ReadTextFileParams,
    *,
    token: str,
    base_url: str = _DRIVE_BASE_URL,
) -> ReadTextFileResult:
    """Read the contents of a plain text file from Google Drive."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            # Get metadata to verify it's a text file.
            meta_resp = await client.get(
                f"{base_url}/{params.file_id}",
                headers=_headers(token),
                params={"fields": "name,mimeType", "supportsAllDrives": "true"},
            )
            if not meta_resp.is_success:
                return ReadTextFileResult(
                    success=False,
                    error=f"Drive API error {meta_resp.status_code}: {meta_resp.text}",
                )

            meta = meta_resp.json()
            file_name = meta.get("name", "Untitled")
            mime_type = meta.get("mimeType", "unknown")

            if mime_type != "text/plain":
                return ReadTextFileResult(
                    success=False,
                    error=f"Only files with MIME type 'text/plain' are supported."
                    f" '{file_name}' has type '{mime_type}'.",
                )

            content_resp = await client.get(
                f"{base_url}/{params.file_id}",
                headers=_headers(token),
                params={"alt": "media", "supportsAllDrives": "true"},
            )
    except httpx.HTTPError as exc:
        return ReadTextFileResult(success=False, error=str(exc))

    if not content_resp.is_success:
        return ReadTextFileResult(
            success=False,
            error=f"Drive API error {content_resp.status_code}: {content_resp.text}",
        )

    return ReadTextFileResult(
        success=True,
        name=file_name,
        content=content_resp.text,
    )
