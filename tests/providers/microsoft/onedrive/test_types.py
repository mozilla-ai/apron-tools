"""Tests for Microsoft OneDrive pydantic models."""

from __future__ import annotations

from apron_tools.providers.microsoft.onedrive.types import (
    CreateFolderParams,
    CreateFolderResult,
    DriveItemSummary,
    FileInfo,
    GetFileInfoResult,
    ListFilesParams,
    ListFilesResult,
    MoveFileOutcome,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
)


class TestListFilesParams:
    def test_defaults(self) -> None:
        params = ListFilesParams()
        assert params.folder_path == ""
        assert params.limit == 25

    def test_custom(self) -> None:
        params = ListFilesParams(folder_path="Documents", limit=50)
        assert params.folder_path == "Documents"
        assert params.limit == 50


class TestSearchParams:
    def test_required_query(self) -> None:
        params = SearchParams(query="report")
        assert params.query == "report"
        assert params.limit == 25


class TestCreateFolderParams:
    def test_defaults(self) -> None:
        params = CreateFolderParams(folder_name="New")
        assert params.folder_name == "New"
        assert params.parent_path == ""


class TestMoveFilesParams:
    def test_required(self) -> None:
        params = MoveFilesParams(item_ids=["a", "b"], destination_folder_id="dest")
        assert params.item_ids == ["a", "b"]
        assert params.destination_folder_id == "dest"
        assert params.new_name is None


class TestDriveItemSummary:
    def test_parse_folder(self) -> None:
        item = DriveItemSummary.model_validate(
            {
                "id": "f1",
                "name": "Reports",
                "folder": {"childCount": 3},
                "webUrl": "https://onedrive.live.com/folder/f1",
            }
        )
        assert item.id == "f1"
        assert item.is_folder is True
        assert item.child_count == 3
        assert item.web_url == "https://onedrive.live.com/folder/f1"

    def test_parse_file(self) -> None:
        item = DriveItemSummary.model_validate(
            {
                "id": "x1",
                "name": "budget.xlsx",
                "file": {"mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                "webUrl": "https://onedrive.live.com/file/x1",
            }
        )
        assert item.is_folder is False
        assert item.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_extra_fields_ignored(self) -> None:
        item = DriveItemSummary.model_validate({"id": "x", "name": "n", "unexpected": True})
        assert item.id == "x"


class TestListFilesResult:
    def test_str_with_items(self) -> None:
        result = ListFilesResult(
            success=True,
            folder_path="Documents",
            items=[
                DriveItemSummary(id="f1", name="Reports", is_folder=True, child_count=2),
                DriveItemSummary(id="x1", name="budget.xlsx", is_folder=False),
            ],
        )
        text = str(result)
        assert "/Documents" in text
        assert "[folder] Reports" in text
        assert "budget.xlsx" in text

    def test_str_root_when_empty(self) -> None:
        result = ListFilesResult(success=True, folder_path="", items=[])
        text = str(result)
        assert "(root)" in text
        assert "no files or folders" in text

    def test_str_has_more(self) -> None:
        result = ListFilesResult(
            success=True,
            folder_path="Docs",
            items=[DriveItemSummary(id="x1", name="a.txt")],
            has_more=True,
        )
        assert "More items available" in str(result)

    def test_str_on_error(self) -> None:
        result = ListFilesResult(success=False, error="boom")
        assert str(result) == "Error: boom"


class TestSearchResult:
    def test_str_with_items(self) -> None:
        result = SearchResult(
            success=True,
            query="budget",
            items=[DriveItemSummary(id="x1", name="budget.xlsx")],
        )
        text = str(result)
        assert 'Results for "budget"' in text
        assert "budget.xlsx" in text

    def test_str_empty(self) -> None:
        result = SearchResult(success=True, query="zzz", items=[])
        assert 'No files found matching "zzz"' in str(result)

    def test_str_on_error(self) -> None:
        result = SearchResult(success=False, error="fail")
        assert str(result) == "Error: fail"


class TestGetFileInfoResult:
    def test_str_full(self) -> None:
        result = GetFileInfoResult(
            success=True,
            file=FileInfo(
                id="x1",
                name="Report.pdf",
                size=2_097_152,
                last_modified="2024-03-15T10:30:00Z",
                web_url="https://onedrive.live.com/view/x1",
                download_url="https://downloads/x1",
            ),
        )
        text = str(result)
        assert "Report.pdf" in text
        assert "2.0 MB" in text
        assert "2024-03-15" in text
        assert "https://onedrive.live.com/view/x1" in text

    def test_str_no_file(self) -> None:
        result = GetFileInfoResult(success=True, file=None)
        assert "No file metadata available" in str(result)

    def test_str_on_error(self) -> None:
        result = GetFileInfoResult(success=False, error="bad")
        assert str(result) == "Error: bad"

    def test_size_formatting_small(self) -> None:
        result = GetFileInfoResult(success=True, file=FileInfo(id="x", name="a", size=512))
        assert "512 bytes" in str(result)


class TestCreateFolderResult:
    def test_str_output(self) -> None:
        result = CreateFolderResult(
            success=True,
            folder_id="f1",
            name="Reports",
            web_url="https://onedrive.live.com/view/f1",
        )
        text = str(result)
        assert "Reports" in text
        assert "f1" in text
        assert "https://onedrive.live.com/view/f1" in text

    def test_str_on_error(self) -> None:
        result = CreateFolderResult(success=False, error="conflict")
        assert str(result) == "Error: conflict"


class TestMoveFilesResult:
    def test_str_mixed(self) -> None:
        result = MoveFilesResult(
            success=True,
            outcomes=[
                MoveFileOutcome(
                    item_id="a",
                    success=True,
                    name="ok.txt",
                    web_url="https://onedrive.live.com/view/a",
                ),
                MoveFileOutcome(item_id="b", success=False, error="403"),
            ],
        )
        text = str(result)
        assert "Moved 'ok.txt'" in text
        assert "Failed 'b': 403" in text

    def test_str_empty(self) -> None:
        result = MoveFilesResult(success=True, outcomes=[])
        assert "No items were moved" in str(result)

    def test_str_on_error(self) -> None:
        result = MoveFilesResult(success=False, error="nope")
        assert str(result) == "Error: nope"
