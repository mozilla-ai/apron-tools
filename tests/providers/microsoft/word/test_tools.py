"""Tests for Microsoft Word tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.word.document import build_docx
from apron_tools.providers.microsoft.word.tools import (
    microsoft_word_create_document,
    microsoft_word_explore_documents,
    microsoft_word_read_document,
    microsoft_word_update_document,
    microsoft_word_upload_to_onedrive,
)
from apron_tools.providers.microsoft.word.types import (
    CreateDocumentParams,
    CreateDocumentResult,
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
_TOKEN = "test_oauth_token"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_ITEM_ID = "docx-001"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# explore_documents
# ---------------------------------------------------------------------------


class TestExploreDocuments:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='doc')",
            json=_load_json("search_files.json"),
        )

        result = await microsoft_word_explore_documents(
            ExploreDocumentsParams(),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, ExploreDocumentsResult)
        assert result.success is True
        assert len(result.documents) == 2
        assert result.documents[0].name == "Project Proposal.docx"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        import httpx

        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
        )

        result = await microsoft_word_explore_documents(
            ExploreDocumentsParams(),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_word_explore_documents._tool_definition
        assert defn.name == "microsoft_word_explore_documents"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_word"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# read_document
# ---------------------------------------------------------------------------


class TestReadDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        docx_bytes = build_docx("Hello World")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=docx_bytes,
        )

        result = await microsoft_word_read_document(
            ReadDocumentParams(document_id=_ITEM_ID),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, ReadDocumentResult)
        assert result.success is True
        assert result.name == "Project Proposal.docx"
        assert "Hello World" in result.paragraphs

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

        result = await microsoft_word_read_document(
            ReadDocumentParams(document_id=_ITEM_ID),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_word_read_document._tool_definition
        assert defn.name == "microsoft_word_read_document"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_word"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# create_document
# ---------------------------------------------------------------------------


class TestCreateDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_create_document(
            CreateDocumentParams(name="Report", content="Some text"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, CreateDocumentResult)
        assert result.success is True
        assert result.document_id == "docx-004"

    async def test_filename_extension_added(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_create_document(
            CreateDocumentParams(name="Report"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_filename_extension_preserved(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Notes.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_create_document(
            CreateDocumentParams(name="Notes.docx"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_upload_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Report.docx:/content",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_word_create_document(
            CreateDocumentParams(name="Report"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False
        assert result.error is not None

    async def test_folder_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Documents/Report.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_create_document(
            CreateDocumentParams(name="Report", folder_path="Documents"),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_word_create_document._tool_definition
        assert defn.name == "microsoft_word_create_document"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_word"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# update_document
# ---------------------------------------------------------------------------


class TestUpdateDocument:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        docx_bytes = build_docx("Original content")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=docx_bytes,
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            json=_load_json("upload_response.json"),
            method="PUT",
        )

        result = await microsoft_word_update_document(
            UpdateDocumentParams(
                document_id=_ITEM_ID,
                content="Appended text",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, UpdateDocumentResult)
        assert result.success is True
        assert result.name == "Project Proposal.docx"

    async def test_download_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_word_update_document(
            UpdateDocumentParams(
                document_id=_ITEM_ID,
                content="New text",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_upload_error(self, httpx_mock: HTTPXMock) -> None:
        docx_bytes = build_docx("Original")
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}",
            json=_load_json("file_metadata.json"),
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            content=docx_bytes,
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/{_ITEM_ID}/content",
            status_code=500,
            text="Server Error",
            method="PUT",
        )

        result = await microsoft_word_update_document(
            UpdateDocumentParams(
                document_id=_ITEM_ID,
                content="New text",
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_word_update_document._tool_definition
        assert defn.name == "microsoft_word_update_document"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_word"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# upload_to_onedrive
# ---------------------------------------------------------------------------


class TestUploadToOnedrive:
    async def test_bytes_upload(self, httpx_mock: HTTPXMock) -> None:
        import base64

        data_b64 = base64.b64encode(b"fake-docx").decode()
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/test.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_upload_to_onedrive(
            UploadToOnedriveParams(
                file={
                    "type": "bytes",
                    "data": data_b64,
                    "filename": "test.docx",
                    "mime_type": "application/octet-stream",
                },
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert isinstance(result, UploadToOnedriveResult)
        assert result.success is True
        assert result.file_id == "docx-004"

    async def test_url_upload(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://example.com/report.docx",
            content=b"remote-docx-bytes",
        )
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/report.docx:/content",
            json=_load_json("upload_response.json"),
        )

        result = await microsoft_word_upload_to_onedrive(
            UploadToOnedriveParams(
                file={"type": "url", "url": "https://example.com/report.docx"},
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is True
        assert result.file_id == "docx-004"

    async def test_url_download_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url="https://example.com/bad.docx",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_word_upload_to_onedrive(
            UploadToOnedriveParams(
                file={"type": "url", "url": "https://example.com/bad.docx"},
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
            url=f"{_GRAPH_BASE}/me/drive/root:/test.docx:/content",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_word_upload_to_onedrive(
            UploadToOnedriveParams(
                file={
                    "type": "bytes",
                    "data": data_b64,
                    "filename": "test.docx",
                    "mime_type": "application/octet-stream",
                },
            ),
            token=_TOKEN,
            base_url=_GRAPH_BASE,
        )

        assert result.success is False

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_word_upload_to_onedrive._tool_definition
        assert defn.name == "microsoft_word_upload_to_onedrive"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_word"
        assert "Files.ReadWrite" in defn.scopes
