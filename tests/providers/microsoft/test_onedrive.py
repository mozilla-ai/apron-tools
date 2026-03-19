"""Tests for shared OneDrive file operations."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.onedrive import (
    download_file,
    get_file_metadata,
    search_files,
    upload_file,
)

TESTDATA_DIR = Path(__file__).parent / "powerpoint" / "testdata"
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
