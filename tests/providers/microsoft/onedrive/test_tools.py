"""Tests for Microsoft OneDrive tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.onedrive.tools import (
    microsoft_onedrive_create_folder,
    microsoft_onedrive_get_file_info,
    microsoft_onedrive_list_files,
    microsoft_onedrive_move_files,
    microsoft_onedrive_search,
)
from apron_tools.providers.microsoft.onedrive.types import (
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
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------


class TestListFiles:
    async def test_success_root(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/children?%24top=25&%24orderby=name&%24select=id%2Cname%2Cfile%2Cfolder%2CwebUrl",
            json=_load_json("list_files.json"),
        )

        result = await microsoft_onedrive_list_files(ListFilesParams(), token=_TOKEN)

        assert isinstance(result, ListFilesResult)
        assert result.success is True
        assert len(result.items) == 3
        assert result.items[0].name == "Documents"
        assert result.items[0].is_folder is True
        assert result.items[0].child_count == 4
        assert result.items[1].name == "Budget.xlsx"
        assert result.items[1].is_folder is False
        assert result.has_more is False

    async def test_success_subfolder(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root:/Documents/Reports:/children?%24top=25&%24orderby=name&%24select=id%2Cname%2Cfile%2Cfolder%2CwebUrl",
            json={"value": [], "@odata.nextLink": "https://next.page"},
        )

        result = await microsoft_onedrive_list_files(
            ListFilesParams(folder_path="Documents/Reports"),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.folder_path == "Documents/Reports"
        assert result.has_more is True

    async def test_limit_capped(self, httpx_mock: HTTPXMock) -> None:
        """Limit is capped at 100 regardless of requested value."""
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/children?%24top=100&%24orderby=name&%24select=id%2Cname%2Cfile%2Cfolder%2CwebUrl",
            json={"value": []},
        )

        result = await microsoft_onedrive_list_files(ListFilesParams(limit=500), token=_TOKEN)

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await microsoft_onedrive_list_files(ListFilesParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None and "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_onedrive_list_files._tool_definition
        assert defn.name == "microsoft_onedrive_list_files"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_onedrive"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='contoso')?%24top=25&%24select=id%2Cname%2Cfile%2Cfolder%2CwebUrl",
            json=_load_json("search_results.json"),
        )

        result = await microsoft_onedrive_search(SearchParams(query="contoso"), token=_TOKEN)

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert result.query == "contoso"
        assert len(result.items) == 2
        assert result.items[0].is_folder is True
        assert result.items[1].name == "Contoso Project 2016.xlsx"

    async def test_escapes_single_quotes(self, httpx_mock: HTTPXMock) -> None:
        """OData single quotes in the query are doubled before URL-encoding."""
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/root/search(q='o%27%27brien')?%24top=25&%24select=id%2Cname%2Cfile%2Cfolder%2CwebUrl",
            json={"value": []},
        )

        result = await microsoft_onedrive_search(SearchParams(query="o'brien"), token=_TOKEN)

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await microsoft_onedrive_search(SearchParams(query="x"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None and "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_onedrive_search._tool_definition
        assert defn.name == "microsoft_onedrive_search"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_onedrive"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# get_file_info
# ---------------------------------------------------------------------------


class TestGetFileInfo:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/me/drive/items/file-001?%24select=id%2Cname%2Csize%2ClastModifiedDateTime%2CwebUrl%2Cfile%2C%40microsoft.graph.downloadUrl",
            json=_load_json("get_file_info.json"),
        )

        result = await microsoft_onedrive_get_file_info(GetFileInfoParams(item_id="file-001"), token=_TOKEN)

        assert isinstance(result, GetFileInfoResult)
        assert result.success is True
        assert result.file is not None
        assert result.file.id == "file-001"
        assert result.file.name == "Budget.xlsx"
        assert result.file.size == 48332
        assert result.file.download_url == "https://graph.microsoft.com/download/file-001"

    async def test_not_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_onedrive_get_file_info(GetFileInfoParams(item_id="bad-id"), token=_TOKEN)

        assert result.success is False
        assert result.error is not None and "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_onedrive_get_file_info._tool_definition
        assert defn.name == "microsoft_onedrive_get_file_info"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_onedrive"
        assert "Files.Read" in defn.scopes


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


class TestCreateFolder:
    async def test_success_root(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"{_GRAPH_BASE}/me/drive/root/children",
            json=_load_json("create_folder.json"),
        )

        result = await microsoft_onedrive_create_folder(
            CreateFolderParams(folder_name="New Folder"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateFolderResult)
        assert result.success is True
        assert result.folder_id == "ACEA49D1-1444-45A9-A1CB-68B1B28AE491"
        assert result.name == "New Folder"

    async def test_success_with_parent_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"{_GRAPH_BASE}/me/drive/root:/Documents/Projects:/children",
            json=_load_json("create_folder.json"),
        )

        result = await microsoft_onedrive_create_folder(
            CreateFolderParams(folder_name="New Folder", parent_path="Documents/Projects"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(method="POST", status_code=409, text="Conflict")

        result = await microsoft_onedrive_create_folder(
            CreateFolderParams(folder_name="Existing"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error is not None and "409" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_onedrive_create_folder._tool_definition
        assert defn.name == "microsoft_onedrive_create_folder"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_onedrive"
        assert "Files.ReadWrite" in defn.scopes


# ---------------------------------------------------------------------------
# move_files
# ---------------------------------------------------------------------------


class TestMoveFiles:
    async def test_success_single(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001?%24select=id%2Cname",
            json=_load_json("get_item_name.json"),
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001",
            json=_load_json("move_item.json"),
        )

        result = await microsoft_onedrive_move_files(
            MoveFilesParams(item_ids=["file-001"], destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert isinstance(result, MoveFilesResult)
        assert result.success is True
        assert len(result.outcomes) == 1
        assert result.outcomes[0].success is True
        assert result.outcomes[0].name == "Budget.xlsx"
        assert result.outcomes[0].web_url == "https://onedrive.live.com/view/folder-002/Budget.xlsx"

    async def test_success_with_new_name_single(self, httpx_mock: HTTPXMock) -> None:
        """new_name is applied when moving a single item."""
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001?%24select=id%2Cname",
            json=_load_json("get_item_name.json"),
        )
        renamed = _load_json("move_item.json") | {"name": "Renamed.xlsx"}
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001",
            json=renamed,
            match_json={
                "parentReference": {"id": "folder-002"},
                "name": "Renamed.xlsx",
            },
        )

        result = await microsoft_onedrive_move_files(
            MoveFilesParams(
                item_ids=["file-001"],
                destination_folder_id="folder-002",
                new_name="Renamed.xlsx",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.outcomes[0].name == "Renamed.xlsx"

    async def test_new_name_ignored_for_bulk(self, httpx_mock: HTTPXMock) -> None:
        """new_name is ignored when moving multiple items."""
        for iid in ("file-001", "file-002"):
            httpx_mock.add_response(
                method="GET",
                url=f"{_GRAPH_BASE}/me/drive/items/{iid}?%24select=id%2Cname",
                json={"id": iid, "name": f"{iid}.bin"},
            )
            httpx_mock.add_response(
                method="PATCH",
                url=f"{_GRAPH_BASE}/me/drive/items/{iid}",
                json={"id": iid, "name": f"{iid}.bin", "webUrl": f"https://onedrive.live.com/view/{iid}"},
                match_json={"parentReference": {"id": "folder-002"}},
            )

        result = await microsoft_onedrive_move_files(
            MoveFilesParams(
                item_ids=["file-001", "file-002"],
                destination_folder_id="folder-002",
                new_name="Should-Be-Ignored.xlsx",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.outcomes) == 2

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        """One item's failure does not abort the batch."""
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001?%24select=id%2Cname",
            json={"id": "file-001", "name": "Budget.xlsx"},
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/me/drive/items/file-001",
            json={"id": "file-001", "name": "Budget.xlsx", "webUrl": "https://onedrive.live.com/view/file-001"},
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/me/drive/items/bad-id?%24select=id%2Cname",
            status_code=404,
            text="Not Found",
        )

        result = await microsoft_onedrive_move_files(
            MoveFilesParams(
                item_ids=["file-001", "bad-id"],
                destination_folder_id="folder-002",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert len(result.outcomes) == 2
        assert result.outcomes[0].success is True
        assert result.outcomes[1].success is False
        assert result.outcomes[1].error is not None and "404" in result.outcomes[1].error

    async def test_empty_destination_rejected(self) -> None:
        result = await microsoft_onedrive_move_files(
            MoveFilesParams(item_ids=["file-001"], destination_folder_id="   "),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error is not None and "destination_folder_id" in result.error

    async def test_empty_items_rejected(self) -> None:
        result = await microsoft_onedrive_move_files(
            MoveFilesParams(item_ids=[], destination_folder_id="folder-002"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error is not None and "item_id" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_onedrive_move_files._tool_definition
        assert defn.name == "microsoft_onedrive_move_files"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_onedrive"
        assert "Files.ReadWrite" in defn.scopes
