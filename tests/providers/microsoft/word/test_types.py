"""Tests for Microsoft Word provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.microsoft.word.types import (
    CreateDocumentParams,
    CreateDocumentResult,
    DocumentInfo,
    ExploreDocumentsParams,
    ExploreDocumentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
    UploadToOnedriveParams,
    UploadToOnedriveResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreDocumentsParams:
    def test_defaults(self) -> None:
        params = ExploreDocumentsParams()
        assert params.max_results == 20

    def test_custom(self) -> None:
        params = ExploreDocumentsParams(max_results=5)
        assert params.max_results == 5


class TestReadDocumentParams:
    def test_required(self) -> None:
        params = ReadDocumentParams(document_id="docx-001")
        assert params.document_id == "docx-001"


class TestCreateDocumentParams:
    def test_required(self) -> None:
        params = CreateDocumentParams(name="Test.docx")
        assert params.name == "Test.docx"
        assert params.content == ""
        assert params.folder_path == "root"

    def test_all_fields(self) -> None:
        params = CreateDocumentParams(name="Report.docx", content="Hello", folder_path="Documents")
        assert params.name == "Report.docx"
        assert params.content == "Hello"
        assert params.folder_path == "Documents"


class TestUpdateDocumentParams:
    def test_required(self) -> None:
        params = UpdateDocumentParams(document_id="docx-001", content="New text")
        assert params.document_id == "docx-001"
        assert params.content == "New text"


class TestUploadToOnedriveParams:
    def test_url_input(self) -> None:
        params = UploadToOnedriveParams(file={"type": "url", "url": "https://example.com/file.docx"})
        assert params.file.type == "url"

    def test_bytes_input(self) -> None:
        import base64

        data_b64 = base64.b64encode(b"hello").decode()
        params = UploadToOnedriveParams(
            file={
                "type": "bytes",
                "data": data_b64,
                "filename": "test.docx",
                "mime_type": "application/octet-stream",
            }
        )
        assert params.file.type == "bytes"
        assert params.file.data == b"hello"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestDocumentInfo:
    def test_parse_from_api(self) -> None:
        data = _load_json("search_files.json")
        info = DocumentInfo.model_validate(data["value"][0])
        assert info.id == "docx-001"
        assert info.name == "Project Proposal.docx"
        assert info.web_url == "https://onedrive.live.com/view/docx-001"
        assert info.last_modified == "2025-01-15T10:30:00Z"
        assert info.size == 524288

    def test_extra_fields_ignored(self) -> None:
        info = DocumentInfo.model_validate({"id": "x", "name": "x.docx", "unknownField": True})
        assert info.id == "x"


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class TestExploreDocumentsResult:
    def test_success(self) -> None:
        data = _load_json("search_files.json")
        documents = [DocumentInfo.model_validate(f) for f in data["value"]]
        result = ExploreDocumentsResult(success=True, documents=documents)
        assert result.success is True
        assert len(result.documents) == 2

    def test_str_output(self) -> None:
        result = ExploreDocumentsResult(
            success=True,
            documents=[
                DocumentInfo(
                    id="docx-001",
                    name="Project Proposal.docx",
                    web_url="https://example.com",
                )
            ],
        )
        text = str(result)
        assert "1 document(s)" in text
        assert "Project Proposal.docx" in text

    def test_str_empty(self) -> None:
        result = ExploreDocumentsResult(success=True, documents=[])
        assert str(result) == "No Word documents found."

    def test_str_on_error(self) -> None:
        result = ExploreDocumentsResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


class TestReadDocumentResult:
    def test_success(self) -> None:
        result = ReadDocumentResult(
            success=True,
            name="Test.docx",
            paragraphs=["Hello", "World"],
        )
        assert result.success is True
        assert result.name == "Test.docx"
        assert len(result.paragraphs) == 2

    def test_str_output(self) -> None:
        result = ReadDocumentResult(
            success=True,
            name="Test.docx",
            paragraphs=["Introduction", "Body text"],
        )
        text = str(result)
        assert "Test.docx" in text
        assert "2 paragraphs" in text
        assert "Introduction" in text

    def test_str_with_tables(self) -> None:
        result = ReadDocumentResult(
            success=True,
            name="Test.docx",
            paragraphs=["Intro"],
            tables=[[["A1", "B1"], ["A2", "B2"]]],
        )
        text = str(result)
        assert "Table 1" in text
        assert "A1" in text

    def test_str_on_error(self) -> None:
        result = ReadDocumentResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


class TestCreateDocumentResult:
    def test_success(self) -> None:
        result = CreateDocumentResult(
            success=True,
            document_id="docx-004",
            name="New.docx",
            web_url="https://example.com",
        )
        assert result.document_id == "docx-004"

    def test_str_output(self) -> None:
        result = CreateDocumentResult(
            success=True,
            document_id="docx-004",
            name="New.docx",
            web_url="https://example.com",
        )
        text = str(result)
        assert "New.docx" in text
        assert "docx-004" in text
        assert "https://example.com" in text

    def test_str_on_error(self) -> None:
        result = CreateDocumentResult(success=False, error="Upload failed")
        assert str(result) == "Error: Upload failed"


class TestUpdateDocumentResult:
    def test_success(self) -> None:
        result = UpdateDocumentResult(success=True, name="Report.docx")
        assert result.name == "Report.docx"

    def test_str_output(self) -> None:
        result = UpdateDocumentResult(success=True, name="Report.docx")
        text = str(result)
        assert "Report.docx" in text

    def test_str_on_error(self) -> None:
        result = UpdateDocumentResult(success=False, error="Download failed")
        assert str(result) == "Error: Download failed"


class TestUploadToOnedriveResult:
    def test_success(self) -> None:
        result = UploadToOnedriveResult(
            success=True,
            file_id="docx-004",
            name="file.docx",
            web_url="https://example.com",
        )
        assert result.file_id == "docx-004"

    def test_str_output(self) -> None:
        result = UploadToOnedriveResult(
            success=True,
            file_id="docx-004",
            name="file.docx",
            web_url="https://example.com",
        )
        text = str(result)
        assert "file.docx" in text
        assert "docx-004" in text
        assert "https://example.com" in text

    def test_str_on_error(self) -> None:
        result = UploadToOnedriveResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"
