"""Tests for Google Slides provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apron_tools.providers.google.slides.types import (
    AddSlideParams,
    AddSlideResult,
    CopyPresentationParams,
    CopyPresentationResult,
    CreatePresentationParams,
    CreatePresentationResult,
    DeleteShapeParams,
    DeleteShapeResult,
    DeleteSlideParams,
    DeleteSlideResult,
    DuplicateSlideParams,
    DuplicateSlideResult,
    FormatTextParams,
    FormatTextResult,
    InsertElementParams,
    InsertElementResult,
    ListPresentationsParams,
    ListPresentationsResult,
    PresentationFile,
    ReadPresentationParams,
    ReadPresentationResult,
    SlideInfo,
    UpdateSlideBackgroundParams,
    UpdateSlideBackgroundResult,
    UpdateSlideTextParams,
    UpdateSlideTextResult,
    UpdateTableCellParams,
    UpdateTableCellResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListPresentationsParams:
    def test_defaults(self):
        params = ListPresentationsParams()
        assert params.max_results == 20

    def test_custom(self):
        params = ListPresentationsParams(max_results=5)
        assert params.max_results == 5


class TestCreatePresentationParams:
    def test_required(self):
        params = CreatePresentationParams(title="Q1 Review")
        assert params.title == "Q1 Review"


class TestCopyPresentationParams:
    def test_required(self):
        params = CopyPresentationParams(presentation_id="pres-001", new_title="Copy")
        assert params.presentation_id == "pres-001"
        assert params.new_title == "Copy"


class TestReadPresentationParams:
    def test_required(self):
        params = ReadPresentationParams(presentation_id="pres-001")
        assert params.presentation_id == "pres-001"
        assert params.include_speaker_notes is False

    def test_with_notes(self):
        params = ReadPresentationParams(
            presentation_id="pres-001",
            include_speaker_notes=True,
        )
        assert params.include_speaker_notes is True


class TestAddSlideParams:
    def test_defaults(self):
        params = AddSlideParams(presentation_id="pres-001")
        assert params.presentation_id == "pres-001"
        assert params.layout == "BLANK"
        assert params.insertion_index is None

    def test_custom(self):
        params = AddSlideParams(
            presentation_id="pres-001",
            layout="TITLE",
            insertion_index=2,
        )
        assert params.layout == "TITLE"
        assert params.insertion_index == 2


class TestUpdateSlideTextParams:
    def test_required(self):
        params = UpdateSlideTextParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            text="Hello",
        )
        assert params.presentation_id == "pres-001"
        assert params.slide_id == "slide-001"
        assert params.text == "Hello"
        assert params.shape_id is None

    def test_with_shape_id(self):
        params = UpdateSlideTextParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            text="Hello",
            shape_id="elem-001",
        )
        assert params.shape_id == "elem-001"


class TestDuplicateSlideParams:
    def test_required(self):
        params = DuplicateSlideParams(
            presentation_id="pres-001",
            slide_id="slide-001",
        )
        assert params.presentation_id == "pres-001"
        assert params.slide_id == "slide-001"
        assert params.insertion_index is None


class TestInsertElementParams:
    def test_defaults(self):
        params = InsertElementParams(
            presentation_id="pres-001",
            slide_id="slide-001",
        )
        assert params.shape_type == "TEXT_BOX"
        assert params.text == ""
        assert params.x == 100
        assert params.y == 100
        assert params.width == 400
        assert params.height == 300

    def test_custom(self):
        params = InsertElementParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            shape_type="RECTANGLE",
            text="Hello",
            x=50,
            y=50,
            width=200,
            height=150,
        )
        assert params.shape_type == "RECTANGLE"
        assert params.text == "Hello"


class TestUpdateTableCellParams:
    def test_required(self):
        params = UpdateTableCellParams(
            presentation_id="pres-001",
            table_id="table-001",
            row=0,
            column=1,
            text="Revenue",
        )
        assert params.table_id == "table-001"
        assert params.row == 0
        assert params.column == 1
        assert params.text == "Revenue"


class TestFormatTextParams:
    def test_required(self):
        params = FormatTextParams(
            presentation_id="pres-001",
            object_id="elem-001",
        )
        assert params.object_id == "elem-001"
        assert params.bold is None
        assert params.italic is None
        assert params.font_size is None
        assert params.foreground_color is None
        assert params.start_index is None
        assert params.end_index is None

    def test_all_options(self):
        params = FormatTextParams(
            presentation_id="pres-001",
            object_id="elem-001",
            bold=True,
            italic=True,
            font_size=24,
            foreground_color="#FF0000",
            start_index=0,
            end_index=10,
        )
        assert params.bold is True
        assert params.font_size == 24
        assert params.foreground_color == "#FF0000"


# ---------------------------------------------------------------------------
# ListPresentationsResult
# ---------------------------------------------------------------------------


class TestListPresentationsResult:
    def test_parse_files(self):
        data = _load_json("list_presentations.json")
        files = [PresentationFile.model_validate(f) for f in data["files"]]
        result = ListPresentationsResult(success=True, files=files)

        assert result.success is True
        assert len(result.files) == 2

    def test_file_fields(self):
        data = _load_json("list_presentations.json")
        f = PresentationFile.model_validate(data["files"][0])

        assert f.id == "pres-001"
        assert f.name == "Q1 Review"
        assert f.created_time == "2024-01-15T10:00:00Z"
        assert f.modified_time == "2024-03-10T14:22:00Z"

    def test_str_output(self):
        data = _load_json("list_presentations.json")
        files = [PresentationFile.model_validate(f) for f in data["files"]]
        result = ListPresentationsResult(success=True, files=files)
        text = str(result)

        assert "2 presentation(s)" in text
        assert "Q1 Review" in text
        assert "Team Kickoff" in text

    def test_str_on_error(self):
        result = ListPresentationsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListPresentationsResult(success=True, files=[])
        assert str(result) == "No presentations found."


# ---------------------------------------------------------------------------
# CreatePresentationResult
# ---------------------------------------------------------------------------


class TestCreatePresentationResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_presentation.json")
        result = CreatePresentationResult.model_validate(data)

        assert result.success is True
        assert result.presentation_id == "pres-001"
        assert result.title == "Q1 Review"
        assert result.slide_count == 1

    def test_str_output(self):
        data = _load_json("create_presentation.json")
        result = CreatePresentationResult.model_validate(data)
        text = str(result)

        assert "Q1 Review" in text
        assert "pres-001" in text
        assert "Slides: 1" in text

    def test_str_on_error(self):
        result = CreatePresentationResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# CopyPresentationResult
# ---------------------------------------------------------------------------


class TestCopyPresentationResult:
    def test_success(self):
        result = CopyPresentationResult(
            success=True,
            id="pres-003",
            name="Copy of Q1 Review",
            original_name="Q1 Review",
        )

        assert result.success is True
        assert result.id == "pres-003"
        assert result.name == "Copy of Q1 Review"
        assert result.original_name == "Q1 Review"

    def test_str_output(self):
        result = CopyPresentationResult(
            success=True,
            id="pres-003",
            name="Copy of Q1 Review",
            original_name="Q1 Review",
        )
        text = str(result)

        assert "copied" in text
        assert "Q1 Review" in text
        assert "Copy of Q1 Review" in text
        assert "pres-003" in text

    def test_str_on_error(self):
        result = CopyPresentationResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ReadPresentationResult
# ---------------------------------------------------------------------------


class TestReadPresentationResult:
    def test_success(self):
        result = ReadPresentationResult(
            success=True,
            title="Q1 Review",
            slide_count=2,
            slides=[
                SlideInfo(object_id="slide-001", index=0, text_content=["Q1 Review"]),
                SlideInfo(object_id="slide-002", index=1, text_content=["Summary"]),
            ],
        )

        assert result.success is True
        assert result.title == "Q1 Review"
        assert result.slide_count == 2
        assert len(result.slides) == 2

    def test_str_output(self):
        result = ReadPresentationResult(
            success=True,
            title="Q1 Review",
            slide_count=2,
            slides=[
                SlideInfo(object_id="slide-001", index=0, text_content=["Q1 Review"]),
                SlideInfo(object_id="slide-002", index=1, text_content=["Summary"]),
            ],
        )
        text = str(result)

        assert "Q1 Review" in text
        assert "Total slides: 2" in text
        assert "Slide 1" in text
        assert "Summary" in text

    def test_str_on_error(self):
        result = ReadPresentationResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# AddSlideResult
# ---------------------------------------------------------------------------


class TestAddSlideResult:
    def test_parse_real_api_response(self):
        data = _load_json("batch_update_add_slide.json")
        result = AddSlideResult.model_validate(data)

        assert result.success is True
        assert result.presentation_id == "pres-001"
        assert result.slide_id == "slide-003"

    def test_str_output(self):
        result = AddSlideResult(
            success=True,
            presentation_id="pres-001",
            slide_id="slide-003",
        )
        text = str(result)

        assert "slide-003" in text

    def test_str_on_error(self):
        result = AddSlideResult(success=False, error="Invalid layout")
        assert str(result) == "Error: Invalid layout"


# ---------------------------------------------------------------------------
# UpdateSlideTextResult
# ---------------------------------------------------------------------------


class TestUpdateSlideTextResult:
    def test_success(self):
        result = UpdateSlideTextResult(
            success=True,
            presentation_id="pres-001",
            shape_id="elem-001",
        )

        assert result.success is True
        assert result.shape_id == "elem-001"

    def test_str_output(self):
        result = UpdateSlideTextResult(
            success=True,
            presentation_id="pres-001",
            shape_id="elem-001",
        )
        text = str(result)

        assert "elem-001" in text

    def test_str_on_error(self):
        result = UpdateSlideTextResult(success=False, error="Shape not found")
        assert str(result) == "Error: Shape not found"


# ---------------------------------------------------------------------------
# DuplicateSlideResult
# ---------------------------------------------------------------------------


class TestDuplicateSlideResult:
    def test_parse_real_api_response(self):
        data = _load_json("batch_update_duplicate.json")
        result = DuplicateSlideResult.model_validate(data)

        assert result.success is True
        assert result.presentation_id == "pres-001"
        assert result.new_slide_id == "slide-004"

    def test_str_output(self):
        result = DuplicateSlideResult(
            success=True,
            presentation_id="pres-001",
            new_slide_id="slide-004",
        )
        text = str(result)

        assert "slide-004" in text

    def test_str_on_error(self):
        result = DuplicateSlideResult(success=False, error="Slide not found")
        assert str(result) == "Error: Slide not found"


# ---------------------------------------------------------------------------
# InsertElementResult
# ---------------------------------------------------------------------------


class TestInsertElementResult:
    def test_success(self):
        result = InsertElementResult(
            success=True,
            presentation_id="pres-001",
            element_id="shape-001",
        )

        assert result.success is True
        assert result.element_id == "shape-001"

    def test_str_output(self):
        result = InsertElementResult(
            success=True,
            presentation_id="pres-001",
            element_id="shape-001",
        )
        text = str(result)

        assert "shape-001" in text

    def test_str_on_error(self):
        result = InsertElementResult(success=False, error="Invalid shape")
        assert str(result) == "Error: Invalid shape"


# ---------------------------------------------------------------------------
# UpdateTableCellResult
# ---------------------------------------------------------------------------


class TestUpdateTableCellResult:
    def test_success(self):
        result = UpdateTableCellResult(
            success=True,
            presentation_id="pres-001",
            table_id="table-001",
            row=0,
            column=1,
        )

        assert result.success is True
        assert result.table_id == "table-001"
        assert result.row == 0
        assert result.column == 1

    def test_str_output(self):
        result = UpdateTableCellResult(
            success=True,
            presentation_id="pres-001",
            table_id="table-001",
            row=0,
            column=1,
        )
        text = str(result)

        assert "table-001" in text
        assert "row=0" in text
        assert "col=1" in text

    def test_str_on_error(self):
        result = UpdateTableCellResult(success=False, error="Table not found")
        assert str(result) == "Error: Table not found"


# ---------------------------------------------------------------------------
# FormatTextResult
# ---------------------------------------------------------------------------


class TestFormatTextResult:
    def test_success(self):
        result = FormatTextResult(
            success=True,
            presentation_id="pres-001",
            object_id="elem-001",
        )

        assert result.success is True
        assert result.object_id == "elem-001"

    def test_str_output(self):
        result = FormatTextResult(
            success=True,
            presentation_id="pres-001",
            object_id="elem-001",
        )
        text = str(result)

        assert "elem-001" in text

    def test_str_on_error(self):
        result = FormatTextResult(success=False, error="Object not found")
        assert str(result) == "Error: Object not found"


# ---------------------------------------------------------------------------
# DeleteShapeParams / DeleteShapeResult
# ---------------------------------------------------------------------------


class TestDeleteShapeParams:
    def test_required(self):
        params = DeleteShapeParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            shape_id="shape-001",
        )
        assert params.presentation_id == "pres-001"
        assert params.slide_id == "slide-001"
        assert params.shape_id == "shape-001"


class TestDeleteShapeResult:
    def test_success_str(self):
        result = DeleteShapeResult(
            success=True,
            presentation_id="pres-001",
            slide_id="slide-001",
            shape_id="shape-001",
        )
        assert "shape-001" in str(result)
        assert "slide-001" in str(result)

    def test_str_on_error(self):
        result = DeleteShapeResult(success=False, error="Shape not found")
        assert str(result) == "Error: Shape not found"


# ---------------------------------------------------------------------------
# DeleteSlideParams / DeleteSlideResult
# ---------------------------------------------------------------------------


class TestDeleteSlideParams:
    def test_required(self):
        params = DeleteSlideParams(presentation_id="pres-001", slide_id="slide-001")
        assert params.presentation_id == "pres-001"
        assert params.slide_id == "slide-001"


class TestDeleteSlideResult:
    def test_success_str(self):
        result = DeleteSlideResult(
            success=True,
            presentation_id="pres-001",
            slide_id="slide-001",
        )
        assert "slide-001" in str(result)

    def test_str_on_error(self):
        result = DeleteSlideResult(success=False, error="Slide not found")
        assert str(result) == "Error: Slide not found"


# ---------------------------------------------------------------------------
# UpdateSlideBackgroundParams / UpdateSlideBackgroundResult
# ---------------------------------------------------------------------------


class TestUpdateSlideBackgroundParams:
    def test_hex_color(self):
        params = UpdateSlideBackgroundParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            background_color="#FFFFFF",
        )
        assert params.background_color == "#FFFFFF"
        assert params.theme_color is None

    def test_theme_color(self):
        params = UpdateSlideBackgroundParams(
            presentation_id="pres-001",
            slide_id="slide-001",
            theme_color="ACCENT1",
        )
        assert params.theme_color == "ACCENT1"
        assert params.background_color is None

    def test_requires_one_color(self):
        with pytest.raises(ValueError, match="exactly one"):
            UpdateSlideBackgroundParams(
                presentation_id="pres-001",
                slide_id="slide-001",
            )

    def test_rejects_both_colors(self):
        with pytest.raises(ValueError, match="exactly one"):
            UpdateSlideBackgroundParams(
                presentation_id="pres-001",
                slide_id="slide-001",
                background_color="#FFFFFF",
                theme_color="ACCENT1",
            )


class TestUpdateSlideBackgroundResult:
    def test_success_str(self):
        result = UpdateSlideBackgroundResult(
            success=True,
            presentation_id="pres-001",
            slide_id="slide-001",
        )
        assert "slide-001" in str(result)

    def test_str_on_error(self):
        result = UpdateSlideBackgroundResult(success=False, error="Slide not found")
        assert str(result) == "Error: Slide not found"
