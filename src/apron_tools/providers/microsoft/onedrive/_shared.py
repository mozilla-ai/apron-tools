"""Shared OneDrive file operations via Microsoft Graph API.

Provides async functions for searching, downloading, uploading, and
querying file metadata in OneDrive. Used by the OneDrive, PowerPoint,
and Word tool modules as a shared infrastructure layer.
"""

from __future__ import annotations

import httpx

_BASE_URL = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: str | None = None) -> dict[str, str]:
    """Build authorization headers for a Microsoft Graph API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


async def _explore_folder(
    client: httpx.AsyncClient,
    token: str,
    folder_id: str,
    extensions: set[str],
    found: list[dict],
    *,
    base_url: str,
    max_results: int,
) -> None:
    """Recursively explore a OneDrive folder for files matching extensions."""
    if len(found) >= max_results:
        return

    # The drive root is addressed via /me/drive/root/children, not /me/drive/items/root/children.
    if folder_id == "root":
        url: str | None = f"{base_url}/me/drive/root/children"
    else:
        url = f"{base_url}/me/drive/items/{folder_id}/children"

    params: dict[str, str | int] | None = {
        "$top": 50,
        "$select": "id,name,file,folder,webUrl,lastModifiedDateTime,size",
    }

    while url and len(found) < max_results:
        resp = await client.get(url, headers=_headers(token), params=params)

        if not resp.is_success:
            # Surface auth/server errors instead of silently returning empty results.
            if resp.status_code in (401, 403) or resp.status_code >= 500:
                resp.raise_for_status()
            return

        data = resp.json()
        for item in data.get("value", []):
            if len(found) >= max_results:
                return
            if item.get("file"):
                name = item.get("name", "")
                if any(name.lower().endswith(ext) for ext in extensions):
                    found.append(item)
            elif item.get("folder"):
                await _explore_folder(
                    client, token, item["id"], extensions, found, base_url=base_url, max_results=max_results
                )

        # Follow pagination. @odata.nextLink is a fully qualified URL with query params included.
        url = data.get("@odata.nextLink")
        params = None


async def search_files(
    token: str,
    extensions: set[str],
    max_results: int = 20,
    *,
    base_url: str = _BASE_URL,
) -> list[dict]:
    """Search OneDrive for files matching extensions.

    Tries the search API first (works for work/school accounts). Falls
    back to recursive folder exploration for personal accounts.

    Args:
        token: OAuth bearer token.
        extensions: File extensions to match, e.g. {".pptx", ".ppt"}.
        max_results: Maximum number of results to return.
        base_url: Graph API base URL (overridable for testing).

    Returns:
        List of file metadata dicts from the Graph API.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Try search API first. Use the shortest extension stem as the query
        # term so it matches broadly (e.g. "ppt" matches .ppt, .pptx, .pptm).
        query_term = min((e.lstrip(".") for e in extensions), key=len)
        resp = await client.get(
            f"{base_url}/me/drive/root/search(q='{query_term}')",
            headers=_headers(token),
        )
        if resp.is_success:
            files = [
                item
                for item in resp.json().get("value", [])
                if any(item.get("name", "").lower().endswith(ext) for ext in extensions)
            ]
            # Successful search — return results even if empty.
            return files[:max_results]

        if resp.status_code != 400:
            # Non-400 failures (auth errors, server errors) should surface.
            resp.raise_for_status()

        # 400 means search is unsupported (personal accounts). Fall back to recursive folder exploration.
        found: list[dict] = []
        await _explore_folder(client, token, "root", extensions, found, base_url=base_url, max_results=max_results)
        return found[:max_results]


async def download_file(
    token: str,
    item_id: str,
    *,
    base_url: str = _BASE_URL,
) -> bytes:
    """Download file content from OneDrive by item ID.

    Args:
        token: OAuth bearer token.
        item_id: The OneDrive item ID.
        base_url: Graph API base URL (overridable for testing).

    Returns:
        Raw file bytes.

    Raises:
        httpx.HTTPStatusError: If the download request fails.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(
            f"{base_url}/me/drive/items/{item_id}/content",
            headers=_headers(token),
        )
        resp.raise_for_status()
        return resp.content


async def upload_file(
    token: str,
    data: bytes,
    filename: str,
    mime_type: str,
    folder_path: str = "root",
    *,
    base_url: str = _BASE_URL,
) -> dict:
    """Upload bytes to OneDrive. Returns the created item metadata dict.

    Args:
        token: OAuth bearer token.
        data: Raw file bytes.
        filename: Filename to use in OneDrive.
        mime_type: MIME type of the file content.
        folder_path: OneDrive folder path ("root" for the root folder).
        base_url: Graph API base URL (overridable for testing).

    Returns:
        The Graph API response dict containing id, name, webUrl, etc.

    Raises:
        httpx.HTTPStatusError: If the upload request fails.
    """
    sanitised_folder = folder_path.strip("/")
    upload_path = filename if sanitised_folder in ("root", "") else f"{sanitised_folder}/{filename}"
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.put(
            f"{base_url}/me/drive/root:/{upload_path}:/content",
            headers=_headers(token, content_type=mime_type),
            content=data,
        )
        resp.raise_for_status()
        return resp.json()


async def update_file_content(
    token: str,
    item_id: str,
    data: bytes,
    mime_type: str,
    *,
    base_url: str = _BASE_URL,
) -> dict:
    """Update an existing file's content by item ID.

    Uses PUT /me/drive/items/{id}/content to replace the file in place,
    preserving its location in OneDrive.

    Args:
        token: OAuth bearer token.
        item_id: The OneDrive item ID of the file to update.
        data: New file content as bytes.
        mime_type: MIME type of the file content.
        base_url: Graph API base URL (overridable for testing).

    Returns:
        The Graph API response dict containing updated item metadata.

    Raises:
        httpx.HTTPStatusError: If the upload request fails.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.put(
            f"{base_url}/me/drive/items/{item_id}/content",
            headers=_headers(token, content_type=mime_type),
            content=data,
        )
        resp.raise_for_status()
        return resp.json()


async def get_file_metadata(
    token: str,
    item_id: str,
    *,
    base_url: str = _BASE_URL,
) -> dict:
    """Get file metadata (name, webUrl, etc.) from OneDrive.

    Args:
        token: OAuth bearer token.
        item_id: The OneDrive item ID.
        base_url: Graph API base URL (overridable for testing).

    Returns:
        The Graph API item metadata dict.

    Raises:
        httpx.HTTPStatusError: If the request fails.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(
            f"{base_url}/me/drive/items/{item_id}",
            headers=_headers(token),
        )
        resp.raise_for_status()
        return resp.json()
