"""Tests for bounded HTTP downloads."""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from apron_tools._http import FileTooLargeError, download

_URL = "https://files.example.com/report.bin"
_LIMIT = 1024 * 1024


async def _download(max_bytes: int = _LIMIT) -> bytes:
    """Download the test URL with a fresh client."""
    async with httpx.AsyncClient() as client:
        return (await download(client, _URL, headers={"Authorization": "Bearer t"}, max_bytes=max_bytes)).content


class TestDownload:
    async def test_returns_body_and_content_type(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, content=b"hello", headers={"content-type": "text/plain; charset=latin-1"})

        async with httpx.AsyncClient() as client:
            result = await download(client, _URL, headers={}, max_bytes=_LIMIT)

        assert result.content == b"hello"
        assert result.content_type == "text/plain; charset=latin-1"
        assert result.encoding == "latin-1"

    async def test_sends_caller_headers_and_requests_uncompressed_content(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=_URL,
            match_headers={"Authorization": "Bearer t", "Accept-Encoding": "identity"},
            content=b"hello",
        )

        assert await _download() == b"hello"

    async def test_accepts_body_at_limit(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, content=b"x" * _LIMIT)

        assert len(await _download()) == _LIMIT

    async def test_rejects_declared_size_over_limit(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, content=b"x" * (_LIMIT + 1))

        with pytest.raises(FileTooLargeError, match="1 MB download limit"):
            await _download()

    async def test_rejects_streamed_size_over_limit_without_content_length(self, httpx_mock: HTTPXMock) -> None:
        chunk = b"x" * (_LIMIT // 2 + 1)
        httpx_mock.add_response(url=_URL, stream=IteratorStream([chunk, chunk]))

        with pytest.raises(FileTooLargeError):
            await _download()

    async def test_ignores_content_length_that_is_not_a_number(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, stream=IteratorStream([b"hello"]), headers={"content-length": "lots"})

        assert await _download() == b"hello"

    async def test_raises_for_error_status(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, status_code=403)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await _download()

        assert exc_info.value.response.status_code == 403
