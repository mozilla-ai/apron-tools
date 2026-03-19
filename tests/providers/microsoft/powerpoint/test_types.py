"""Tests for Microsoft PowerPoint provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.microsoft.powerpoint.types import (
    AddSlideParams,
    AddSlideResult,
    CreatePresentationParams,
    CreatePresentationResult,
    ExplorePresentationsParams,
    ExplorePresentationsResult,
    PresentationInfo,
    ReadPresentationParams,
    ReadPresentationResult,
    SlideInfo,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UploadToOnedriveParams,
    UploadToOnedriveResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExplorePresentationsParams:
    def test_defaults(self) -> None:
        params = ExplorePresentationsParams()
        assert params.max_results == 20

    def test_custom(self) -> None:
        params = ExplorePresentationsParams(max_results=5)
        assert params.max_results == 5


class TestReadPresentationParams:
    def test_required(self) -> None:
        params = ReadPresentationParams(presentation_id="pptx-001")
        assert params.presentation_id == "pptx-001"
        assert params.include_notes is False

    def test_with_notes(self) -> None:
        params = ReadPresentationParams(presentation_id="pptx-001", include_notes=True)
        assert params.include_notes is True


class TestCreatePresentationParams:
    def test_required(self) -> None:
        params = CreatePresentationParams(name="Test.pptx")
        assert params.name == "Test.pptx"
        assert params.title == ""
        assert params.folder_path == "root"

    def test_all_fields(self) -> None:
        params = CreatePresentationParams(name="Report.pptx", title="Q4 Report", folder_path="Documents")
        assert params.name == "Report.pptx"
        assert params.title == "Q4 Report"
        assert params.folder_path == "Documents"


class TestAddSlideParams:
    def test_required(self) -> None:
        params = AddSlideParams(presentation_id="pptx-001")
        assert params.presentation_id == "pptx-001"
        assert params.layout == "blank"
        assert params.title == ""
        assert params.content == ""

    def test_all_fields(self) -> None:
        params = AddSlideParams(
            presentation_id="pptx-001",
            layout="title_and_content",
            title="Slide Title",
            content="Body text",
        )
        assert params.layout == "title_and_content"
        assert params.title == "Slide Title"


class TestUpdateSlideTextParams:
    def test_required(self) -> None:
        params = UpdateSlideTextParams(presentation_id="pptx-001", slide_number=1, text="Updated")
        assert params.slide_number == 1
        assert params.text == "Updated"
        assert params.shape_index == 0


class TestUploadToOnedriveParams:
    def test_url_input(self) -> None:
        params = UploadToOnedriveParams(file={"type": "url", "url": "https://example.com/file.pptx"})
        assert params.file.type == "url"

    def test_bytes_input(self) -> None:
        import base64

        data_b64 = base64.b64encode(b"hello").decode()
        params = UploadToOnedriveParams(
            file={
                "type": "bytes",
                "data": data_b64,
                "filename": "test.pptx",
                "mime_type": "application/octet-stream",
            }
        )
        assert params.file.type == "bytes"
        assert params.file.data == b"hello"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestPresentationInfo:
    def test_parse_from_api(self) -> None:
        data = _load_json("search_files.json")
        info = PresentationInfo.model_validate(data["value"][0])
        assert info.id == "pptx-001"
        assert info.name == "Q4 Review.pptx"
        assert info.web_url == "https://onedrive.live.com/view/pptx-001"
        assert info.last_modified == "2025-01-15T10:30:00Z"
        assert info.size == 1048576

    def test_extra_fields_ignored(self) -> None:
        info = PresentationInfo.model_validate({"id": "x", "name": "x.pptx", "unknownField": True})
        assert info.id == "x"


class TestSlideInfo:
    def test_basic(self) -> None:
        slide = SlideInfo(number=1, title="Intro", texts=["Hello"], notes="Note")
        assert slide.number == 1
        assert slide.title == "Intro"
        assert slide.texts == ["Hello"]
        assert slide.notes == "Note"

    def test_defaults(self) -> None:
        slide = SlideInfo(number=1)
        assert slide.title == ""
        assert slide.texts == []
        assert slide.notes == ""


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class TestExplorePresentationsResult:
    def test_success(self) -> None:
        data = _load_json("search_files.json")
        presentations = [PresentationInfo.model_validate(f) for f in data["value"]]
        result = ExplorePresentationsResult(success=True, presentations=presentations)
        assert result.success is True
        assert len(result.presentations) == 2

    def test_str_output(self) -> None:
        result = ExplorePresentationsResult(
            success=True,
            presentations=[
                PresentationInfo(
                    id="pptx-001",
                    name="Q4 Review.pptx",
                    web_url="https://example.com",
                )
            ],
        )
        text = str(result)
        assert "1 presentation(s)" in text
        assert "Q4 Review.pptx" in text

    def test_str_empty(self) -> None:
        result = ExplorePresentationsResult(success=True, presentations=[])
        assert str(result) == "No PowerPoint presentations found."

    def test_str_on_error(self) -> None:
        result = ExplorePresentationsResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


class TestReadPresentationResult:
    def test_success(self) -> None:
        result = ReadPresentationResult(
            success=True,
            name="Test.pptx",
            slides=[SlideInfo(number=1, title="Hello", texts=["World"])],
        )
        assert result.success is True
        assert result.name == "Test.pptx"
        assert len(result.slides) == 1

    def test_str_output(self) -> None:
        result = ReadPresentationResult(
            success=True,
            name="Test.pptx",
            slides=[
                SlideInfo(number=1, title="Intro", texts=["Welcome"]),
                SlideInfo(number=2, title="", texts=["Content"]),
            ],
        )
        text = str(result)
        assert "Test.pptx" in text
        assert "2 slides" in text
        assert "Intro" in text

    def test_str_on_error(self) -> None:
        result = ReadPresentationResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


class TestCreatePresentationResult:
    def test_success(self) -> None:
        result = CreatePresentationResult(
            success=True,
            presentation_id="pptx-004",
            name="New.pptx",
            web_url="https://example.com",
        )
        assert result.presentation_id == "pptx-004"

    def test_str_output(self) -> None:
        result = CreatePresentationResult(
            success=True,
            presentation_id="pptx-004",
            name="New.pptx",
            web_url="https://example.com",
        )
        text = str(result)
        assert "New.pptx" in text
        assert "pptx-004" in text
        assert "https://example.com" in text

    def test_str_on_error(self) -> None:
        result = CreatePresentationResult(success=False, error="Upload failed")
        assert str(result) == "Error: Upload failed"


class TestAddSlideResult:
    def test_success(self) -> None:
        result = AddSlideResult(success=True, name="Deck.pptx", layout="blank", slide_count=3)
        assert result.slide_count == 3

    def test_str_output(self) -> None:
        result = AddSlideResult(success=True, name="Deck.pptx", layout="blank", slide_count=3)
        text = str(result)
        assert "Deck.pptx" in text
        assert "blank" in text
        assert "3" in text

    def test_str_on_error(self) -> None:
        result = AddSlideResult(success=False, error="Download failed")
        assert str(result) == "Error: Download failed"


class TestUpdateSlideTextResult:
    def test_success(self) -> None:
        result = UpdateSlideTextResult(success=True, name="Deck.pptx", slide_number=2, shape_name="Title 1")
        assert result.slide_number == 2
        assert result.shape_name == "Title 1"

    def test_str_output(self) -> None:
        result = UpdateSlideTextResult(success=True, name="Deck.pptx", slide_number=2, shape_name="Title 1")
        text = str(result)
        assert "Deck.pptx" in text
        assert "slide 2" in text
        assert "Title 1" in text

    def test_str_on_error(self) -> None:
        result = UpdateSlideTextResult(success=False, error="Out of range")
        assert str(result) == "Error: Out of range"


class TestUploadToOnedriveResult:
    def test_success(self) -> None:
        result = UploadToOnedriveResult(
            success=True,
            file_id="pptx-004",
            name="file.pptx",
            web_url="https://example.com",
        )
        assert result.file_id == "pptx-004"

    def test_str_output(self) -> None:
        result = UploadToOnedriveResult(
            success=True,
            file_id="pptx-004",
            name="file.pptx",
            web_url="https://example.com",
        )
        text = str(result)
        assert "file.pptx" in text
        assert "pptx-004" in text
        assert "https://example.com" in text

    def test_str_on_error(self) -> None:
        result = UploadToOnedriveResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"
