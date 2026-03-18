"""Tests for Google Docs provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.google.docs.types import (
    CopyDocumentParams,
    CopyDocumentResult,
    CreateDocumentParams,
    CreateDocumentResult,
    DocumentFile,
    ListDocumentsParams,
    ListDocumentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListDocumentsParams:
    def test_defaults(self):
        params = ListDocumentsParams()
        assert params.max_results == 20

    def test_custom(self):
        params = ListDocumentsParams(max_results=5)
        assert params.max_results == 5


class TestCreateDocumentParams:
    def test_required(self):
        params = CreateDocumentParams(title="Meeting Notes")
        assert params.title == "Meeting Notes"
        assert params.content == ""

    def test_with_content(self):
        params = CreateDocumentParams(title="Notes", content="# Hello")
        assert params.content == "# Hello"


class TestReadDocumentParams:
    def test_required(self):
        params = ReadDocumentParams(document_id="doc-001")
        assert params.document_id == "doc-001"
        assert params.include_metadata is False

    def test_custom(self):
        params = ReadDocumentParams(document_id="doc-001", include_metadata=True)
        assert params.include_metadata is True


class TestUpdateDocumentParams:
    def test_required(self):
        params = UpdateDocumentParams(
            document_id="doc-001",
            requests=[{"insertText": {"location": {"index": 1}, "text": "Hello\n"}}],
        )
        assert params.document_id == "doc-001"
        assert len(params.requests) == 1

    def test_multiple_requests(self):
        params = UpdateDocumentParams(
            document_id="doc-001",
            requests=[
                {"insertText": {"location": {"index": 1}, "text": "Hello\n"}},
                {"replaceAllText": {"containsText": {"text": "old"}, "replaceText": "new"}},
            ],
        )
        assert len(params.requests) == 2


class TestCopyDocumentParams:
    def test_required(self):
        params = CopyDocumentParams(document_id="doc-001", new_title="Copy")
        assert params.document_id == "doc-001"
        assert params.new_title == "Copy"


# ---------------------------------------------------------------------------
# ListDocumentsResult
# ---------------------------------------------------------------------------


class TestListDocumentsResult:
    def test_parse_files(self):
        data = _load_json("list_documents.json")
        files = [DocumentFile.model_validate(f) for f in data["files"]]
        result = ListDocumentsResult(success=True, files=files)

        assert result.success is True
        assert len(result.files) == 2

    def test_file_fields(self):
        data = _load_json("list_documents.json")
        f = DocumentFile.model_validate(data["files"][0])

        assert f.id == "doc-001"
        assert f.name == "Meeting Notes"
        assert f.created_time == "2024-01-15T10:00:00Z"
        assert f.modified_time == "2024-03-10T14:22:00Z"

    def test_str_output(self):
        data = _load_json("list_documents.json")
        files = [DocumentFile.model_validate(f) for f in data["files"]]
        result = ListDocumentsResult(success=True, files=files)
        text = str(result)

        assert "2 document(s)" in text
        assert "Meeting Notes" in text
        assert "Project Brief" in text

    def test_str_on_error(self):
        result = ListDocumentsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListDocumentsResult(success=True, files=[])
        assert str(result) == "No documents found."


# ---------------------------------------------------------------------------
# CreateDocumentResult
# ---------------------------------------------------------------------------


class TestCreateDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_document.json")
        result = CreateDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert result.title == "Meeting Notes"
        assert result.revision_id == "revision-001"

    def test_str_output(self):
        data = _load_json("create_document.json")
        result = CreateDocumentResult.model_validate(data)
        text = str(result)

        assert "Meeting Notes" in text
        assert "doc-001" in text
        assert "https://docs.google.com/document/d/doc-001/edit" in text

    def test_str_on_error(self):
        result = CreateDocumentResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# ReadDocumentResult
# ---------------------------------------------------------------------------


class TestReadDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert result.title == "Meeting Notes"
        assert result.revision_id == "revision-001"

    def test_text_content(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)
        text = result.text_content

        assert "Meeting Notes" in text
        assert "Discussion points for today." in text

    def test_str_output(self):
        data = _load_json("read_document.json")
        result = ReadDocumentResult.model_validate(data)
        text = str(result)

        assert "Meeting Notes" in text
        assert "chars" in text

    def test_str_empty_document(self):
        result = ReadDocumentResult(
            success=True,
            document_id="doc-001",
            title="Empty Doc",
        )
        assert "empty" in str(result).lower()

    def test_str_on_error(self):
        result = ReadDocumentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# UpdateDocumentResult
# ---------------------------------------------------------------------------


class TestUpdateDocumentResult:
    def test_parse_real_api_response(self):
        data = _load_json("update_document.json")
        result = UpdateDocumentResult.model_validate(data)

        assert result.success is True
        assert result.document_id == "doc-001"
        assert len(result.replies) == 1
        assert result.write_control.required_revision_id == "revision-002"

    def test_str_output(self):
        data = _load_json("update_document.json")
        result = UpdateDocumentResult.model_validate(data)
        text = str(result)

        assert "doc-001" in text
        assert "revision-002" in text

    def test_str_on_error(self):
        result = UpdateDocumentResult(success=False, error="Permission denied")
        assert str(result) == "Error: Permission denied"


# ---------------------------------------------------------------------------
# CopyDocumentResult
# ---------------------------------------------------------------------------


class TestCopyDocumentResult:
    def test_success(self):
        result = CopyDocumentResult(
            success=True,
            id="doc-003",
            name="Copy of Meeting Notes",
            original_name="Meeting Notes",
        )

        assert result.success is True
        assert result.id == "doc-003"
        assert result.name == "Copy of Meeting Notes"
        assert result.original_name == "Meeting Notes"

    def test_str_output(self):
        result = CopyDocumentResult(
            success=True,
            id="doc-003",
            name="Copy of Meeting Notes",
            original_name="Meeting Notes",
        )
        text = str(result)

        assert "copied" in text.lower()
        assert "Meeting Notes" in text
        assert "Copy of Meeting Notes" in text
        assert "doc-003" in text

    def test_str_on_error(self):
        result = CopyDocumentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"
