"""Tests for shared OneDrive file operations."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from apron_tools.providers.microsoft.onedrive import (
    FileTooLargeError,
    download_file,
    get_file_metadata,
    search_files,
    upload_file,
)
from apron_tools.providers.microsoft.onedrive import _shared as onedrive_shared

TESTDATA_DIR = Path(__file__).parent / "powerpoint" / "testdata"
_LIMIT = 1024 * 1024
_TOKEN = "test_oauth_token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# search_files
# ---------------------------------------------------------------------------


class TestSearchFiles:
    async def test_search_api_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='ppt')",
            json=_load_json("search_files.json"),
        )

        result = await search_files(_TOKEN, {".pptx", ".ppt", ".pptm"}, base_url=_GRAPH_BASE)

        assert len(result) == 2
        assert result[0]["name"] == "Q4 Review.pptx"
        assert result[1]["id"] == "pptx-002"

    async def test_max_results(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='ppt')",
            json=_load_json("search_files.json"),
        )

        result = await search_files(_TOKEN, {".pptx", ".ppt", ".pptm"}, max_results=1, base_url=_GRAPH_BASE)

        assert len(result) == 1

    async def test_fallback_to_folder_exploration(self, httpx_mock: HTTPXMock) -> None:
        """When search API fails, falls back to recursive folder exploration."""
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='ppt')",
            status_code=400,
            text="Search not supported",
        )
        httpx_mock.add_response(
            url=re.compile(rf"^{re.escape(_GRAPH_BASE)}/me/drive/root/children"),
            json=_load_json("folder_children.json"),
        )
        httpx_mock.add_response(
            url=re.compile(rf"^{re.escape(_GRAPH_BASE)}/me/drive/items/folder-001/children"),
            json={"value": []},
        )

        result = await search_files(_TOKEN, {".pptx", ".ppt", ".pptm"}, base_url=_GRAPH_BASE)

        assert len(result) == 1
        assert result[0]["name"] == "Team Update.pptx"

    async def test_empty_results_no_fallback(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='ppt')",
            json={"value": []},
        )

        result = await search_files(_TOKEN, {".pptx", ".ppt", ".pptm"}, base_url=_GRAPH_BASE)

        assert result == []


# ---------------------------------------------------------------------------
# download_file
# ---------------------------------------------------------------------------


class TestDownloadFile:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001/content",
            content=b"fake-pptx-bytes",
        )

        result = await download_file(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)

        assert result == b"fake-pptx-bytes"

    async def test_not_found(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/bad-id/content",
            status_code=404,
            text="Not Found",
        )

        try:
            await download_file(_TOKEN, "bad-id", base_url=_GRAPH_BASE)
            raise AssertionError("Expected HTTPStatusError")
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 404

    async def test_requests_uncompressed_content(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001/content",
            match_headers={"Accept-Encoding": "identity"},
            content=b"fake-pptx-bytes",
        )

        result = await download_file(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)

        assert result == b"fake-pptx-bytes"

    async def test_accepts_file_at_limit(self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(onedrive_shared, "_MAX_DOWNLOAD_BYTES", _LIMIT)
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001/content",
            content=b"x" * _LIMIT,
        )

        result = await download_file(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)

        assert len(result) == _LIMIT

    async def test_rejects_declared_size_over_limit(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(onedrive_shared, "_MAX_DOWNLOAD_BYTES", _LIMIT)
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001/content",
            content=b"x" * (_LIMIT + 1),
        )

        with pytest.raises(FileTooLargeError, match="1 MB download limit"):
            await download_file(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)

    async def test_rejects_streamed_size_over_limit_without_content_length(
        self, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(onedrive_shared, "_MAX_DOWNLOAD_BYTES", _LIMIT)
        chunk = b"x" * (_LIMIT // 2 + 1)
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001/content",
            stream=IteratorStream([chunk, chunk]),
        )

        with pytest.raises(FileTooLargeError):
            await download_file(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)


# ---------------------------------------------------------------------------
# upload_file
# ---------------------------------------------------------------------------


class TestUploadFile:
    async def test_upload_to_root(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/report.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await upload_file(
            _TOKEN,
            b"pptx-content",
            "report.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            base_url=_GRAPH_BASE,
        )

        assert result["id"] == "pptx-004"
        assert result["name"] == "New Presentation.pptx"

    async def test_upload_to_folder(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Documents/report.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await upload_file(
            _TOKEN,
            b"pptx-content",
            "report.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "Documents",
            base_url=_GRAPH_BASE,
        )

        assert result["id"] == "pptx-004"

    async def test_upload_error(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/test.pptx:/content",
            status_code=403,
            text="Forbidden",
        )

        try:
            await upload_file(
                _TOKEN,
                b"data",
                "test.pptx",
                "application/octet-stream",
                base_url=_GRAPH_BASE,
            )
            raise AssertionError("Expected HTTPStatusError")
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 403


# ---------------------------------------------------------------------------
# get_file_metadata
# ---------------------------------------------------------------------------


class TestGetFileMetadata:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/pptx-001",
            json=_load_json("file_metadata.json"),
        )

        result = await get_file_metadata(_TOKEN, "pptx-001", base_url=_GRAPH_BASE)

        assert result["id"] == "pptx-001"
        assert result["name"] == "Q4 Review.pptx"
        assert result["webUrl"] == "https://onedrive.live.com/view/pptx-001"

    async def test_not_found(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/bad-id",
            status_code=404,
            text="Not Found",
        )

        try:
            await get_file_metadata(_TOKEN, "bad-id", base_url=_GRAPH_BASE)
            raise AssertionError("Expected HTTPStatusError")
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 404
