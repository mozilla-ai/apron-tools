"""Tests for Google Drive tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.google.drive.tools import (
    create_folder,
    get_file_info,
    list_files,
    move_file,
    search,
    share_file,
)
from any_tool.providers.google.drive.types import (
    CreateFolderParams,
    CreateFolderResult,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileParams,
    MoveFileResult,
    SearchParams,
    SearchResult,
    ShareFileParams,
    ShareFileResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test-token"
_DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"
_FILE_ID = "file-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------


class TestListFiles:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_files.json"))

        result = await list_files(ListFilesParams(), token=_TOKEN)

        assert isinstance(result, ListFilesResult)
        assert result.success is True
        assert len(result.files) == 2
        assert result.files[0].name == "Project Plan"

    async def test_success_with_folder(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("list_files.json"))

        result = await list_files(
            ListFilesParams(folder_id="folder-001"),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.files) == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await list_files(ListFilesParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = list_files._tool_definition
        assert defn.name == "list_files"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


class TestCreateFolder:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_folder.json"))

        result = await create_folder(
            CreateFolderParams(name="New Folder"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateFolderResult)
        assert result.success is True
        assert result.id == "folder-002"
        assert result.name == "New Folder"

    async def test_with_parent(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("create_folder.json"))

        result = await create_folder(
            CreateFolderParams(name="New Folder", parent_id="folder-001"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await create_folder(
            CreateFolderParams(name="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = create_folder._tool_definition
        assert defn.name == "create_folder"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------


class TestGetFileInfo:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("get_file_info.json"))

        result = await get_file_info(
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

        result = await get_file_info(
            GetFileInfoParams(file_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = get_file_info._tool_definition
        assert defn.name == "get_file_info"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------


class TestMoveFile:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        # First request: get current parents.
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        # Second request: update parents.
        httpx_mock.add_response(json=_load_json("move_file.json"))

        result = await move_file(
            MoveFileParams(file_id=_FILE_ID, destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert isinstance(result, MoveFileResult)
        assert result.success is True
        assert result.id == _FILE_ID
        assert result.parents == ["folder-002"]

    async def test_meta_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await move_file(
            MoveFileParams(file_id="bad-id", destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_update_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("move_file_meta.json"))
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await move_file(
            MoveFileParams(file_id=_FILE_ID, destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = move_file._tool_definition
        assert defn.name == "move_file"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("search.json"))

        result = await search(
            SearchParams(query="Project"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.files) == 1
        assert result.files[0].name == "Project Plan"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=500, text="Internal Server Error")

        result = await search(
            SearchParams(query="test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "500" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = search._tool_definition
        assert defn.name == "search"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes


# ---------------------------------------------------------------------------
# share_file
# ---------------------------------------------------------------------------


class TestShareFile:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("share_file.json"))

        result = await share_file(
            ShareFileParams(
                file_id=_FILE_ID,
                email="bob@example.com",
                role="writer",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, ShareFileResult)
        assert result.success is True
        assert result.id == "perm-001"
        assert result.role == "writer"
        assert result.email_address == "bob@example.com"
        assert result.display_name == "Bob Jones"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await share_file(
            ShareFileParams(file_id="bad-id", email="nobody@example.com"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = share_file._tool_definition
        assert defn.name == "share_file"
        assert defn.provider == "google_drive"
        assert "https://www.googleapis.com/auth/drive" in defn.scopes
