"""Tests for Notion provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from any_tool.providers.notion.types import (
    BlockObject,
    CreateDatabaseParams,
    CreateDatabaseResult,
    CreateOrUpdateDatabaseEntryParams,
    CreateOrUpdateDatabaseEntryResult,
    CreatePageParams,
    CreatePageResult,
    DatabaseObject,
    ExploreTeamspaceParams,
    ExploreTeamspaceResult,
    GetDatabaseEntryParams,
    GetDatabaseEntryResult,
    GetDatabaseSchemaParams,
    GetDatabaseSchemaResult,
    PageObject,
    QueryDatabaseParams,
    QueryDatabaseResult,
    ReadPageParams,
    ReadPageResult,
    UpdateDatabaseSchemaParams,
    UpdateDatabaseSchemaResult,
    UpdatePageParams,
    UpdatePageResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreTeamspaceParams:
    def test_defaults(self):
        params = ExploreTeamspaceParams()
        assert params.page_size == 100

    def test_custom_values(self):
        params = ExploreTeamspaceParams(page_size=50)
        assert params.page_size == 50


class TestCreatePageParams:
    def test_required_fields(self):
        params = CreatePageParams(parent_page_id="abc123", title="My Page")
        assert params.parent_page_id == "abc123"
        assert params.title == "My Page"
        assert params.content == ""

    def test_with_content(self):
        params = CreatePageParams(parent_page_id="abc123", title="My Page", content="# Hello")
        assert params.content == "# Hello"


class TestUpdatePageParams:
    def test_required_fields(self):
        params = UpdatePageParams(page_id="abc123", content="New content")
        assert params.page_id == "abc123"
        assert params.content == "New content"


class TestReadPageParams:
    def test_required_fields(self):
        params = ReadPageParams(page_id="abc123")
        assert params.page_id == "abc123"


class TestGetDatabaseSchemaParams:
    def test_required_fields(self):
        params = GetDatabaseSchemaParams(database_id="db123")
        assert params.database_id == "db123"


class TestQueryDatabaseParams:
    def test_defaults(self):
        params = QueryDatabaseParams(data_source_id="ds-001")
        assert params.data_source_id == "ds-001"
        assert params.page_size == 100
        assert params.filter is None
        assert params.sorts is None

    def test_custom_values(self):
        params = QueryDatabaseParams(
            data_source_id="ds-001",
            filter={"property": "Status", "select": {"equals": "Done"}},
            sorts=[{"property": "Name", "direction": "ascending"}],
            page_size=50,
        )
        assert params.filter is not None
        assert params.sorts is not None
        assert params.page_size == 50


class TestGetDatabaseEntryParams:
    def test_required_fields(self):
        params = GetDatabaseEntryParams(page_id="page123")
        assert params.page_id == "page123"


class TestCreateOrUpdateDatabaseEntryParams:
    def test_create_mode(self):
        params = CreateOrUpdateDatabaseEntryParams(
            database_id="db123",
            properties={"Name": {"title": [{"text": {"content": "Task 1"}}]}},
        )
        assert params.database_id == "db123"
        assert params.page_id is None

    def test_update_mode(self):
        params = CreateOrUpdateDatabaseEntryParams(
            page_id="page123",
            properties={"Status": {"select": {"name": "Done"}}},
        )
        assert params.page_id == "page123"


class TestCreateDatabaseParams:
    def test_required_fields(self):
        params = CreateDatabaseParams(parent_page_id="page123", title="My DB")
        assert params.parent_page_id == "page123"
        assert params.title == "My DB"
        assert params.properties is None
        assert params.description == ""


class TestUpdateDatabaseSchemaParams:
    def test_required_fields(self):
        params = UpdateDatabaseSchemaParams(database_id="db123")
        assert params.database_id == "db123"
        assert params.title is None
        assert params.properties is None
        assert params.description is None


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class TestPageObject:
    def test_parse_from_api(self):
        data = _load_json("retrieve_page.json")
        page = PageObject.model_validate(data)

        assert page.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert page.object == "page"
        assert page.in_trash is False
        assert page.title == "Project Notes"

    def test_title_extraction(self):
        data = _load_json("retrieve_page.json")
        page = PageObject.model_validate(data)
        assert page.title == "Project Notes"

    def test_title_fallback(self):
        page = PageObject(properties={})
        assert page.title == "Untitled"


class TestBlockObject:
    def test_paragraph_block(self):
        data = _load_json("block_children.json")
        block = BlockObject.model_validate(data["results"][0])

        assert block.type == "paragraph"
        assert block.text_content == "This is the first paragraph of the page."

    def test_heading_block(self):
        data = _load_json("block_children.json")
        block = BlockObject.model_validate(data["results"][1])

        assert block.type == "heading_2"
        assert block.text_content == "Section Title"

    def test_bulleted_list_block(self):
        data = _load_json("block_children.json")
        block = BlockObject.model_validate(data["results"][2])

        assert block.type == "bulleted_list_item"
        assert block.text_content == "First item"

    def test_todo_block(self):
        data = _load_json("block_children.json")
        block = BlockObject.model_validate(data["results"][3])

        assert block.type == "to_do"
        assert block.text_content == "Complete the report"

    def test_divider_block(self):
        block = BlockObject(type="divider", divider={})
        assert block.text_content == "---"

    def test_unknown_block_type(self):
        block = BlockObject(type="image")
        assert block.text_content == ""


class TestDatabaseObject:
    def test_parse_from_api(self):
        data = _load_json("retrieve_database.json")
        db = DatabaseObject.model_validate(data)

        assert db.id == "d4e5f6a7-b8c9-0123-defa-b45678901234"
        assert db.title_text == "Tasks"
        assert "Name" in db.properties
        assert "Status" in db.properties
        assert len(db.data_sources) == 1
        assert db.data_sources[0].id == "ds-tasks-001"

    def test_title_fallback(self):
        db = DatabaseObject(title=[])
        assert db.title_text == "Untitled"


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class TestExploreTeamspaceResult:
    def test_success_str(self):
        pages = [PageObject.model_validate(p) for p in _load_json("search_pages.json")["results"]]
        dbs = [DatabaseObject.model_validate(d) for d in _load_json("search_databases.json")["results"]]
        result = ExploreTeamspaceResult(success=True, pages=pages, databases=dbs)

        text = str(result)
        assert "# Notion Workspace" in text
        assert "Project Notes" in text
        assert "Tasks" in text

    def test_error_str(self):
        result = ExploreTeamspaceResult(success=False, error="Unauthorized")
        assert str(result) == "Error: Unauthorized"


class TestCreatePageResult:
    def test_parse_api_response(self):
        data = _load_json("create_page.json")
        result = CreatePageResult.model_validate(data)

        assert result.success is True
        assert result.id == "e7f8a9b0-c1d2-3456-efab-cd7890123456"
        assert "Sprint-Planning" in result.url

    def test_str_output(self):
        data = _load_json("create_page.json")
        result = CreatePageResult.model_validate(data)
        text = str(result)

        assert "Page created" in text
        assert result.id in text

    def test_str_on_error(self):
        result = CreatePageResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"


class TestUpdatePageResult:
    def test_success(self):
        result = UpdatePageResult(success=True, page_id="abc123", blocks_appended=3)

        assert result.success is True
        assert result.page_id == "abc123"
        assert result.blocks_appended == 3

    def test_str_output(self):
        result = UpdatePageResult(success=True, page_id="abc123", blocks_appended=3)
        text = str(result)

        assert "abc123" in text
        assert "3 block(s) appended" in text

    def test_str_on_error(self):
        result = UpdatePageResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


class TestReadPageResult:
    def test_success(self):
        page = PageObject.model_validate(_load_json("retrieve_page.json"))
        blocks = [BlockObject.model_validate(b) for b in _load_json("block_children.json")["results"]]
        result = ReadPageResult(success=True, page=page, blocks=blocks)

        assert result.success is True
        assert result.page is not None
        assert len(result.blocks) == 4

    def test_str_output(self):
        page = PageObject.model_validate(_load_json("retrieve_page.json"))
        blocks = [BlockObject.model_validate(b) for b in _load_json("block_children.json")["results"]]
        result = ReadPageResult(success=True, page=page, blocks=blocks)
        text = str(result)

        assert "# Project Notes" in text
        assert "This is the first paragraph of the page." in text

    def test_str_on_error(self):
        result = ReadPageResult(success=False, error="Page not found")
        assert str(result) == "Error: Page not found"

    def test_str_no_page(self):
        result = ReadPageResult(success=True)
        assert str(result) == "No page data."


class TestGetDatabaseSchemaResult:
    def test_parse_database(self):
        db = DatabaseObject.model_validate(_load_json("retrieve_database.json"))
        result = GetDatabaseSchemaResult(success=True, database=db)

        assert result.success is True
        assert result.database is not None
        assert result.database.title_text == "Tasks"

    def test_str_output(self):
        db = DatabaseObject.model_validate(_load_json("retrieve_database.json"))
        result = GetDatabaseSchemaResult(success=True, database=db)
        text = str(result)

        assert "# Database: Tasks" in text
        assert "Name" in text
        assert "Status" in text
        assert "type: select" in text

    def test_str_on_error(self):
        result = GetDatabaseSchemaResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_no_database(self):
        result = GetDatabaseSchemaResult(success=True)
        assert str(result) == "No database data."


class TestQueryDatabaseResult:
    def test_parse_api_response(self):
        data = _load_json("query_data_source.json")
        results = [PageObject.model_validate(p) for p in data["results"]]
        result = QueryDatabaseResult(
            success=True,
            results=results,
            has_more=data["has_more"],
            next_cursor=data["next_cursor"],
        )

        assert result.success is True
        assert len(result.results) == 2
        assert result.has_more is True
        assert result.next_cursor == "v1-abc123-cursor"

    def test_str_output(self):
        data = _load_json("query_data_source.json")
        results = [PageObject.model_validate(p) for p in data["results"]]
        result = QueryDatabaseResult(
            success=True,
            results=results,
            has_more=True,
            next_cursor="v1-abc123-cursor",
        )
        text = str(result)

        assert "2 entry/entries" in text
        assert "Implement auth flow" in text
        assert "More results available" in text

    def test_str_on_error(self):
        result = QueryDatabaseResult(success=False, error="Bad request")
        assert str(result) == "Error: Bad request"


class TestGetDatabaseEntryResult:
    def test_success(self):
        page = PageObject.model_validate(_load_json("retrieve_page.json"))
        blocks = [BlockObject.model_validate(b) for b in _load_json("block_children.json")["results"]]
        result = GetDatabaseEntryResult(success=True, page=page, blocks=blocks)

        assert result.success is True
        assert result.page is not None
        assert len(result.blocks) == 4

    def test_str_output(self):
        page = PageObject.model_validate(_load_json("retrieve_page.json"))
        result = GetDatabaseEntryResult(success=True, page=page, blocks=[])
        text = str(result)

        assert "Entry: Project Notes" in text

    def test_str_on_error(self):
        result = GetDatabaseEntryResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"

    def test_str_no_entry(self):
        result = GetDatabaseEntryResult(success=True)
        assert str(result) == "No entry data."


class TestCreateOrUpdateDatabaseEntryResult:
    def test_parse_create_response(self):
        data = _load_json("create_page_entry.json")
        result = CreateOrUpdateDatabaseEntryResult.model_validate(data)

        assert result.success is True
        assert result.id == "b1c2d3e4-f5a6-7890-bcde-f01234567890"

    def test_parse_update_response(self):
        data = _load_json("update_page_entry.json")
        result = CreateOrUpdateDatabaseEntryResult.model_validate(data)

        assert result.success is True
        assert result.id == "f8a9b0c1-d2e3-4567-abcd-ef8901234567"

    def test_str_output(self):
        data = _load_json("create_page_entry.json")
        result = CreateOrUpdateDatabaseEntryResult.model_validate(data)
        text = str(result)

        assert "Database entry saved" in text
        assert result.id in text

    def test_str_on_error(self):
        result = CreateOrUpdateDatabaseEntryResult(success=False, error="Validation error")
        assert str(result) == "Error: Validation error"


class TestCreateDatabaseResult:
    def test_parse_api_response(self):
        data = _load_json("create_database.json")
        result = CreateDatabaseResult.model_validate(data)

        assert result.success is True
        assert result.id == "c8d9e0f1-a2b3-4567-cdef-a12345678901"
        assert result.title_text == "Bug Tracker"

    def test_str_output(self):
        data = _load_json("create_database.json")
        result = CreateDatabaseResult.model_validate(data)
        text = str(result)

        assert "Database created" in text
        assert "Bug Tracker" in text
        assert result.id in text

    def test_str_on_error(self):
        result = CreateDatabaseResult(success=False, error="Permission denied")
        assert str(result) == "Error: Permission denied"


class TestUpdateDatabaseSchemaResult:
    def test_parse_api_response(self):
        data = _load_json("update_database.json")
        result = UpdateDatabaseSchemaResult.model_validate(data)

        assert result.success is True
        assert result.id == "d4e5f6a7-b8c9-0123-defa-b45678901234"
        assert result.title_text == "Tasks (Updated)"

    def test_str_output(self):
        data = _load_json("update_database.json")
        result = UpdateDatabaseSchemaResult.model_validate(data)
        text = str(result)

        assert "Database updated" in text
        assert "Tasks (Updated)" in text

    def test_str_on_error(self):
        result = UpdateDatabaseSchemaResult(success=False, error="Not found")
        assert str(result) == "Error: Not found"


class TestEmbedExternalFileTypes:
    def test_params_defaults(self):
        from any_tool.providers.notion.types import EmbedExternalFileParams

        params = EmbedExternalFileParams(page_id="page-001", url="https://example.com/image.png")
        assert params.caption == ""
        assert params.file_type == "auto"

    def test_params_custom(self):
        from any_tool.providers.notion.types import EmbedExternalFileParams

        params = EmbedExternalFileParams(
            page_id="page-001", url="https://example.com/doc.pdf", caption="My file", file_type="file"
        )
        assert params.file_type == "file"
        assert params.caption == "My file"

    def test_result_success(self):
        from any_tool.providers.notion.types import EmbedExternalFileResult

        result = EmbedExternalFileResult(
            success=True, block_type="image", file_url="https://example.com/img.png", page_id="page-001"
        )
        assert result.success is True
        assert "image" in str(result)
        assert "page-001" in str(result)

    def test_result_error(self):
        from any_tool.providers.notion.types import EmbedExternalFileResult

        result = EmbedExternalFileResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"
