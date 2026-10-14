"""Tests for bounded HTTP downloads."""

from __future__ import annotations

import gzip
from collections.abc import Iterator

import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from apron_tools._http import CompressedResponseError, DownloadError, FileTooLargeError, download

_URL = "https://files.example.com/report.bin"
_CDN_URL = "https://cdn.example.net/report.bin"
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

    async def test_accepts_body_declared_as_uncompressed(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, content=b"hello", headers={"content-encoding": "identity"})

        assert await _download() == b"hello"

    async def test_rejects_compressed_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, content=gzip.compress(b"hello"), headers={"content-encoding": "gzip"})

        with pytest.raises(CompressedResponseError, match="compressed"):
            await _download()

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


class TestDownloadErrors:
    def test_refusals_share_a_base(self) -> None:
        assert issubclass(CompressedResponseError, DownloadError)
        assert issubclass(FileTooLargeError, DownloadError)

    def test_file_too_large_reports_a_limit_below_one_megabyte(self) -> None:
        assert str(FileTooLargeError(512 * 1024)) == "The file is larger than the 0.5 MB download limit."


class TestRedirects:
    async def test_follows_redirect_without_reading_its_body(self, httpx_mock: HTTPXMock) -> None:
        redirect_body_read = False

        def redirect_body() -> Iterator[bytes]:
            nonlocal redirect_body_read
            redirect_body_read = True
            yield b"moved"

        httpx_mock.add_response(
            url=_URL,
            status_code=302,
            headers={"location": _CDN_URL},
            stream=IteratorStream(redirect_body()),
        )
        httpx_mock.add_response(url=_CDN_URL, content=b"hello")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            result = await download(client, _URL, headers={}, max_bytes=_LIMIT)

        assert result.content == b"hello"
        assert not redirect_body_read

    async def test_follows_redirect_when_client_does_not(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, status_code=302, headers={"location": _CDN_URL})
        httpx_mock.add_response(url=_CDN_URL, content=b"hello")

        assert await _download() == b"hello"

    async def test_keeps_authorization_on_same_origin_redirect(self, httpx_mock: HTTPXMock) -> None:
        moved = "https://files.example.com/moved.bin"
        httpx_mock.add_response(url=_URL, status_code=302, headers={"location": "/moved.bin"})
        httpx_mock.add_response(url=moved, match_headers={"Authorization": "Bearer t"}, content=b"hello")

        assert await _download() == b"hello"

    async def test_drops_authorization_on_cross_origin_redirect(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, status_code=302, headers={"location": _CDN_URL})
        httpx_mock.add_response(url=_CDN_URL, content=b"hello")

        await _download()

        redirected = httpx_mock.get_request(url=_CDN_URL)
        assert redirected is not None
        assert "Authorization" not in redirected.headers
        assert redirected.headers["Accept-Encoding"] == "identity"

    async def test_rejects_too_many_redirects(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(url=_URL, status_code=302, headers={"location": _URL}, is_reusable=True)

        async with httpx.AsyncClient(max_redirects=2) as client:
            with pytest.raises(httpx.TooManyRedirects, match="redirected too many times"):
                await download(client, _URL, headers={}, max_bytes=_LIMIT)

        assert len(httpx_mock.get_requests()) == 3
