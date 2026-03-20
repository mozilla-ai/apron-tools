"""Shared image upload helpers for Google Docs and Slides.

Both insert_image tools follow the same flow: resolve the file input,
validate it is an image, upload to Drive via multipart/related, set
public reader permissions so the Docs/Slides API can fetch it, and
clean up the Drive file if the downstream insert fails.

.. warning:: Security consideration

    Uploaded images are shared with ``type: anyone, role: reader`` so
    that the Docs/Slides batchUpdate API can fetch them by URL. The
    public permission persists after insertion. Callers that need
    stricter access control should revoke the permission or delete the
    Drive file after the image has been embedded.
"""

from __future__ import annotations

import contextlib
import json
import uuid

import httpx

from apron_tools.fileio import resolve_file_input
from apron_tools.types import FileInput

_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
_DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3/files"
_TIMEOUT = 60.0


async def upload_image_to_drive(
    file: FileInput,
    token: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, str, str]:
    """Upload an image to Google Drive and make it publicly readable.

    Args:
        file: Image file to upload.
        token: OAuth bearer token.
        client: Optional shared httpx client for connection reuse.

    Returns:
        A tuple of (drive_file_id, public_url, filename).

    Raises:
        ValueError: If the file is not an image.
        httpx.HTTPStatusError: If a Drive API call fails.
    """
    data, filename, mime_type = await resolve_file_input(file)

    if not mime_type.startswith("image/"):
        raise ValueError(f"Only image files are supported. '{filename}' has type '{mime_type}'.")

    # Upload to Drive via multipart/related.
    boundary = f"apron_{uuid.uuid4().hex}"
    body = (
        (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps({'name': filename})}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode()
        + data
        + f"\r\n--{boundary}--".encode()
    )

    async def _do_upload(c: httpx.AsyncClient) -> tuple[str, str]:
        upload_resp = await c.post(
            _DRIVE_UPLOAD_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            params={
                "uploadType": "multipart",
                "fields": "id,webContentLink",
                "supportsAllDrives": "true",
            },
            content=body,
        )
        upload_resp.raise_for_status()
        resp_data = upload_resp.json()
        file_id = resp_data["id"]

        # Set public reader permissions so the Docs/Slides API can fetch the image.
        try:
            perm_resp = await c.post(
                f"{_DRIVE_BASE_URL}/{file_id}/permissions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"role": "reader", "type": "anyone"},
            )
            perm_resp.raise_for_status()
        except httpx.HTTPError:
            # Best-effort cleanup if permission setting fails.
            with contextlib.suppress(httpx.HTTPError):
                await c.delete(
                    f"{_DRIVE_BASE_URL}/{file_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"supportsAllDrives": "true"},
                )
            raise

        # Prefer webContentLink from the API when available.
        public_url = resp_data.get(
            "webContentLink",
            f"https://drive.google.com/uc?id={file_id}&export=download",
        )
        return file_id, public_url

    if client is not None:
        drive_file_id, public_url = await _do_upload(client)
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            drive_file_id, public_url = await _do_upload(c)

    return drive_file_id, public_url, filename


async def delete_drive_file(
    file_id: str,
    token: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Delete a file from Google Drive. Used to clean up on insert failure."""

    async def _do_delete(c: httpx.AsyncClient) -> None:
        resp = await c.delete(
            f"{_DRIVE_BASE_URL}/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"supportsAllDrives": "true"},
        )
        resp.raise_for_status()

    if client is not None:
        await _do_delete(client)
    else:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            await _do_delete(c)
