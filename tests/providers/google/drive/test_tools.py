"""Tests for Google Drive tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.google.drive.tools import (
    google_drive_create_folder,
    google_drive_get_file_info,
    google_drive_list_files,
    google_drive_move_files,
    google_drive_search,
    google_drive_share_files,
)
from apron_tools.providers.google.drive.types import (
    CreateFolderParams,
    CreateFolderResult,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
    ShareFilesParams,
    ShareFilesResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test-token"
_FILE_ID = "file-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------


class TestListFiles:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_files.json"))

        result = await google_drive_list_files(ListFilesParams(), token=_TOKEN)

        assert isinstance(result, ListFilesResult)
        assert result.success is True
        assert len(result.files) == 2
        assert result.files[0].name == "Project Plan"

    async def test_success_with_folder(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_files.json"))

        result = await google_drive_list_files(
            ListFilesParams(folder_id="folder-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.files) == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_drive_list_files(ListFilesParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_list_files._tool_definition
        assert defn.name == "google_drive_list_files"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


class TestCreateFolder:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_folder.json"))

        result = await google_drive_create_folder(
            CreateFolderParams(name="New Folder"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateFolderResult)
        assert result.success is True
        assert result.id == "folder-002"
        assert result.name == "New Folder"

    async def test_with_parent(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_folder.json"))

        result = await google_drive_create_folder(
            CreateFolderParams(name="New Folder", parent_id="folder-001"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_drive_create_folder(
            CreateFolderParams(name="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_create_folder._tool_definition
        assert defn.name == "google_drive_create_folder"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------


class TestGetFileInfo:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_file_info.json"))

        result = await google_drive_get_file_info(
            GetFileInfoParams(file_id=_FILE_ID),
            token=_TOKEN,
        )

        assert isinstance(result, GetFileInfoResult)
        assert result.success is True
        assert result.id == _FILE_ID
        assert result.name == "Project Plan"
        assert result.description == "Q1 project planning document"
        assert len(result.owners) == 1
        assert result.owners[0].display_name == "Alice Smith"
        assert result.shared is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_drive_get_file_info(
            GetFileInfoParams(file_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_get_file_info._tool_definition
        assert defn.name == "google_drive_get_file_info"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------


class TestMoveFiles:
    async def test_single_file(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(json=_load_json("move_file.json"))

        result = await google_drive_move_files(
            MoveFilesParams(file_ids=_FILE_ID, destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert isinstance(result, MoveFilesResult)
        assert result.success is True
        assert result.destination_folder_id == "folder-002"
        assert len(result.items) == 1
        item = result.items[0]
        assert item.success is True
        assert item.file_id == _FILE_ID
        assert item.parents == ["folder-002"]

    async def test_multiple_files(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(json=_load_json("move_file.json"))
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(json=_load_json("move_file.json"))

        result = await google_drive_move_files(
            MoveFilesParams(file_ids=f"{_FILE_ID}, file-002", destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.items) == 2
        assert all(item.success for item in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(json=_load_json("move_file.json"))
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_drive_move_files(
            MoveFilesParams(file_ids=f"{_FILE_ID},bad-id", destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "404" in result.items[1].error

    async def test_empty_file_ids(self) -> None:
        result = await google_drive_move_files(
            MoveFilesParams(file_ids=" , ", destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No file IDs provided."

    async def test_update_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_drive_move_files(
            MoveFilesParams(file_ids=_FILE_ID, destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is False
        assert "403" in result.items[0].error

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_move_files._tool_definition
        assert defn.name == "google_drive_move_files"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("search.json"))

        result = await google_drive_search(
            SearchParams(query="Project"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.files) == 1
        assert result.files[0].name == "Project Plan"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await google_drive_search(
            SearchParams(query="test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_search._tool_definition
        assert defn.name == "google_drive_search"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# share_file
# ---------------------------------------------------------------------------


class TestShareFiles:
    async def test_single_file(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file.json"))

        result = await google_drive_share_files(
            ShareFilesParams(
                file_ids=_FILE_ID,
                email="bob@example.com",
                role="writer",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, ShareFilesResult)
        assert result.success is True
        assert result.target == "bob@example.com"
        assert result.role == "writer"
        assert len(result.items) == 1
        item = result.items[0]
        assert item.success is True
        assert item.file_id == _FILE_ID
        assert item.permission_id == "perm-001"
        assert item.email_address == "bob@example.com"
        assert item.display_name == "Bob Jones"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body == {"type": "user", "role": "writer", "emailAddress": "bob@example.com"}

    async def test_group_share(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file_group.json"))

        result = await google_drive_share_files(
            ShareFilesParams(
                file_ids=_FILE_ID,
                share_type="group",
                group_email="team@example.com",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.target == "team@example.com"
        assert result.items[0].type == "group"

        body = json.loads(httpx_mock.get_request().content)
        assert body == {"type": "group", "role": "reader", "emailAddress": "team@example.com"}

    async def test_domain_share(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file_domain.json"))

        result = await google_drive_share_files(
            ShareFilesParams(
                file_ids=_FILE_ID,
                share_type="domain",
                domain="example.com",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.target == "domain example.com"
        assert result.items[0].type == "domain"

        body = json.loads(httpx_mock.get_request().content)
        assert body == {"type": "domain", "role": "reader", "domain": "example.com"}

    async def test_anyone_with_link_when_allowed(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file_anyone.json"))

        result = await google_drive_share_files(
            ShareFilesParams(file_ids=_FILE_ID, allow_anyone_with_link=True),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.target == "anyone with the link"
        assert result.items[0].type == "anyone"

        body = json.loads(httpx_mock.get_request().content)
        assert body == {"type": "anyone", "role": "reader"}

    async def test_anyone_with_link_overrides_share_type(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file_anyone.json"))

        await google_drive_share_files(
            ShareFilesParams(
                file_ids=_FILE_ID,
                share_type="user",
                email="bob@example.com",
                allow_anyone_with_link=True,
            ),
            token=_TOKEN,
        )

        body = json.loads(httpx_mock.get_request().content)
        assert body == {"type": "anyone", "role": "reader"}

    async def test_multiple_files(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file.json"))
        httpx_mock.add_response(json=_load_json("share_file.json"))

        result = await google_drive_share_files(
            ShareFilesParams(
                file_ids=f"{_FILE_ID},file-002",
                email="bob@example.com",
                role="writer",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert [item.file_id for item in result.items] == [_FILE_ID, "file-002"]
        assert all(item.success for item in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file.json"))
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_drive_share_files(
            ShareFilesParams(file_ids=f"{_FILE_ID},bad-id", email="bob@example.com"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "403" in result.items[1].error

    async def test_empty_file_ids(self) -> None:
        result = await google_drive_share_files(
            ShareFilesParams(file_ids=" , ", email="bob@example.com"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No file IDs provided."

    async def test_has_tool_definition(self) -> None:
        defn = google_drive_share_files._tool_definition
        assert defn.name == "google_drive_share_files"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


class TestGoogleDriveUploadFile:
    async def test_upload_from_bytes(self, httpx_mock) -> None:
        import base64

        from apron_tools.providers.google.drive.tools import google_drive_upload_file
        from apron_tools.providers.google.drive.types import UploadFileParams
        from apron_tools.types import FileFromBytes

        httpx_mock.add_response(
            json={"id": "file-001", "name": "report.pdf", "webViewLink": "https://drive.google.com/file-001"},
        )
        b64 = base64.b64encode(b"pdf content").decode()
        result = await google_drive_upload_file(
            UploadFileParams(file=FileFromBytes(data=b64, filename="report.pdf", mime_type="application/pdf")),
            token="test-token",
            base_url="https://test.googleapis.com/upload/drive/v3/files",
        )
        assert result.success is True
        assert result.id == "file-001"
        assert result.name == "report.pdf"

    async def test_upload_with_folder(self, httpx_mock) -> None:
        import base64

        from apron_tools.providers.google.drive.tools import google_drive_upload_file
        from apron_tools.providers.google.drive.types import UploadFileParams
        from apron_tools.types import FileFromBytes

        httpx_mock.add_response(
            json={"id": "file-002", "name": "doc.txt", "webViewLink": "https://drive.google.com/file-002"},
        )
        b64 = base64.b64encode(b"text").decode()
        result = await google_drive_upload_file(
            UploadFileParams(
                file=FileFromBytes(data=b64, filename="doc.txt", mime_type="text/plain"),
                folder_id="folder-001",
            ),
            token="test-token",
            base_url="https://test.googleapis.com/upload/drive/v3/files",
        )
        assert result.success is True
        request = httpx_mock.get_request()
        assert b"folder-001" in request.content

    async def test_upload_api_error(self, httpx_mock) -> None:
        import base64

        from apron_tools.providers.google.drive.tools import google_drive_upload_file
        from apron_tools.providers.google.drive.types import UploadFileParams
        from apron_tools.types import FileFromBytes

        httpx_mock.add_response(status_code=403, text="Forbidden")
        b64 = base64.b64encode(b"data").decode()
        result = await google_drive_upload_file(
            UploadFileParams(file=FileFromBytes(data=b64, filename="f.bin", mime_type="application/octet-stream")),
            token="bad-token",
            base_url="https://test.googleapis.com/upload/drive/v3/files",
        )
        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        from apron_tools.providers.google.drive.tools import google_drive_upload_file

        defn = google_drive_upload_file._tool_definition
        assert defn.name == "google_drive_upload_file"
        assert defn.provider == "google"
        assert defn.service == "google_drive"


class TestGoogleDriveReadTextFile:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        from apron_tools.providers.google.drive.tools import google_drive_read_text_file
        from apron_tools.providers.google.drive.types import ReadTextFileParams

        # First request: metadata. Second request: content.
        httpx_mock.add_response(json={"name": "notes.txt", "mimeType": "text/plain"})
        httpx_mock.add_response(text="Hello world\nLine two")
        result = await google_drive_read_text_file(
            ReadTextFileParams(file_id="file-001"),
            token=_TOKEN,
        )
        assert result.success is True
        assert result.name == "notes.txt"
        assert "Hello world" in result.content
        assert "notes.txt" in str(result)

    async def test_non_text_file_rejected(self, httpx_mock: HTTPXMock) -> None:
        from apron_tools.providers.google.drive.tools import google_drive_read_text_file
        from apron_tools.providers.google.drive.types import ReadTextFileParams

        httpx_mock.add_response(json={"name": "image.png", "mimeType": "image/png"})
        result = await google_drive_read_text_file(
            ReadTextFileParams(file_id="file-002"),
            token=_TOKEN,
        )
        assert result.success is False
        assert "text/plain" in result.error or "image/png" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        from apron_tools.providers.google.drive.tools import google_drive_read_text_file
        from apron_tools.providers.google.drive.types import ReadTextFileParams

        httpx_mock.add_response(status_code=404, text="Not Found")
        result = await google_drive_read_text_file(
            ReadTextFileParams(file_id="file-404"),
            token=_TOKEN,
        )
        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        from apron_tools.providers.google.drive.tools import google_drive_read_text_file

        defn = google_drive_read_text_file._tool_definition
        assert defn.name == "google_drive_read_text_file"
        assert defn.provider == "google"
        assert defn.service == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes
