"""Tests for the shared file I/O module."""

from __future__ import annotations

import base64

import pytest

from apron_tools.fileio import resolve_file_input
from apron_tools.types import FileFromBytes, FileFromUrl


class TestResolveFileFromBytes:
    async def test_returns_data_directly(self):
        b64 = base64.b64encode(b"hello world").decode()
        file = FileFromBytes(data=b64, filename="test.txt", mime_type="text/plain")
        data, filename, mime_type = await resolve_file_input(file)
        assert data == b"hello world"
        assert filename == "test.txt"
        assert mime_type == "text/plain"


class TestResolveFileFromUrl:
    async def test_downloads_and_returns(self, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/report.pdf",
            content=b"pdf-bytes",
            headers={"content-type": "application/pdf"},
        )
        file = FileFromUrl(url="https://example.com/report.pdf")
        data, filename, mime_type = await resolve_file_input(file)
        assert data == b"pdf-bytes"
        assert filename == "report.pdf"
        assert mime_type == "application/pdf"

    async def test_explicit_overrides(self, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/file",
            content=b"data",
            headers={"content-type": "text/html"},
        )
        file = FileFromUrl(url="https://example.com/file", filename="custom.bin", mime_type="application/octet-stream")
        data, filename, mime_type = await resolve_file_input(file)
        assert filename == "custom.bin"
        assert mime_type == "application/octet-stream"

    async def test_infers_filename_from_content_disposition(self, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/download",
            content=b"data",
            headers={
                "content-type": "application/pdf",
                "content-disposition": 'attachment; filename="quarterly.pdf"',
            },
        )
        file = FileFromUrl(url="https://example.com/download")
        _, filename, _ = await resolve_file_input(file)
        assert filename == "quarterly.pdf"

    async def test_fallback_filename(self, httpx_mock):
        httpx_mock.add_response(
            url="https://example.com/",
            content=b"data",
            headers={"content-type": "application/octet-stream"},
        )
        file = FileFromUrl(url="https://example.com/")
        _, filename, _ = await resolve_file_input(file)
        assert filename == "download"

    async def test_download_error_raises(self, httpx_mock):
        import httpx

        httpx_mock.add_response(url="https://example.com/missing", status_code=404)
        file = FileFromUrl(url="https://example.com/missing")
        with pytest.raises(httpx.HTTPStatusError):
            await resolve_file_input(file)
