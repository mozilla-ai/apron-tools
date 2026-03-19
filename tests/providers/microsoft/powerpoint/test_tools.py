"""Tests for Microsoft PowerPoint tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.powerpoint.presentation import build_pptx
from apron_tools.providers.microsoft.powerpoint.tools import (
    microsoft_powerpoint_add_slide,
    microsoft_powerpoint_create_presentation,
    microsoft_powerpoint_explore_presentations,
    microsoft_powerpoint_read_presentation,
    microsoft_powerpoint_update_slide_text,
    microsoft_powerpoint_upload_to_onedrive,
)
from apron_tools.providers.microsoft.powerpoint.types import (
    AddSlideParams,
    AddSlideResult,
    CreatePresentationParams,
    CreatePresentationResult,
    ExplorePresentationsParams,
    ExplorePresentationsResult,
    ReadPresentationParams,
    ReadPresentationResult,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UploadToOnedriveParams,
    UploadToOnedriveResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_ITEM_ID = "pptx-001"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# explore_presentations
# ---------------------------------------------------------------------------


class TestExplorePresentations:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='ppt')",
            json=_load_json("search_files.json"),
        )

        result = await microsoft_powerpoint_explore_presentations(
            ExplorePresentationsParams(),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, ExplorePresentationsResult)
        assert result.success is True
        assert len(result.presentations) == 2
        assert result.presentations[0].name == "Q4 Review.pptx"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
        )

        result = await microsoft_powerpoint_explore_presentations(
            ExplorePresentationsParams(),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_explore_presentations._tool_definition
        assert defn.name == "microsoft_powerpoint_explore_presentations"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_presentation
# ---------------------------------------------------------------------------


class TestReadPresentation:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        pptx_bytes = build_pptx("Test Title")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=pptx_bytes,
        )

        result = await microsoft_powerpoint_read_presentation(
            ReadPresentationParams(presentation_id=_ITEM_ID),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, ReadPresentationResult)
        assert result.success is True
        assert result.name == "Q4 Review.pptx"
        assert len(result.slides) == 1
        assert result.slides[0].title == "Test Title"

    async def test_download_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_powerpoint_read_presentation(
            ReadPresentationParams(presentation_id=_ITEM_ID),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_read_presentation._tool_definition
        assert defn.name == "microsoft_powerpoint_read_presentation"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# create_presentation
# ---------------------------------------------------------------------------


class TestCreatePresentation:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_create_presentation(
            CreatePresentationParams(name="Report", title="Q4 Report"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, CreatePresentationResult)
        assert result.success is True
        assert result.presentation_id == "pptx-004"

    async def test_filename_extension_added(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_create_presentation(
            CreatePresentationParams(name="Report"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_filename_extension_preserved(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Deck.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_create_presentation(
            CreatePresentationParams(name="Deck.pptx"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_upload_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.pptx:/content",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_powerpoint_create_presentation(
            CreatePresentationParams(name="Report"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_folder_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Documents/Report.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_create_presentation(
            CreatePresentationParams(name="Report", folder_path="Documents"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_create_presentation._tool_definition
        assert defn.name == "microsoft_powerpoint_create_presentation"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# add_slide
# ---------------------------------------------------------------------------


class TestAddSlide:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        pptx_bytes = build_pptx("Initial")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=pptx_bytes,
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            json=_load_json("upload_response.json"),
            method="PUT",
        )

        result = await microsoft_powerpoint_add_slide(
            AddSlideParams(
                presentation_id=_ITEM_ID,
                layout="title_and_content",
                title="New Slide",
                content="Some content",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, AddSlideResult)
        assert result.success is True
        assert result.slide_count == 2
        assert result.layout == "title_and_content"
        assert result.name == "Q4 Review.pptx"

    async def test_download_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_powerpoint_add_slide(
            AddSlideParams(presentation_id=_ITEM_ID),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_add_slide._tool_definition
        assert defn.name == "microsoft_powerpoint_add_slide"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# update_slide_text
# ---------------------------------------------------------------------------


class TestUpdateSlideText:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        pptx_bytes = build_pptx("Original")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=pptx_bytes,
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            json=_load_json("upload_response.json"),
            method="PUT",
        )

        result = await microsoft_powerpoint_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_ITEM_ID,
                slide_number=1,
                text="Updated Title",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, UpdateSlideTextResult)
        assert result.success is True
        assert result.slide_number == 1
        assert result.shape_name != ""

    async def test_slide_out_of_range(self, httpx_mock: HTTPXMock) -> None:
        pptx_bytes = build_pptx("Title")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=pptx_bytes,
        )

        result = await microsoft_powerpoint_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_ITEM_ID,
                slide_number=99,
                text="Bad",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert "out of range" in result.error

    async def test_download_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_powerpoint_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_ITEM_ID,
                slide_number=1,
                text="text",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_update_slide_text._tool_definition
        assert defn.name == "microsoft_powerpoint_update_slide_text"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# upload_to_onedrive
# ---------------------------------------------------------------------------


class TestUploadToOnedrive:
    async def test_bytes_upload(self, httpx_mock: HTTPXMock) -> None:
        import base64

        data_b64 = base64.b64encode(b"fake-pptx").decode()
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/test.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_upload_to_onedrive(
            UploadToOnedriveParams(
                file={
                    "type": "bytes",
                    "data": data_b64,
                    "filename": "test.pptx",
                    "mime_type": "application/octet-stream",
                },
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, UploadToOnedriveResult)
        assert result.success is True
        assert result.file_id == "pptx-004"

    async def test_url_upload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://example.com/deck.pptx",
            content=b"remote-pptx-bytes",
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/deck.pptx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_powerpoint_upload_to_onedrive(
            UploadToOnedriveParams(
                file={"type": "url", "url": "https://example.com/deck.pptx"},
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True
        assert result.file_id == "pptx-004"

    async def test_url_download_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://example.com/bad.pptx",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_powerpoint_upload_to_onedrive(
            UploadToOnedriveParams(
                file={"type": "url", "url": "https://example.com/bad.pptx"},
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert "Download failed" in result.error

    async def test_upload_error(self, httpx_mock: HTTPXMock) -> None:
        import base64

        data_b64 = base64.b64encode(b"data").decode()
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/test.pptx:/content",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_powerpoint_upload_to_onedrive(
            UploadToOnedriveParams(
                file={
                    "type": "bytes",
                    "data": data_b64,
                    "filename": "test.pptx",
                    "mime_type": "application/octet-stream",
                },
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_powerpoint_upload_to_onedrive._tool_definition
        assert defn.name == "microsoft_powerpoint_upload_to_onedrive"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_powerpoint"
        assert "Files.ReadWrite" in defn.scopes
