"""HTTP downloads of untrusted content, bounded by a size limit."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class FileTooLargeError(Exception):
    """A file is larger than the download size limit."""

    def __init__(self, limit_bytes: int) -> None:
        """Build the error for the given limit.

        Args:
            limit_bytes: The download size limit in bytes.
        """
        super().__init__(f"The file is larger than the {limit_bytes // (1024 * 1024)} MB download limit.")


@dataclass(frozen=True)
class Download:
    """A downloaded response body and the headers that describe it."""

    content: bytes
    content_type: str
    encoding: str


async def download(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    max_bytes: int,
) -> Download:
    """Send a GET request and read the response body, up to a size limit.

    The limit bounds the memory that the body uses, because the body is untrusted.
    Redirects are followed up to the client's redirect limit, and their bodies are never read.

    Args:
        client: The client that sends the request.
        url: The URL to download.
        headers: The request headers.
        max_bytes: The largest body to accept, in bytes.

    Returns:
        The body, its content type, and its text encoding.

    Raises:
        httpx.HTTPError: If the request fails, the response status is not a success, or the body is compressed.
        httpx.TooManyRedirects: If the redirects exceed the client's redirect limit.
        FileTooLargeError: If the body is larger than the limit.
    """
    # Without compression, Content-Length is the real size and each chunk stays small.
    request = client.build_request("GET", url, headers={**headers, "Accept-Encoding": "identity"})
    for _ in range(client.max_redirects + 1):
        resp = await client.send(request, stream=True, follow_redirects=False)
        try:
            if resp.next_request is None:
                return await _read_body(resp, max_bytes)
            request = resp.next_request
        finally:
            await resp.aclose()
    raise httpx.TooManyRedirects("The download was redirected too many times.", request=request)


async def _read_body(resp: httpx.Response, max_bytes: int) -> Download:
    """Read a streamed final response, up to a size limit."""
    resp.raise_for_status()
    if resp.headers.get("content-encoding", "identity").strip().lower() not in {"", "identity"}:
        raise httpx.DecodingError("The server sent a compressed file, which the download does not accept.")
    declared = resp.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise FileTooLargeError(max_bytes)
    data = bytearray()
    async for chunk in resp.aiter_bytes():
        if len(data) + len(chunk) > max_bytes:
            raise FileTooLargeError(max_bytes)
        data += chunk
    return Download(
        content=bytes(data),
        content_type=resp.headers.get("content-type", ""),
        encoding=resp.encoding or "utf-8",
    )
