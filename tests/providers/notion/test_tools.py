"""Tests for Notion tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.notion.tools import (
    notion_create_database,
    notion_create_or_update_database_entry,
    notion_create_page,
    notion_explore_teamspace,
    notion_get_database_entry,
    notion_get_database_schema,
    notion_query_database,
    notion_read_page,
    notion_update_database_schema,
    notion_update_page,
)
from any_tool.providers.notion.types import (
    CreateDatabaseParams,
    CreateDatabaseResult,
    CreateOrUpdateDatabaseEntryParams,
    CreateOrUpdateDatabaseEntryResult,
    CreatePageParams,
    CreatePageResult,
    ExploreTeamspaceParams,
    ExploreTeamspaceResult,
    GetDatabaseEntryParams,
    GetDatabaseEntryResult,
    GetDatabaseSchemaParams,
    GetDatabaseSchemaResult,
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
_TOKEN = "ntn_test_token_abc123"
_BASE_URL = "https://api.notion.com"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# explore_teamspace
# ---------------------------------------------------------------------------


class TestExploreTeamspace:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("search_pages.json"),
            url=f"{_BASE_URL}/v1/search",
            method="POST",
        )
        httpx_mock.add_response(
            json=_load_json("search_databases.json"),
            url=f"{_BASE_URL}/v1/search",
            method="POST",
        )

        result = await notion_explore_teamspace(ExploreTeamspaceParams(), token=_TOKEN)

        assert isinstance(result, ExploreTeamspaceResult)
        assert result.success is True
        assert len(result.pages) == 2
        assert len(result.databases) == 1
        assert result.pages[0].title == "Project Notes"
        assert result.databases[0].title_text == "Tasks"

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("search_pages.json"), method="POST")
        httpx_mock.add_response(json=_load_json("search_databases.json"), method="POST")

        await notion_explore_teamspace(ExploreTeamspaceParams(), token=_TOKEN)

        request = httpx_mock.get_requests()[0]
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"
        assert request.headers["notion-version"] == "2026-03-11"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden", method="POST")

        result = await notion_explore_teamspace(ExploreTeamspaceParams(), token=_TOKEN)

        assert result.success is False
        assert result.error is not None
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_explore_teamspace._tool_definition
        assert defn.name == "notion_explore_teamspace"
        assert defn.provider == "notion"
        assert defn.scopes == ["read_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/post-search"


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


class TestCreatePage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_page.json"),
            url=f"{_BASE_URL}/v1/pages",
            method="POST",
        )

        result = await notion_create_page(
            CreatePageParams(
                parent_page_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                title="Sprint Planning",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreatePageResult)
        assert result.success is True
        assert result.id == "e7f8a9b0-c1d2-3456-efab-cd7890123456"

    async def test_with_content(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_page.json"),
            url=f"{_BASE_URL}/v1/pages",
            method="POST",
        )

        result = await notion_create_page(
            CreatePageParams(
                parent_page_id="parent123",
                title="Test Page",
                content="# Heading\n\nSome paragraph.",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "children" in body
        assert len(body["children"]) == 2

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad request", method="POST")

        result = await notion_create_page(
            CreatePageParams(parent_page_id="bad", title="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error is not None
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_create_page._tool_definition
        assert defn.name == "notion_create_page"
        assert defn.provider == "notion"
        assert defn.scopes == ["insert_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/post-page"


# ---------------------------------------------------------------------------
# update_page
# ---------------------------------------------------------------------------


class TestUpdatePage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("append_blocks.json"),
            url=f"{_BASE_URL}/v1/blocks/page123/children",
            method="PATCH",
        )

        result = await notion_update_page(
            UpdatePageParams(page_id="page123", content="Some new content"),
            token=_TOKEN,
        )

        assert isinstance(result, UpdatePageResult)
        assert result.success is True
        assert result.page_id == "page123"
        assert result.blocks_appended == 1

    async def test_empty_content(self, httpx_mock: HTTPXMock) -> None:
        result = await notion_update_page(
            UpdatePageParams(page_id="page123", content=""),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.blocks_appended == 0

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not found", method="PATCH")

        result = await notion_update_page(
            UpdatePageParams(page_id="missing", content="Hello"),
            token=_TOKEN,
        )

        assert result.success is False
        assert result.error is not None
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_update_page._tool_definition
        assert defn.name == "notion_update_page"
        assert defn.provider == "notion"
        assert defn.scopes == ["update_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/patch-block-children"


# ---------------------------------------------------------------------------
# read_page
# ---------------------------------------------------------------------------


class TestReadPage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        page_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        httpx_mock.add_response(
            json=_load_json("retrieve_page.json"),
            url=f"{_BASE_URL}/v1/pages/{page_id}",
        )
        httpx_mock.add_response(
            json=_load_json("block_children.json"),
            url=f"{_BASE_URL}/v1/blocks/{page_id}/children?page_size=100",
        )

        result = await notion_read_page(ReadPageParams(page_id=page_id), token=_TOKEN)

        assert isinstance(result, ReadPageResult)
        assert result.success is True
        assert result.page is not None
        assert result.page.title == "Project Notes"
        assert len(result.blocks) == 4
        assert result.blocks[0].text_content == "This is the first paragraph of the page."

    async def test_auth_header(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(json=_load_json("retrieve_page.json"))
        httpx_mock.add_response(json=_load_json("block_children.json"))

        await notion_read_page(ReadPageParams(page_id="test123"), token=_TOKEN)

        request = httpx_mock.get_requests()[0]
        assert request.headers["authorization"] == f"Bearer {_TOKEN}"
        assert request.headers["notion-version"] == "2026-03-11"

    async def test_page_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not found")

        result = await notion_read_page(ReadPageParams(page_id="missing"), token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_read_page._tool_definition
        assert defn.name == "notion_read_page"
        assert defn.provider == "notion"
        assert defn.scopes == ["read_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/retrieve-a-page"


# ---------------------------------------------------------------------------
# get_database_schema
# ---------------------------------------------------------------------------


class TestGetDatabaseSchema:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        db_id = "d4e5f6a7-b8c9-0123-defa-b45678901234"
        httpx_mock.add_response(
            json=_load_json("retrieve_database.json"),
            url=f"{_BASE_URL}/v1/databases/{db_id}",
        )

        result = await notion_get_database_schema(
            GetDatabaseSchemaParams(database_id=db_id),
            token=_TOKEN,
        )

        assert isinstance(result, GetDatabaseSchemaResult)
        assert result.success is True
        assert result.database is not None
        assert result.database.title_text == "Tasks"
        assert "Status" in result.database.properties

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not found")

        result = await notion_get_database_schema(
            GetDatabaseSchemaParams(database_id="missing"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_get_database_schema._tool_definition
        assert defn.name == "notion_get_database_schema"
        assert defn.provider == "notion"
        assert defn.scopes == ["read_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/retrieve-database"


# ---------------------------------------------------------------------------
# query_database
# ---------------------------------------------------------------------------


class TestQueryDatabase:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        ds_id = "ds-tasks-001"
        httpx_mock.add_response(
            json=_load_json("query_data_source.json"),
            url=f"{_BASE_URL}/v1/data_sources/{ds_id}/query",
            method="POST",
        )

        result = await notion_query_database(
            QueryDatabaseParams(data_source_id=ds_id),
            token=_TOKEN,
        )

        assert isinstance(result, QueryDatabaseResult)
        assert result.success is True
        assert len(result.results) == 2
        assert result.has_more is True
        assert result.next_cursor == "v1-abc123-cursor"
        assert result.results[0].title == "Implement auth flow"

    async def test_with_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("query_data_source.json"),
            method="POST",
        )

        await notion_query_database(
            QueryDatabaseParams(
                data_source_id="ds-001",
                filter={"property": "Status", "select": {"equals": "Done"}},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "filter" in body
        assert body["filter"]["property"] == "Status"

    async def test_default_sort(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("query_data_source.json"),
            method="POST",
        )

        await notion_query_database(
            QueryDatabaseParams(data_source_id="ds-001"),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["sorts"] == [{"timestamp": "last_edited_time", "direction": "descending"}]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad request", method="POST")

        result = await notion_query_database(
            QueryDatabaseParams(data_source_id="ds-bad"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_query_database._tool_definition
        assert defn.name == "notion_query_database"
        assert defn.provider == "notion"
        assert defn.scopes == ["read_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/query-a-data-source"


# ---------------------------------------------------------------------------
# get_database_entry
# ---------------------------------------------------------------------------


class TestGetDatabaseEntry:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        page_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        httpx_mock.add_response(
            json=_load_json("retrieve_page.json"),
            url=f"{_BASE_URL}/v1/pages/{page_id}",
        )
        httpx_mock.add_response(
            json=_load_json("block_children.json"),
            url=f"{_BASE_URL}/v1/blocks/{page_id}/children?page_size=100",
        )

        result = await notion_get_database_entry(
            GetDatabaseEntryParams(page_id=page_id),
            token=_TOKEN,
        )

        assert isinstance(result, GetDatabaseEntryResult)
        assert result.success is True
        assert result.page is not None
        assert len(result.blocks) == 4

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not found")

        result = await notion_get_database_entry(
            GetDatabaseEntryParams(page_id="missing"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_get_database_entry._tool_definition
        assert defn.name == "notion_get_database_entry"
        assert defn.provider == "notion"
        assert defn.scopes == ["read_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/retrieve-a-page"


# ---------------------------------------------------------------------------
# create_or_update_database_entry
# ---------------------------------------------------------------------------


class TestCreateOrUpdateDatabaseEntry:
    async def test_create_entry(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_page_entry.json"),
            url=f"{_BASE_URL}/v1/pages",
            method="POST",
        )

        result = await notion_create_or_update_database_entry(
            CreateOrUpdateDatabaseEntryParams(
                database_id="d4e5f6a7-b8c9-0123-defa-b45678901234",
                properties={"Name": {"title": [{"text": {"content": "New Task"}}]}},
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateOrUpdateDatabaseEntryResult)
        assert result.success is True
        assert result.id == "b1c2d3e4-f5a6-7890-bcde-f01234567890"

    async def test_update_entry(self, httpx_mock: HTTPXMock) -> None:
        page_id = "f8a9b0c1-d2e3-4567-abcd-ef8901234567"
        httpx_mock.add_response(
            json=_load_json("update_page_entry.json"),
            url=f"{_BASE_URL}/v1/pages/{page_id}",
            method="PATCH",
        )

        result = await notion_create_or_update_database_entry(
            CreateOrUpdateDatabaseEntryParams(
                page_id=page_id,
                properties={"Status": {"select": {"name": "Done"}}},
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert result.id == page_id

    async def test_create_sends_database_parent(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_page_entry.json"),
            method="POST",
        )

        await notion_create_or_update_database_entry(
            CreateOrUpdateDatabaseEntryParams(
                database_id="db123",
                properties={"Name": {"title": [{"text": {"content": "Task"}}]}},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert body["parent"]["database_id"] == "db123"

    async def test_update_sends_patch(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("update_page_entry.json"),
            method="PATCH",
        )

        await notion_create_or_update_database_entry(
            CreateOrUpdateDatabaseEntryParams(
                page_id="page123",
                properties={"Status": {"select": {"name": "Done"}}},
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        assert request.method == "PATCH"
        assert "/pages/page123" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Validation error", method="POST")

        result = await notion_create_or_update_database_entry(
            CreateOrUpdateDatabaseEntryParams(
                database_id="db123",
                properties={},
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_create_or_update_database_entry._tool_definition
        assert defn.name == "notion_create_or_update_database_entry"
        assert defn.provider == "notion"
        assert set(defn.scopes) == {"insert_content", "update_content"}
        assert defn.api_docs_url == "https://developers.notion.com/reference/post-page"


# ---------------------------------------------------------------------------
# create_database
# ---------------------------------------------------------------------------


class TestCreateDatabase:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_database.json"),
            url=f"{_BASE_URL}/v1/databases",
            method="POST",
        )

        result = await notion_create_database(
            CreateDatabaseParams(
                parent_page_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                title="Bug Tracker",
                description="Track and manage bugs.",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateDatabaseResult)
        assert result.success is True
        assert result.id == "c8d9e0f1-a2b3-4567-cdef-a12345678901"
        assert result.title_text == "Bug Tracker"

    async def test_default_properties(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_database.json"),
            method="POST",
        )

        await notion_create_database(
            CreateDatabaseParams(parent_page_id="parent123", title="New DB"),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request is not None
        body = json.loads(request.content)
        assert "Name" in body["properties"]
        assert body["properties"]["Name"] == {"title": {}}

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden", method="POST")

        result = await notion_create_database(
            CreateDatabaseParams(parent_page_id="bad", title="DB"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_create_database._tool_definition
        assert defn.name == "notion_create_database"
        assert defn.provider == "notion"
        assert defn.scopes == ["insert_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/create-a-database"


# ---------------------------------------------------------------------------
# update_database_schema
# ---------------------------------------------------------------------------


class TestUpdateDatabaseSchema:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        db_id = "d4e5f6a7-b8c9-0123-defa-b45678901234"
        httpx_mock.add_response(
            json=_load_json("update_database.json"),
            url=f"{_BASE_URL}/v1/databases/{db_id}",
            method="PATCH",
        )

        result = await notion_update_database_schema(
            UpdateDatabaseSchemaParams(
                database_id=db_id,
                title="Tasks (Updated)",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateDatabaseSchemaResult)
        assert result.success is True
        assert result.title_text == "Tasks (Updated)"

    async def test_no_updates(self, httpx_mock: HTTPXMock) -> None:
        result = await notion_update_database_schema(
            UpdateDatabaseSchemaParams(database_id="db123"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "No updates provided" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not found", method="PATCH")

        result = await notion_update_database_schema(
            UpdateDatabaseSchemaParams(database_id="missing", title="Updated"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = notion_update_database_schema._tool_definition
        assert defn.name == "notion_update_database_schema"
        assert defn.provider == "notion"
        assert defn.scopes == ["update_content"]
        assert defn.api_docs_url == "https://developers.notion.com/reference/update-a-database"


class TestNotionEmbedExternalFile:
    async def test_embed_image_auto(self, httpx_mock) -> None:
        from any_tool.providers.notion.tools import notion_embed_external_file
        from any_tool.providers.notion.types import EmbedExternalFileParams

        httpx_mock.add_response(json={"results": [{"object": "block", "id": "block-001"}]})
        result = await notion_embed_external_file(
            EmbedExternalFileParams(page_id="page-001", url="https://example.com/photo.png"),
            token="test-token",
        )
        assert result.success is True
        assert result.block_type == "image"
        assert result.page_id == "page-001"

    async def test_embed_file_auto(self, httpx_mock) -> None:
        from any_tool.providers.notion.tools import notion_embed_external_file
        from any_tool.providers.notion.types import EmbedExternalFileParams

        httpx_mock.add_response(json={"results": [{"object": "block", "id": "block-001"}]})
        result = await notion_embed_external_file(
            EmbedExternalFileParams(page_id="page-001", url="https://example.com/report.pdf"),
            token="test-token",
        )
        assert result.success is True
        assert result.block_type == "file"

    async def test_embed_explicit_type(self, httpx_mock) -> None:
        from any_tool.providers.notion.tools import notion_embed_external_file
        from any_tool.providers.notion.types import EmbedExternalFileParams

        httpx_mock.add_response(json={"results": [{"object": "block", "id": "block-001"}]})
        result = await notion_embed_external_file(
            EmbedExternalFileParams(page_id="page-001", url="https://example.com/data", file_type="image"),
            token="test-token",
        )
        assert result.block_type == "image"

    async def test_api_error(self, httpx_mock) -> None:
        from any_tool.providers.notion.tools import notion_embed_external_file
        from any_tool.providers.notion.types import EmbedExternalFileParams

        httpx_mock.add_response(status_code=403, text="Forbidden")
        result = await notion_embed_external_file(
            EmbedExternalFileParams(page_id="page-001", url="https://example.com/img.png"),
            token="bad-token",
        )
        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        from any_tool.providers.notion.tools import notion_embed_external_file

        defn = notion_embed_external_file._tool_definition
        assert defn.name == "notion_embed_external_file"
        assert defn.provider == "notion"
        assert defn.service == "notion"
