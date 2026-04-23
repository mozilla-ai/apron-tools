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
    google_slides_insert_image,
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
    InsertImageParams,
    InsertImageResult,
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
    async def test_success_uses_named_layout_id_when_available(self, httpx_mock: HTTPXMock) -> None:
        # The tool prefers matching the requested layout to an object in the
        # presentation's layouts and referencing it by layoutId.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_add_slide.json"),
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID, layout="TITLE_AND_BODY"),
            token=_TOKEN,
        )

        assert isinstance(result, AddSlideResult)
        assert result.success is True
        assert result.slide_id == "slide-003"
        assert result.presentation_id == _PRES_ID
        assert result.fallback_reason is None

        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        create_slide = body["requests"][0]["createSlide"]
        assert create_slide["slideLayoutReference"] == {"layoutId": "layout-title-and-body"}

    async def test_falls_back_to_predefined_layout_when_not_in_presentation(self, httpx_mock: HTTPXMock) -> None:
        # When the presentation does not expose a matching named layout, the
        # tool falls back to the predefined layout enum.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_add_slide.json"),
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID, layout="TITLE_ONLY"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.fallback_reason is not None
        assert "TITLE_ONLY" in result.fallback_reason

        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        create_slide = body["requests"][0]["createSlide"]
        assert create_slide["slideLayoutReference"] == {"predefinedLayout": "TITLE_ONLY"}

    async def test_blank_layout_does_not_record_fallback(self, httpx_mock: HTTPXMock) -> None:
        # Requesting the default BLANK layout should always resolve cleanly
        # without any fallback note even when read_presentation returns minimal
        # layout metadata.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_add_slide.json"),
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.fallback_reason is None

    async def test_layout_case_insensitive_match(self, httpx_mock: HTTPXMock) -> None:
        # Layout resolution is case-insensitive to match the Slides API's
        # convention of uppercase predefined layouts.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_add_slide.json"),
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID, layout="title_and_body"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.fallback_reason is None
        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        create_slide = body["requests"][0]["createSlide"]
        assert create_slide["slideLayoutReference"] == {"layoutId": "layout-title-and-body"}

    async def test_read_presentation_error_propagates(self, httpx_mock: HTTPXMock) -> None:
        # If the initial read fails, the tool surfaces the error rather than
        # continuing with incomplete information.
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id="bad_id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_batch_update_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            status_code=400,
            text="Bad Request",
        )

        result = await google_slides_add_slide(
            AddSlideParams(presentation_id=_PRES_ID),
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
    async def test_success_existing_shape_with_text(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
                text="Updated text",
                shape_id="shape-with-text",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateSlideTextResult)
        assert result.success is True
        assert result.shape_id == "shape-with-text"
        assert result.fallback_reason is None

        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        requests = body["requests"]
        assert len(requests) == 2
        assert "deleteText" in requests[0]
        assert requests[1]["insertText"]["text"] == "Updated text"

    async def test_skips_delete_text_for_empty_shape(self, httpx_mock: HTTPXMock) -> None:
        # The Slides API rejects deleteText when the shape has no text. The
        # tool must detect that and send only an insertText request.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
                text="Fresh text",
                shape_id="shape-empty",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.shape_id == "shape-empty"

        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        requests = body["requests"]
        assert len(requests) == 1
        assert "deleteText" not in requests[0]
        assert requests[0]["insertText"]["text"] == "Fresh text"

    async def test_missing_shape_falls_back_to_new_textbox(self, httpx_mock: HTTPXMock) -> None:
        # If the caller-supplied shape_id is not present on the slide, the
        # tool creates a replacement text box and notes the fallback.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            json=_load_json("batch_update_generic.json"),
        )

        with patch("apron_tools.providers.google.slides.tools.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "deadbeef11223344"  # pragma: allowlist secret
            result = await google_slides_update_slide_text(
                UpdateSlideTextParams(
                    presentation_id=_PRES_ID,
                    slide_id="slide-001",
                    text="Replacement",
                    shape_id="shape-missing",
                ),
                token=_TOKEN,
            )

        assert result.success is True
        assert result.shape_id == "textbox_deadbeef"
        assert result.fallback_reason is not None
        assert "shape-missing" in result.fallback_reason

        batch_req = next(r for r in httpx_mock.get_requests() if r.url.path.endswith(":batchUpdate"))
        body = json.loads(batch_req.content)
        requests = body["requests"]
        assert len(requests) == 2
        assert requests[0]["createShape"]["objectId"] == "textbox_deadbeef"
        assert requests[1]["insertText"]["objectId"] == "textbox_deadbeef"

    async def test_missing_slide_returns_error(self, httpx_mock: HTTPXMock) -> None:
        # An unknown slide_id must short-circuit before the batchUpdate call.
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_PRES_ID,
                slide_id="slide-does-not-exist",
                text="test",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "slide-does-not-exist" in result.error

    async def test_success_new_textbox(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
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

    async def test_read_error_propagates(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

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
        assert "404" in result.error

    async def test_batch_update_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}",
            json=_load_json("read_presentation_with_layouts.json"),
        )
        httpx_mock.add_response(
            url=f"{_SLIDES_BASE}/{_PRES_ID}:batchUpdate",
            status_code=400,
            text="Bad Request",
        )

        result = await google_slides_update_slide_text(
            UpdateSlideTextParams(
                presentation_id=_PRES_ID,
                slide_id="slide-001",
                text="test",
                shape_id="shape-with-text",
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


# ---------------------------------------------------------------------------
# insert_image
# ---------------------------------------------------------------------------


class TestGoogleSlidesInsertImage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        img = base64.b64encode(b"\x89PNG\r\n\x1a\nfakedata").decode()

        # Step 1: Drive upload (returns webContentLink).
        httpx_mock.add_response(
            json={
                "id": "drive-img-001",
                "webContentLink": "https://drive.google.com/uc?id=drive-img-001&export=download",
            }
        )
        # Step 2: Permission set.
        httpx_mock.add_response(json={"id": "perm-001"})
        # Step 3: batchUpdate createImage.
        httpx_mock.add_response(json={"presentationId": _PRES_ID, "replies": [{}]})

        params = InsertImageParams(
            presentation_id=_PRES_ID,
            slide_id="slide-001",
            file=FileFromBytes(data=img, filename="chart.png", mime_type="image/png"),
        )
        result = await google_slides_insert_image(params, token=_TOKEN)

        assert isinstance(result, InsertImageResult)
        assert result.success is True
        assert result.presentation_id == _PRES_ID
        assert result.filename == "chart.png"
        assert result.drive_file_id == "drive-img-001"
        assert result.image_id.startswith("image_")
        assert "chart.png" in str(result)

    async def test_non_image_rejected(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        params = InsertImageParams(
            presentation_id=_PRES_ID,
            slide_id="slide-001",
            file=FileFromBytes(
                data=base64.b64encode(b"text").decode(),
                filename="notes.txt",
                mime_type="text/plain",
            ),
        )
        result = await google_slides_insert_image(params, token=_TOKEN)

        assert result.success is False
        assert "image" in result.error.lower()

    async def test_batch_update_error_cleans_up_drive_file(self, httpx_mock: HTTPXMock) -> None:
        import base64

        from apron_tools.types import FileFromBytes

        img = base64.b64encode(b"\x89PNGfake").decode()

        # Drive upload and permission succeed.
        httpx_mock.add_response(json={"id": "drive-img-001"})
        httpx_mock.add_response(json={"id": "perm-001"})
        # batchUpdate fails.
        httpx_mock.add_response(status_code=400, text="Bad Request")
        # Cleanup DELETE.
        httpx_mock.add_response(status_code=204)

        params = InsertImageParams(
            presentation_id=_PRES_ID,
            slide_id="slide-001",
            file=FileFromBytes(data=img, filename="chart.png", mime_type="image/png"),
        )
        result = await google_slides_insert_image(params, token=_TOKEN)

        assert result.success is False
        assert "400" in result.error
        assert result.drive_file_id == "drive-img-001"

        # Verify cleanup DELETE was called.
        requests = httpx_mock.get_requests()
        delete_req = [r for r in requests if r.method == "DELETE"]
        assert len(delete_req) == 1
        assert "drive-img-001" in str(delete_req[0].url)

    async def test_has_tool_definition(self) -> None:
        defn = google_slides_insert_image._tool_definition
        assert defn.name == "google_slides_insert_image"
        assert defn.provider == "google"
        assert defn.service == "google_slides"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes
        assert "https://www.googleapis.com/auth/presentations" in defn.scopes
