"""Shared file I/O for resolving FileInput to raw bytes.

Tools that accept file uploads use this module to normalise
``FileFromUrl`` and ``FileFromBytes`` into a common
``(bytes, filename, mime_type)`` tuple.
"""

from __future__ import annotations

from email.message import Message
from urllib.parse import unquote, urlparse

import httpx

from apron_tools.types import FileFromBytes, FileFromUrl, FileInput

_TIMEOUT = 60.0


async def resolve_file_input(file: FileInput) -> tuple[bytes, str, str]:
    """Resolve a FileInput to raw bytes, filename, and MIME type.

    For ``FileFromBytes``: returns the data directly.
    For ``FileFromUrl``: downloads the URL and infers filename/MIME type
    from the response headers when not explicitly provided.

    .. warning:: Security consideration

        When resolving a ``FileFromUrl``, the URL is fetched as-is with
        no network filtering or size limits. See the warning on
        ``FileFromUrl`` for details. Callers exposing this to untrusted
        input should validate URLs before passing them here.

    Args:
        file: A ``FileFromUrl`` or ``FileFromBytes`` instance.

    Returns:
        A tuple of (bytes, filename, mime_type).

    Raises:
        httpx.HTTPStatusError: If the URL download fails.
    """
    if isinstance(file, FileFromBytes):
        return file.data, file.filename, file.mime_type

    return await _download_url(file)


async def _download_url(file: FileFromUrl) -> tuple[bytes, str, str]:
    """Download a file from a URL and infer metadata from the response."""
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(str(file.url))
        resp.raise_for_status()

    data = resp.content

    # Infer filename from explicit override, Content-Disposition, or URL path.
    filename = file.filename
    if not filename:
        disposition = resp.headers.get("content-disposition", "")
        if disposition:
            msg = Message()
            msg["content-disposition"] = disposition
            # Prefer RFC 5987 filename* over plain filename.
            raw = msg.get_param("filename*") or msg.get_filename() or ""
            filename = str(raw) if raw else ""
        if not filename:
            filename = unquote(urlparse(str(file.url)).path.rsplit("/", 1)[-1]) or "download"

    # Infer MIME type from explicit override or Content-Type header.
    mime_type = file.mime_type
    if not mime_type:
        mime_type = resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip()

    return data, filename, mime_type
