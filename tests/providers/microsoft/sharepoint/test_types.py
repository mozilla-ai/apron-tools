"""Tests for Microsoft SharePoint provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.microsoft.sharepoint.types import (
    CreateFolderParams,
    CreateFolderResult,
    DriveInfo,
    DriveItem,
    ExploreDriveParams,
    ExploreDriveResult,
    ListDrivesParams,
    ListDrivesResult,
    ListSitesParams,
    ListSitesResult,
    MoveFileParams,
    MoveFileResult,
    SearchParams,
    SearchResult,
    SiteInfo,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListSitesParams:
    def test_defaults(self):
        params = ListSitesParams()
        assert params.query == ""
        assert params.limit == 25

    def test_custom(self):
        params = ListSitesParams(query="marketing", limit=10)
        assert params.query == "marketing"
        assert params.limit == 10


class TestListDrivesParams:
    def test_required(self):
        params = ListDrivesParams(site_id="site-001")
        assert params.site_id == "site-001"


class TestExploreDriveParams:
    def test_defaults(self):
        params = ExploreDriveParams(drive_id="drive-001")
        assert params.drive_id == "drive-001"
        assert params.folder_path == ""
        assert params.limit == 25

    def test_custom(self):
        params = ExploreDriveParams(drive_id="drive-001", folder_path="Reports/2024", limit=50)
        assert params.folder_path == "Reports/2024"
        assert params.limit == 50


class TestCreateFolderParams:
    def test_required(self):
        params = CreateFolderParams(drive_id="drive-001", folder_name="Archive")
        assert params.drive_id == "drive-001"
        assert params.folder_name == "Archive"
        assert params.parent_path == ""

    def test_with_parent_path(self):
        params = CreateFolderParams(drive_id="drive-001", folder_name="2024", parent_path="Reports")
        assert params.parent_path == "Reports"


class TestSearchParams:
    def test_required(self):
        params = SearchParams(drive_id="drive-001", query="budget")
        assert params.drive_id == "drive-001"
        assert params.query == "budget"
        assert params.limit == 25

    def test_custom_limit(self):
        params = SearchParams(drive_id="drive-001", query="report", limit=10)
        assert params.limit == 10


class TestMoveFileParams:
    def test_required(self):
        params = MoveFileParams(drive_id="drive-001", item_id="item-002", destination_folder_id="item-003")
        assert params.drive_id == "drive-001"
        assert params.item_id == "item-002"
        assert params.destination_folder_id == "item-003"
        assert params.new_name is None

    def test_with_rename(self):
        params = MoveFileParams(
            drive_id="drive-001",
            item_id="item-002",
            destination_folder_id="item-003",
            new_name="renamed.xlsx",
        )
        assert params.new_name == "renamed.xlsx"


# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class TestSiteInfo:
    def test_parse_from_api(self):
        data = _load_json("list_sites.json")
        site = SiteInfo.model_validate(data["value"][0])
        assert site.id == "contoso.sharepoint.com,site-001,web-001"
        assert site.name == "Contoso USA"
        assert site.web_url == "https://contoso.sharepoint.com"
        assert site.is_personal_site is False
        assert site.site_collection is not None
        assert site.site_collection.hostname == "contoso.sharepoint.com"
        assert site.site_collection.data_location_code == "NAM"


class TestDriveInfo:
    def test_parse_from_api(self):
        data = _load_json("list_drives.json")
        drive = DriveInfo.model_validate(data["value"][0])
        assert drive.id == "drive-001"
        assert drive.name == "Documents"
        assert drive.drive_type == "documentLibrary"
        assert drive.web_url == "https://contoso.sharepoint.com/sites/siteA/Documents"
        assert drive.owner is not None
        assert drive.owner.group is not None
        assert drive.owner.group.display_name == "Site A Members"
        assert drive.quota is not None
        assert drive.quota.total == 27487790694400
        assert drive.quota.used == 1234567890


class TestDriveItem:
    def test_parse_folder(self):
        data = _load_json("drive_children.json")
        item = DriveItem.model_validate(data["value"][0])
        assert item.id == "item-001"
        assert item.name == "Reports"
        assert item.folder is not None
        assert item.folder.child_count == 5
        assert item.file is None
        assert item.last_modified_by is not None
        assert item.last_modified_by.user is not None
        assert item.last_modified_by.user.display_name == "Alice Smith"

    def test_parse_file(self):
        data = _load_json("drive_children.json")
        item = DriveItem.model_validate(data["value"][1])
        assert item.id == "item-002"
        assert item.name == "budget.xlsx"
        assert item.file is not None
        assert item.file.mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert item.folder is None
        assert item.size == 12345

    def test_parse_search_result_with_parent_reference(self):
        data = _load_json("search_results.json")
        item = DriveItem.model_validate(data["value"][0])
        assert item.parent_reference is not None
        assert item.parent_reference.path == "/drives/drive-001/root:/Documents"


# ---------------------------------------------------------------------------
# ListSitesResult
# ---------------------------------------------------------------------------


class TestListSitesResult:
    def test_success(self):
        data = _load_json("list_sites.json")
        sites = [SiteInfo.model_validate(s) for s in data["value"]]
        result = ListSitesResult(success=True, sites=sites)
        assert result.success is True
        assert len(result.sites) == 2
        assert result.sites[0].name == "Contoso USA"

    def test_str_output(self):
        data = _load_json("list_sites.json")
        sites = [SiteInfo.model_validate(s) for s in data["value"]]
        result = ListSitesResult(success=True, sites=sites)
        text = str(result)
        assert "2 site(s)" in text
        assert "Contoso USA" in text
        assert "Site A" in text

    def test_str_empty(self):
        result = ListSitesResult(success=True, sites=[])
        assert str(result) == "No sites found."

    def test_str_on_error(self):
        result = ListSitesResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


# ---------------------------------------------------------------------------
# ListDrivesResult
# ---------------------------------------------------------------------------


class TestListDrivesResult:
    def test_success(self):
        data = _load_json("list_drives.json")
        drives = [DriveInfo.model_validate(d) for d in data["value"]]
        result = ListDrivesResult(success=True, drives=drives)
        assert result.success is True
        assert len(result.drives) == 2

    def test_str_output(self):
        data = _load_json("list_drives.json")
        drives = [DriveInfo.model_validate(d) for d in data["value"]]
        result = ListDrivesResult(success=True, drives=drives)
        text = str(result)
        assert "2 drive(s)" in text
        assert "Documents" in text
        assert "documentLibrary" in text

    def test_str_empty(self):
        result = ListDrivesResult(success=True, drives=[])
        assert str(result) == "No drives found."

    def test_str_on_error(self):
        result = ListDrivesResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


# ---------------------------------------------------------------------------
# ExploreDriveResult
# ---------------------------------------------------------------------------


class TestExploreDriveResult:
    def test_success(self):
        data = _load_json("drive_children.json")
        items = [DriveItem.model_validate(i) for i in data["value"]]
        result = ExploreDriveResult(success=True, items=items)
        assert result.success is True
        assert len(result.items) == 2

    def test_str_output(self):
        data = _load_json("drive_children.json")
        items = [DriveItem.model_validate(i) for i in data["value"]]
        result = ExploreDriveResult(success=True, items=items)
        text = str(result)
        assert "2 item(s)" in text
        assert "[folder] Reports" in text
        assert "[file] budget.xlsx" in text

    def test_str_empty(self):
        result = ExploreDriveResult(success=True, items=[])
        assert str(result) == "No items found."

    def test_str_on_error(self):
        result = ExploreDriveResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


# ---------------------------------------------------------------------------
# CreateFolderResult
# ---------------------------------------------------------------------------


class TestCreateFolderResult:
    def test_success(self):
        data = _load_json("create_folder.json")
        folder = DriveItem.model_validate(data)
        result = CreateFolderResult(success=True, folder=folder)
        assert result.success is True
        assert result.folder is not None
        assert result.folder.name == "New Folder"
        assert result.folder.id == "item-003"

    def test_str_output(self):
        data = _load_json("create_folder.json")
        folder = DriveItem.model_validate(data)
        result = CreateFolderResult(success=True, folder=folder)
        text = str(result)
        assert "New Folder" in text
        assert "item-003" in text
        assert "created successfully" in text

    def test_str_no_folder(self):
        result = CreateFolderResult(success=True, folder=None)
        assert str(result) == "Folder created but no details returned."

    def test_str_on_error(self):
        result = CreateFolderResult(success=False, error="Conflict")
        assert str(result) == "Error: Conflict"


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


class TestSearchResult:
    def test_success(self):
        data = _load_json("search_results.json")
        items = [DriveItem.model_validate(i) for i in data["value"]]
        result = SearchResult(success=True, items=items)
        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].name == "budget.xlsx"

    def test_str_output(self):
        data = _load_json("search_results.json")
        items = [DriveItem.model_validate(i) for i in data["value"]]
        result = SearchResult(success=True, items=items)
        text = str(result)
        assert "1 item(s)" in text
        assert "[file] budget.xlsx" in text

    def test_str_empty(self):
        result = SearchResult(success=True, items=[])
        assert str(result) == "No items found."

    def test_str_on_error(self):
        result = SearchResult(success=False, error="Bad request")
        assert str(result) == "Error: Bad request"


# ---------------------------------------------------------------------------
# MoveFileResult
# ---------------------------------------------------------------------------


class TestMoveFileResult:
    def test_success(self):
        data = _load_json("move_file.json")
        item = DriveItem.model_validate(data)
        result = MoveFileResult(success=True, item=item)
        assert result.success is True
        assert result.item is not None
        assert result.item.name == "budget.xlsx"
        assert result.item.parent_reference is not None
        assert result.item.parent_reference.id == "item-003"

    def test_str_output(self):
        data = _load_json("move_file.json")
        item = DriveItem.model_validate(data)
        result = MoveFileResult(success=True, item=item)
        text = str(result)
        assert "budget.xlsx" in text
        assert "moved" in text

    def test_str_no_item(self):
        result = MoveFileResult(success=True, item=None)
        assert str(result) == "Item moved but no details returned."

    def test_str_on_error(self):
        result = MoveFileResult(success=False, error="Item not found")
        assert str(result) == "Error: Item not found"
