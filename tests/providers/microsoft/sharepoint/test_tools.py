"""Tests for Microsoft SharePoint tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from apron_tools.providers.microsoft.sharepoint.tools import (
    microsoft_sharepoint_create_folder,
    microsoft_sharepoint_explore_drive,
    microsoft_sharepoint_list_drives,
    microsoft_sharepoint_list_sites,
    microsoft_sharepoint_move_files,
    microsoft_sharepoint_search,
)
from apron_tools.providers.microsoft.sharepoint.types import (
    CreateFolderParams,
    CreateFolderResult,
    ExploreDriveParams,
    ExploreDriveResult,
    ListDrivesParams,
    ListDrivesResult,
    ListSitesParams,
    ListSitesResult,
    MoveFilesParams,
    MoveFilesResult,
    SearchParams,
    SearchResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_SITE_ID = "contoso.sharepoint.com,site-001,web-001"
_DRIVE_ID = "drive-001"
_ITEM_ID = "item-002"
_FOLDER_ID = "item-003"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_sites
# ---------------------------------------------------------------------------


class TestListSites:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/sites?search=%2A&%24top=25",
            json=_load_json("list_sites.json"),
        )

        result = await microsoft_sharepoint_list_sites(ListSitesParams(), token=_TOKEN)

        assert isinstance(result, ListSitesResult)
        assert result.success is True
        assert len(result.sites) == 2
        assert result.sites[0].name == "Contoso USA"
        assert result.sites[1].name == "Site A"

    async def test_with_query(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/sites?search=marketing&%24top=10",
            json=_load_json("list_sites.json"),
        )

        result = await microsoft_sharepoint_list_sites(ListSitesParams(query="marketing", limit=10), token=_TOKEN)

        assert result.success is True
        assert len(result.sites) == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=401, text="Unauthorized")

        result = await microsoft_sharepoint_list_sites(ListSitesParams(), token=_TOKEN)

        assert result.success is False
        assert "401" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_list_sites._tool_definition
        assert defn.name == "microsoft_sharepoint_list_sites"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Sites.Read.All" in defn.scopes


# ---------------------------------------------------------------------------
# list_drives
# ---------------------------------------------------------------------------


class TestListDrives:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/sites/{_SITE_ID}/drives",
            json=_load_json("list_drives.json"),
        )

        result = await microsoft_sharepoint_list_drives(ListDrivesParams(site_id=_SITE_ID), token=_TOKEN)

        assert isinstance(result, ListDrivesResult)
        assert result.success is True
        assert len(result.drives) == 2
        assert result.drives[0].name == "Documents"
        assert result.drives[0].drive_type == "documentLibrary"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_sharepoint_list_drives(ListDrivesParams(site_id="bad-site-id"), token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_list_drives._tool_definition
        assert defn.name == "microsoft_sharepoint_list_drives"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Sites.Read.All" in defn.scopes


# ---------------------------------------------------------------------------
# explore_drive
# ---------------------------------------------------------------------------


class TestExploreDrive:
    async def test_success_root(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/root/children?%24top=25&%24orderby=name",
            json=_load_json("drive_children.json"),
        )

        result = await microsoft_sharepoint_explore_drive(ExploreDriveParams(drive_id=_DRIVE_ID), token=_TOKEN)

        assert isinstance(result, ExploreDriveResult)
        assert result.success is True
        assert len(result.items) == 2
        assert result.items[0].name == "Reports"
        assert result.items[0].folder is not None
        assert result.items[1].name == "budget.xlsx"
        assert result.items[1].file is not None

    async def test_success_subfolder(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/root:/Reports:/children?%24top=25&%24orderby=name",
            json={"value": []},
        )

        result = await microsoft_sharepoint_explore_drive(
            ExploreDriveParams(drive_id=_DRIVE_ID, folder_path="Reports"), token=_TOKEN
        )

        assert result.success is True
        assert len(result.items) == 0

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await microsoft_sharepoint_explore_drive(ExploreDriveParams(drive_id="bad-drive"), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_explore_drive._tool_definition
        assert defn.name == "microsoft_sharepoint_explore_drive"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Files.ReadWrite.All" in defn.scopes


# ---------------------------------------------------------------------------
# create_folder
# ---------------------------------------------------------------------------


class TestCreateFolder:
    async def test_success_root(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/root/children",
            json=_load_json("create_folder.json"),
        )

        result = await microsoft_sharepoint_create_folder(
            CreateFolderParams(drive_id=_DRIVE_ID, folder_name="New Folder"),
            token=_TOKEN,
        )

        assert isinstance(result, CreateFolderResult)
        assert result.success is True
        assert result.folder is not None
        assert result.folder.name == "New Folder"
        assert result.folder.id == "item-003"

    async def test_success_with_parent_path(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/root:/Reports:/children",
            json=_load_json("create_folder.json"),
        )

        result = await microsoft_sharepoint_create_folder(
            CreateFolderParams(drive_id=_DRIVE_ID, folder_name="New Folder", parent_path="Reports"),
            token=_TOKEN,
        )

        assert result.success is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=409, text="Conflict")

        result = await microsoft_sharepoint_create_folder(
            CreateFolderParams(drive_id=_DRIVE_ID, folder_name="Existing"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "409" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_create_folder._tool_definition
        assert defn.name == "microsoft_sharepoint_create_folder"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Files.ReadWrite.All" in defn.scopes


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/root/search(q='budget')?%24top=25",
            json=_load_json("search_results.json"),
        )

        result = await microsoft_sharepoint_search(SearchParams(drive_id=_DRIVE_ID, query="budget"), token=_TOKEN)

        assert isinstance(result, SearchResult)
        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].name == "budget.xlsx"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await microsoft_sharepoint_search(SearchParams(drive_id=_DRIVE_ID, query=""), token=_TOKEN)

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_search._tool_definition
        assert defn.name == "microsoft_sharepoint_search"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Files.ReadWrite.All" in defn.scopes


# ---------------------------------------------------------------------------
# move_file
# ---------------------------------------------------------------------------


class TestMoveFiles:
    async def test_single_item(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}?%24select=id%2Cname",
            json=_load_json("get_item.json"),
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}",
            json=_load_json("move_file.json"),
        )

        result = await microsoft_sharepoint_move_files(
            MoveFilesParams(
                drive_id=_DRIVE_ID,
                item_ids=_ITEM_ID,
                destination_folder_id=_FOLDER_ID,
            ),
            token=_TOKEN,
        )

        assert isinstance(result, MoveFilesResult)
        assert result.success is True
        assert result.destination_folder_id == _FOLDER_ID
        assert len(result.items) == 1
        entry = result.items[0]
        assert entry.success is True
        assert entry.item is not None
        assert entry.item.name == "budget.xlsx"
        assert entry.item.parent_reference is not None
        assert entry.item.parent_reference.id == _FOLDER_ID

    async def test_multiple_items(self, httpx_mock: HTTPXMock) -> None:
        for _ in range(2):
            httpx_mock.add_response(
                method="GET",
                json=_load_json("get_item.json"),
            )
            httpx_mock.add_response(
                method="PATCH",
                json=_load_json("move_file.json"),
            )

        result = await microsoft_sharepoint_move_files(
            MoveFilesParams(
                drive_id=_DRIVE_ID,
                item_ids=f"{_ITEM_ID}, item-other",
                destination_folder_id=_FOLDER_ID,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert [entry.item_id for entry in result.items] == [_ITEM_ID, "item-other"]
        assert all(entry.success for entry in result.items)

    async def test_partial_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}?%24select=id%2Cname",
            json=_load_json("get_item.json"),
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}",
            json=_load_json("move_file.json"),
        )
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await microsoft_sharepoint_move_files(
            MoveFilesParams(
                drive_id=_DRIVE_ID,
                item_ids=f"{_ITEM_ID},bad-item",
                destination_folder_id=_FOLDER_ID,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is True
        assert result.items[1].success is False
        assert "404" in result.items[1].error

    async def test_empty_item_ids(self) -> None:
        result = await microsoft_sharepoint_move_files(
            MoveFilesParams(
                drive_id=_DRIVE_ID,
                item_ids=" , ",
                destination_folder_id=_FOLDER_ID,
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error == "No item IDs provided."

    async def test_patch_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}?%24select=id%2Cname",
            json=_load_json("get_item.json"),
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{_GRAPH_BASE}/drives/{_DRIVE_ID}/items/{_ITEM_ID}",
            status_code=403,
            text="Forbidden",
        )

        result = await microsoft_sharepoint_move_files(
            MoveFilesParams(
                drive_id=_DRIVE_ID,
                item_ids=_ITEM_ID,
                destination_folder_id=_FOLDER_ID,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.items[0].success is False
        assert "403" in result.items[0].error

    async def test_has_tool_definition(self) -> None:
        defn = microsoft_sharepoint_move_files._tool_definition
        assert defn.name == "microsoft_sharepoint_move_files"
        assert defn.provider == "microsoft"
        assert defn.service == "microsoft_sharepoint"
        assert "Files.ReadWrite.All" in defn.scopes
