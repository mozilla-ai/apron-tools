"""Tests for Google Docs tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.google.docs.tools import (
    google_docs_copy_document,
    google_docs_create_document,
    google_docs_list_documents,
    google_docs_read_document,
    google_docs_update_document,
)
from any_tool.providers.google.docs.types import (
    CopyDocumentParams,
    CopyDocumentResult,
    CreateDocumentParams,
    CreateDocumentResult,
    ListDocumentsParams,
    ListDocumentsResult,
    ReadDocumentParams,
    ReadDocumentResult,
    UpdateDocumentParams,
    UpdateDocumentResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_DOCS_BASE = "https://docs.googleapis.com/v1/documents"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"
_DOCUMENT_ID = "doc-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_documents
# ---------------------------------------------------------------------------


class TestListDocuments:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}?q=mimeType%3D%27application%2Fvnd.google-apps.document%27&pageSize=20&fields=files%28id%2Cname%2CcreatedTime%2CmodifiedTime%29&orderBy=modifiedTime+desc&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=allDrives",
            json=_load_json("list_documents.json"),
        )

        result = await google_docs_list_documents(ListDocumentsParams(), token=_TOKEN)

        assert isinstance(result, ListDocumentsResult)
        assert result.success is True
        assert len(result.files) == 2
        assert result.files[0].name == "Meeting Notes"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_docs_list_documents(ListDocumentsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_docs_list_documents._tool_definition
        assert defn.name == "google_docs_list_documents"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# create_document
# ---------------------------------------------------------------------------


class TestCreateDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=_DOCS_BASE,
            json=_load_json("create_document.json"),
        )

        result = await google_docs_create_document(
            CreateDocumentParams(title="Meeting Notes"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateDocumentResult)
        assert result.success is True
        assert result.document_id == _DOCUMENT_ID
        assert result.title == "Meeting Notes"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_docs_create_document(
            CreateDocumentParams(title="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_docs_create_document._tool_definition
        assert defn.name == "google_docs_create_document"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
        assert "https://www.googleapis.com/auth/documents" in defn.scopes


# ---------------------------------------------------------------------------
# read_document
# ---------------------------------------------------------------------------


class TestReadDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DOCS_BASE}/{_DOCUMENT_ID}",
            json=_load_json("read_document.json"),
        )

        result = await google_docs_read_document(
            ReadDocumentParams(document_id=_DOCUMENT_ID),
            token=_TOKEN,
        )

        assert isinstance(result, ReadDocumentResult)
        assert result.success is True
        assert result.document_id == _DOCUMENT_ID
        assert result.title == "Meeting Notes"
        assert "Discussion points" in result.text_content

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_docs_read_document(
            ReadDocumentParams(document_id="bad_id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_docs_read_document._tool_definition
        assert defn.name == "google_docs_read_document"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
        assert "https://www.googleapis.com/auth/documents" in defn.scopes


# ---------------------------------------------------------------------------
# update_document
# ---------------------------------------------------------------------------


class TestUpdateDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DOCS_BASE}/{_DOCUMENT_ID}:batchUpdate",
            json=_load_json("update_document.json"),
        )

        result = await google_docs_update_document(
            UpdateDocumentParams(
                document_id=_DOCUMENT_ID,
                requests=[
                    {"insertText": {"location": {"index": 1}, "text": "Hello\n"}},
                ],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateDocumentResult)
        assert result.success is True
        assert result.document_id == _DOCUMENT_ID
        assert result.write_control.required_revision_id == "revision-002"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_docs_update_document(
            UpdateDocumentParams(
                document_id="bad_id",
                requests=[{"insertText": {"location": {"index": 1}, "text": "x"}}],
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_docs_update_document._tool_definition
        assert defn.name == "google_docs_update_document"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
        assert "https://www.googleapis.com/auth/documents" in defn.scopes


# ---------------------------------------------------------------------------
# copy_document
# ---------------------------------------------------------------------------


class TestCopyDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_DOCUMENT_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_document_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_DOCUMENT_ID}/copy?supportsAllDrives=true",
            json=_load_json("copy_document.json"),
        )

        result = await google_docs_copy_document(
            CopyDocumentParams(
                document_id=_DOCUMENT_ID,
                new_title="Copy of Meeting Notes",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CopyDocumentResult)
        assert result.success is True
        assert result.id == "doc-003"
        assert result.name == "Copy of Meeting Notes"
        assert result.original_name == "Meeting Notes"

    async def test_meta_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_docs_copy_document(
            CopyDocumentParams(document_id="bad_id", new_title="Copy"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_copy_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_DOCUMENT_ID}?fields=name&supportsAllDrives=true",
            json=_load_json("copy_document_meta.json"),
        )
        httpx_mock.add_response(
            url=f"{_DRIVE_BASE}/{_DOCUMENT_ID}/copy?supportsAllDrives=true",
            status_code=403,
            text="Forbidden",
        )

        result = await google_docs_copy_document(
            CopyDocumentParams(
                document_id=_DOCUMENT_ID,
                new_title="Copy",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_docs_copy_document._tool_definition
        assert defn.name == "google_docs_copy_document"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


class TestGoogleDocsReplaceText:
    async def test_success(self, httpx_mock) -> None:
        from any_tool.providers.google.docs.tools import google_docs_replace_text
        from any_tool.providers.google.docs.types import ReplaceTextParams

        httpx_mock.add_response(json={"title": "My Document"})
        httpx_mock.add_response(
            json={
                "documentId": "doc-001",
                "replies": [{"replaceAllText": {"occurrencesChanged": 3}}],
            }
        )
        result = await google_docs_replace_text(
            ReplaceTextParams(document_id="doc-001", find_text="old", replace_text="new"),
            token="test-token",
        )
        assert result.success is True
        assert result.occurrences_changed == 3
        assert result.title == "My Document"
        assert "3 occurrence(s)" in str(result)

    async def test_zero_replacements(self, httpx_mock) -> None:
        from any_tool.providers.google.docs.tools import google_docs_replace_text
        from any_tool.providers.google.docs.types import ReplaceTextParams

        httpx_mock.add_response(json={"title": "My Document"})
        httpx_mock.add_response(
            json={"documentId": "doc-001", "replies": [{"replaceAllText": {"occurrencesChanged": 0}}]}
        )
        result = await google_docs_replace_text(
            ReplaceTextParams(document_id="doc-001", find_text="nonexistent", replace_text="new"),
            token="test-token",
        )
        assert result.success is True
        assert result.occurrences_changed == 0

    async def test_api_error(self, httpx_mock) -> None:
        from any_tool.providers.google.docs.tools import google_docs_replace_text
        from any_tool.providers.google.docs.types import ReplaceTextParams

        httpx_mock.add_response(status_code=404, text="Not Found")
        result = await google_docs_replace_text(
            ReplaceTextParams(document_id="bad-id", find_text="old", replace_text="new"),
            token="test-token",
        )
        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        from any_tool.providers.google.docs.tools import google_docs_replace_text

        defn = google_docs_replace_text._tool_definition
        assert defn.name == "google_docs_replace_text"
        assert defn.provider == "google"
        assert defn.service == "google_docs"
