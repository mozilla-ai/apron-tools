"""Tests for Google Drive provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.google.drive.types import (
    CreateFolderParams,
    CreateFolderResult,
    DriveFile,
    GetFileInfoParams,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileItem,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
    ShareFileItem,
    ShareFilesParams,
    ShareFilesResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListFilesParams:
    def test_defaults(self):
        params = ListFilesParams()
        assert params.max_results == 20
        assert params.folder_id is None

    def test_custom(self):
        params = ListFilesParams(max_results=5, folder_id="folder-001")
        assert params.max_results == 5
        assert params.folder_id == "folder-001"


class TestCreateFolderParams:
    def test_required(self):
        params = CreateFolderParams(name="New Folder")
        assert params.name == "New Folder"
        assert params.parent_id is None

    def test_with_parent(self):
        params = CreateFolderParams(name="Subfolder", parent_id="folder-001")
        assert params.parent_id == "folder-001"


class TestGetFileInfoParams:
    def test_required(self):
        params = GetFileInfoParams(file_id="file-001")
        assert params.file_id == "file-001"


class TestMoveFilesParams:
    def test_required(self):
        params = MoveFilesParams(file_ids="file-001", destination_folder_id="folder-002")
        assert params.file_ids == "file-001"
        assert params.destination_folder_id == "folder-002"

    def test_multiple_ids(self):
        params = MoveFilesParams(file_ids="file-001,file-002", destination_folder_id="folder-002")
        assert params.file_ids == "file-001,file-002"


class TestSearchParams:
    def test_required(self):
        params = SearchParams(query="Project")
        assert params.query == "Project"
        assert params.max_results == 20

    def test_custom(self):
        params = SearchParams(query="Budget", max_results=5)
        assert params.max_results == 5


class TestShareFilesParams:
    def test_required(self):
        params = ShareFilesParams(file_ids="file-001", email="bob@example.com")
        assert params.file_ids == "file-001"
        assert params.email == "bob@example.com"
        assert params.role == "reader"

    def test_custom_role(self):
        params = ShareFilesParams(
            file_ids="file-001,file-002",
            email="bob@example.com",
            role="writer",
        )
        assert params.role == "writer"
        assert params.file_ids == "file-001,file-002"


# ---------------------------------------------------------------------------
# ListFilesResult
# ---------------------------------------------------------------------------


class TestListFilesResult:
    def test_parse_files(self):
        data = _load_json("list_files.json")
        result = ListFilesResult.model_validate(data)

        assert result.success is True
        assert len(result.files) == 2

    def test_file_fields(self):
        data = _load_json("list_files.json")
        f = DriveFile.model_validate(data["files"][0])

        assert f.id == "file-001"
        assert f.name == "Project Plan"
        assert f.mime_type == "application/vnd.google-apps.document"
        assert f.created_time == "2024-01-15T10:00:00Z"
        assert f.modified_time == "2024-03-10T14:22:00Z"
        assert f.parents == ["folder-001"]
        assert "file-001" in f.web_view_link

    def test_str_output(self):
        data = _load_json("list_files.json")
        result = ListFilesResult.model_validate(data)
        text = str(result)

        assert "2 file(s)" in text
        assert "Project Plan" in text
        assert "Work" in text

    def test_str_on_error(self):
        result = ListFilesResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListFilesResult(success=True, files=[])
        assert str(result) == "No files found."


# ---------------------------------------------------------------------------
# CreateFolderResult
# ---------------------------------------------------------------------------


class TestCreateFolderResult:
    def test_parse_real_api_response(self):
        data = _load_json("create_folder.json")
        result = CreateFolderResult.model_validate(data)

        assert result.success is True
        assert result.id == "folder-002"
        assert result.name == "New Folder"
        assert "folder-002" in result.web_view_link

    def test_str_output(self):
        data = _load_json("create_folder.json")
        result = CreateFolderResult.model_validate(data)
        text = str(result)

        assert "New Folder" in text
        assert "folder-002" in text

    def test_str_on_error(self):
        result = CreateFolderResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"


# ---------------------------------------------------------------------------
# GetFileInfoResult
# ---------------------------------------------------------------------------


class TestGetFileInfoResult:
    def test_parse_real_api_response(self):
        data = _load_json("get_file_info.json")
        result = GetFileInfoResult.model_validate(data)

        assert result.success is True
        assert result.id == "file-001"
        assert result.name == "Project Plan"
        assert result.mime_type == "application/vnd.google-apps.document"
        assert result.description == "Q1 project planning document"
        assert result.starred is False
        assert result.trashed is False
        assert result.parents == ["folder-001"]
        assert result.size == "2048"
        assert len(result.owners) == 1
        assert result.owners[0].display_name == "Alice Smith"
        assert result.owners[0].email_address == "alice@example.com"
        assert result.shared is True

    def test_str_output(self):
        data = _load_json("get_file_info.json")
        result = GetFileInfoResult.model_validate(data)
        text = str(result)

        assert "Project Plan" in text
        assert "file-001" in text
        assert "Alice Smith" in text
        assert "alice@example.com" in text

    def test_str_on_error(self):
        result = GetFileInfoResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# MoveFilesResult
# ---------------------------------------------------------------------------


class TestMoveFilesResult:
    def test_str_output(self):
        result = MoveFilesResult(
            success=True,
            destination_folder_id="folder-002",
            items=[
                MoveFileItem(file_id="file-001", success=True, name="Project Plan"),
            ],
        )
        text = str(result)

        assert "Project Plan" in text
        assert "folder-002" in text

    def test_partial_failure(self):
        result = MoveFilesResult(
            success=True,
            destination_folder_id="folder-002",
            items=[
                MoveFileItem(file_id="file-001", success=True, name="A"),
                MoveFileItem(file_id="file-002", success=False, error="403"),
            ],
        )
        text = str(result)
        assert "Failed: 403" in text

    def test_empty_items(self):
        result = MoveFilesResult(success=True)
        assert "No files processed" in str(result)

    def test_str_on_error(self):
        result = MoveFilesResult(success=False, error="Permission denied")
        assert str(result) == "Error: Permission denied"


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    def test_parse_real_api_response(self):
        data = _load_json("search.json")
        result = SearchResult.model_validate(data)

        assert result.success is True
        assert len(result.files) == 1
        assert result.files[0].name == "Project Plan"

    def test_str_output(self):
        data = _load_json("search.json")
        result = SearchResult.model_validate(data)
        text = str(result)

        assert "1 result(s)" in text
        assert "Project Plan" in text

    def test_str_on_error(self):
        result = SearchResult(success=False, error="Invalid query")
        assert str(result) == "Error: Invalid query"

    def test_str_empty(self):
        result = SearchResult(success=True, files=[])
        assert str(result) == "No files matched the search."


# ---------------------------------------------------------------------------
# ShareFilesResult
# ---------------------------------------------------------------------------


class TestShareFilesResult:
    def test_str_output(self):
        result = ShareFilesResult(
            success=True,
            email="bob@example.com",
            role="writer",
            items=[
                ShareFileItem(
                    file_id="file-001",
                    success=True,
                    permission_id="perm-001",
                    type="user",
                    role="writer",
                    emailAddress="bob@example.com",
                    displayName="Bob Jones",
                ),
            ],
        )
        text = str(result)

        assert "file-001" in text
        assert "bob@example.com" in text
        assert "writer" in text

    def test_partial_failure(self):
        result = ShareFilesResult(
            success=True,
            email="bob@example.com",
            role="reader",
            items=[
                ShareFileItem(file_id="file-001", success=True),
                ShareFileItem(file_id="file-002", success=False, error="403"),
            ],
        )
        text = str(result)
        assert "Failed: 403" in text

    def test_empty_items(self):
        result = ShareFilesResult(success=True)
        assert "No files processed" in str(result)

    def test_str_on_error(self):
        result = ShareFilesResult(success=False, error="User not found")
        assert str(result) == "Error: User not found"
