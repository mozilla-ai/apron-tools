"""Tests for Google Slides tool functions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pytest_httpx import HTTPXMock

from apron_tools.providers.google.slides.tools import (
    google_slides_add_slide,
    google_slides_copy_presentation,
    google_slides_create_presentation,
    google_slides_duplicate_slide,
    google_slides_format_text,
    google_slides_insert_element,
    google_slides_list_presentations,
    google_slides_read_presentation,
    google_slides_update_slide_text,
    google_slides_update_table_cell,
)
from apron_tools.providers.google.slides.types import (
    AddSlideParams,
    AddSlideResult,
    CopyPresentationParams,
    CopyPresentationResult,
    CreatePresentationParams,
    CreatePresentationResult,
    DuplicateSlideParams,
    DuplicateSlideResult,
    FormatTextParams,
    FormatTextResult,
    InsertElementParams,
    InsertElementResult,
    ListPresentationsParams,
    ListPresentationsResult,
    ReadPresentationParams,
    ReadPresentationResult,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UpdateTableCellParams,
    UpdateTableCellResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_SLIDES_BASE = "https://slides.googleapis.com/v1/presentations"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"
_PRES_ID = "pres-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_presentations
# ---------------------------------------------------------------------------


class TestListPresentations:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}?q=mimeType%3D%27application%2Fvnd.google-apps.presentation%27&pageSize=20&fields=files%28id%2Cname%2CcreatedTime%2CmodifiedTime%29&orderBy=modifiedTime+desc&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=allDrives",
            json=_load_json("list_presentations.json"),
        )

        result = await google_slides_list_presentations(ListPresentationsParams(), token=_TOKEN)

        assert isinstance(result, ListPresentationsResult)
        assert result.success is True
        assert len(result.files) == 2
        assert result.files[0].name == "Q1 Review"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_slides_list_presentations(ListPresentationsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_list_presentations._tool_definition
        assert defn.name == "google_slides_list_presentations"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# create_presentation
# ---------------------------------------------------------------------------


class TestCreatePresentation:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=_SLIDES_BASE,
            json=_load_json("create_presentation.json"),
        )

        result = await google_slides_create_presentation(
            CreatePresentationParams(title="Q1 Review"),
            token=_TOKEN,
        )

        assert isinstance(result, CreatePresentationResult)
        assert result.success is True
        assert result.presentation_id == _PRES_ID
        assert result.title == "Q1 Review"
        assert result.slide_count == 1

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_create_presentation(
            CreatePresentationParams(title="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_create_presentation._tool_definition
        assert defn.name == "google_slides_create_presentation"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# copy_presentation
# ---------------------------------------------------------------------------


class TestCopyPresentation:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_PRES_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_presentation_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_PRES_ID}/copy?supportsAllDrives=true",
            json=_load_json("copy_presentation.json"),
        )

        result = await google_slides_copy_presentation(
            CopyPresentationParams(
                presentation_id=_PRES_ID,
                new_title="Copy of Q1 Review",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CopyPresentationResult)
        assert result.success is True
        assert result.id == "pres-003"
        assert result.name == "Copy of Q1 Review"
        assert result.original_name == "Q1 Review"

    async def test_meta_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_slides_copy_presentation(
            CopyPresentationParams(presentation_id="bad_id", new_title="Copy"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_copy_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_PRES_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_presentation_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_PRES_ID}/copy?supportsAllDrives=true",
            status_code=403,
            text="Forbidden",
        )

        result = await google_slides_copy_presentation(
            CopyPresentationParams(
                presentation_id=_PRES_ID,
                new_title="Copy",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_copy_presentation._tool_definition
        assert defn.name == "google_slides_copy_presentation"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# read_presentation
# ---------------------------------------------------------------------------


class TestReadPresentation:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation.json"),
        )

        result = await google_slides_read_presentation(
            ReadPresentationParams(presentation_id=_PRES_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadPresentationResult)
        assert result.success is True
        assert result.title == "Q1 Review"
        assert result.slide_count == 2
        assert len(result.slides) == 2
        assert result.slides[0].object_id == "slide-001"
        assert "Q1 Review" in result.slides[0].text_content

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_slides_read_presentation(
            ReadPresentationParams(presentation_id="bad_id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_read_presentation._tool_definition
        assert defn.name == "google_slides_read_presentation"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# add_slide
# ---------------------------------------------------------------------------


class TestAddSlide:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_add_slide.json"),
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID),
            token=_TOKEN,
        )

        assert isinstance(result, AddSlideResult)
        assert result.success is True
        assert result.slide_id == "slide-003"
        assert result.presentation_id == _PRES_ID

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id="bad_id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_add_slide._tool_definition
        assert defn.name == "google_slides_add_slide"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# update_slide_text
# ---------------------------------------------------------------------------


class TestUpdateSlideText:
    async def test_success_existing_shape(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
                text="Updated text",
                shape_id="elem-001",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateSlideTextResult)
        assert result.success is True
        assert result.shape_id == "elem-001"

    async def test_success_new_textbox(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        with patch("apron_tools.providers.google.slides.tools.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "aabbccdd11223344"
            result = await google_slides_update_slide_text(
                UpdateSlideTextParams(
                    presentation_id=_PRES_ID,
                    slide_id="slide-001",
                    text="New text",
                ),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.shape_id == "textbox_aabbccdd"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id="bad_id",
                slide_id="slide-001",
                text="test",
                shape_id="elem-001",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_update_slide_text._tool_definition
        assert defn.name == "google_slides_update_slide_text"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# duplicate_slide
# ---------------------------------------------------------------------------


class TestDuplicateSlide:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_duplicate.json"),
        )

        result = await google_slides_duplicate_slide(
            DuplicateSlideParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, DuplicateSlideResult)
        assert result.success is True
        assert result.new_slide_id == "slide-004"
        assert result.presentation_id == _PRES_ID

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_slides_duplicate_slide(
            DuplicateSlideParams(
                presentation_id="bad_id",
                slide_id="slide-001",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_duplicate_slide._tool_definition
        assert defn.name == "google_slides_duplicate_slide"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# insert_element
# ---------------------------------------------------------------------------


class TestInsertElement:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_insert_element(
            InsertElementParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
                shape_type="RECTANGLE",
                text="Hello",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, InsertElementResult)
        assert result.success is True
        assert result.element_id.startswith("shape_")

    async def test_success_no_text(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_insert_element(
            InsertElementParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
            ),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_insert_element(
            InsertElementParams(
                presentation_id="bad_id",
                slide_id="slide-001",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_insert_element._tool_definition
        assert defn.name == "google_slides_insert_element"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# update_table_cell
# ---------------------------------------------------------------------------


class TestUpdateTableCell:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_update_table_cell(
            UpdateTableCellParams(
                presentation_id=_PRES_ID,
                table_id="table-001",
                row=0,
                column=1,
                text="Revenue",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateTableCellResult)
        assert result.success is True
        assert result.table_id == "table-001"
        assert result.row == 0
        assert result.column == 1

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_update_table_cell(
            UpdateTableCellParams(
                presentation_id="bad_id",
                table_id="table-001",
                row=0,
                column=0,
                text="test",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_update_table_cell._tool_definition
        assert defn.name == "google_slides_update_table_cell"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes


# ---------------------------------------------------------------------------
# format_text
# ---------------------------------------------------------------------------


class TestFormatText:
    async def test_success_bold(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_format_text(
            FormatTextParams(
                presentation_id=_PRES_ID,
                object_id="elem-001",
                bold=True,
            ),
            token=_TOKEN,
        )

        assert isinstance(result, FormatTextResult)
        assert result.success is True
        assert result.object_id == "elem-001"

    async def test_success_full_style(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_format_text(
            FormatTextParams(
                presentation_id=_PRES_ID,
                object_id="elem-001",
                bold=True,
                italic=True,
                font_size=24,
                foreground_color="#FF0000",
                start_index=0,
                end_index=10,
            ),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_no_options_returns_error(self) -> None:
        result = await google_slides_format_text(
            FormatTextParams(
                presentation_id=_PRES_ID,
                object_id="elem-001",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "No formatting options" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_slides_format_text(
            FormatTextParams(
                presentation_id="bad_id",
                object_id="elem-001",
                bold=True,
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_format_text._tool_definition
        assert defn.name == "google_slides_format_text"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes
