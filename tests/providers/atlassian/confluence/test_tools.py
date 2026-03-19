"""Tests for Atlassian Confluence tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.atlassian.confluence.tools import (
    atlassian_confluence_create_page,
    atlassian_confluence_explore_spaces,
    atlassian_confluence_get_child_pages,
    atlassian_confluence_get_page_content,
    atlassian_confluence_search_content,
    atlassian_confluence_update_page,
)
from any_tool.providers.atlassian.confluence.types import (
    CreatePageParams,
    CreatePageResult,
    ExploreSpacesParams,
    ExploreSpacesResult,
    GetChildPagesParams,
    GetChildPagesResult,
    GetPageContentParams,
    GetPageContentResult,
    SearchContentParams,
    SearchContentResult,
    UpdatePageParams,
    UpdatePageResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test_oauth_token_abc123"
_BASE = "https://api.atlassian.com"
_CLOUD_ID = "1324a887-45db-1bf4-1e99-ef0ff456d421"
_V2_PREFIX = f"{_BASE}/ex/confluence/{_CLOUD_ID}/wiki/api/v2"
_V1_PREFIX = f"{_BASE}/ex/confluence/{_CLOUD_ID}/wiki/rest/api"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


def _mock_cloud_id(httpx_mock: HTTPXMock) -> None:
    """Register the accessible-resources response that resolves the cloud ID."""
    httpx_mock.add_response(
        url=f"{_BASE}/oauth/token/accessible-resources",
        json=_load_json("accessible_resources.json"),
    )


# ---------------------------------------------------------------------------
# explore_spaces
# ---------------------------------------------------------------------------


class TestExploreSpaces:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/spaces?limit=25",
            json=_load_json("explore_spaces.json"),
        )

        result = await atlassian_confluence_explore_spaces(ExploreSpacesParams(), token=_TOKEN)

        assert isinstance(result, ExploreSpacesResult)
        assert result.success is True
        assert len(result.spaces) == 2
        assert result.spaces[0].key == "ENG"
        assert result.spaces[0].name == "Engineering"

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            json=[],
        )

        result = await atlassian_confluence_explore_spaces(ExploreSpacesParams(), token=_TOKEN)

        assert result.success is False
        assert "cloud ID" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await atlassian_confluence_explore_spaces(ExploreSpacesParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_explore_spaces._tool_definition
        assert defn.name == "atlassian_confluence_explore_spaces"
        assert defn.provider == "atlassian_confluence"
        assert "read:confluence-content.all" in defn.scopes


# ---------------------------------------------------------------------------
# get_page_content
# ---------------------------------------------------------------------------


class TestGetPageContent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304?body-format=storage",
            json=_load_json("get_page.json"),
        )

        result = await atlassian_confluence_get_page_content(
            GetPageContentParams(page_id="98304"),
            token=_TOKEN,
        )

        assert isinstance(result, GetPageContentResult)
        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98304"
        assert result.page.title == "Engineering Home"
        assert "<h1>Welcome to Engineering</h1>" in result.page.body_storage

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            status_code=401,
            text="Unauthorized",
        )

        result = await atlassian_confluence_get_page_content(
            GetPageContentParams(page_id="98304"),
            token=_TOKEN,
        )

        assert result.success is False

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await atlassian_confluence_get_page_content(
            GetPageContentParams(page_id="99999"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_get_page_content._tool_definition
        assert defn.name == "atlassian_confluence_get_page_content"
        assert defn.provider == "atlassian_confluence"
        assert "read:confluence-content.all" in defn.scopes


# ---------------------------------------------------------------------------
# create_page
# ---------------------------------------------------------------------------


class TestCreatePage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages",
            json=_load_json("create_page.json"),
            status_code=200,
        )

        result = await atlassian_confluence_create_page(
            CreatePageParams(
                space_id="65541",
                title="New Design Doc",
                body="<p>Initial design document content.</p>",
                parent_id="98304",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreatePageResult)
        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98400"
        assert result.page.title == "New Design Doc"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            status_code=400,
            text='{"message":"Space not found"}',
        )

        result = await atlassian_confluence_create_page(
            CreatePageParams(space_id="99999", title="Test"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_create_page._tool_definition
        assert defn.name == "atlassian_confluence_create_page"
        assert defn.provider == "atlassian_confluence"
        assert "write:confluence-content" in defn.scopes


# ---------------------------------------------------------------------------
# update_page
# ---------------------------------------------------------------------------


class TestUpdatePage:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        # GET to fetch current version.
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304",
            json=_load_json("get_page.json"),
            method="GET",
        )
        # PUT to update.
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304",
            json=_load_json("update_page.json"),
            method="PUT",
        )

        result = await atlassian_confluence_update_page(
            UpdatePageParams(
                page_id="98304",
                title="Engineering Home (Updated)",
                body="<h1>Welcome to Engineering</h1><p>Updated content here.</p>",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdatePageResult)
        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98304"
        assert result.page.version.number == 6

    async def test_get_fails(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304",
            status_code=404,
            text="Not Found",
        )

        result = await atlassian_confluence_update_page(
            UpdatePageParams(
                page_id="98304",
                title="Updated",
                body="<p>Content</p>",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_put_fails(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        # GET succeeds.
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304",
            json=_load_json("get_page.json"),
            method="GET",
        )
        # PUT fails.
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304",
            status_code=409,
            text="Version conflict",
            method="PUT",
        )

        result = await atlassian_confluence_update_page(
            UpdatePageParams(
                page_id="98304",
                title="Updated",
                body="<p>Content</p>",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "409" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_update_page._tool_definition
        assert defn.name == "atlassian_confluence_update_page"
        assert defn.provider == "atlassian_confluence"
        assert "read:confluence-content.all" in defn.scopes
        assert "write:confluence-content" in defn.scopes


# ---------------------------------------------------------------------------
# search_content
# ---------------------------------------------------------------------------


class TestSearchContent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V1_PREFIX}/search?cql=type%3Dpage+AND+space%3DENG&limit=25",
            json=_load_json("search_content.json"),
        )

        result = await atlassian_confluence_search_content(
            SearchContentParams(cql="type=page AND space=ENG"),
            token=_TOKEN,
        )

        assert isinstance(result, SearchContentResult)
        assert result.success is True
        assert len(result.results) == 3
        assert result.total_size == 3
        assert result.results[0].content.id == "98304"

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            json=[],
        )

        result = await atlassian_confluence_search_content(
            SearchContentParams(cql="type=page"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "cloud ID" in result.error

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=400, text="Invalid CQL query")

        result = await atlassian_confluence_search_content(
            SearchContentParams(cql="INVALID"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_search_content._tool_definition
        assert defn.name == "atlassian_confluence_search_content"
        assert defn.provider == "atlassian_confluence"
        assert "search:confluence" in defn.scopes


# ---------------------------------------------------------------------------
# get_child_pages
# ---------------------------------------------------------------------------


class TestGetChildPages:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(
            url=f"{_V2_PREFIX}/pages/98304/direct-children",
            json=_load_json("get_child_pages.json"),
        )

        result = await atlassian_confluence_get_child_pages(
            GetChildPagesParams(page_id="98304"),
            token=_TOKEN,
        )

        assert isinstance(result, GetChildPagesResult)
        assert result.success is True
        assert len(result.children) == 3
        assert result.children[0].title == "Architecture Overview"
        assert result.children[1].title == "Development Guidelines"

    async def test_cloud_id_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_BASE}/oauth/token/accessible-resources",
            status_code=401,
            text="Unauthorized",
        )

        result = await atlassian_confluence_get_child_pages(
            GetChildPagesParams(page_id="98304"),
            token=_TOKEN,
        )

        assert result.success is False

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        _mock_cloud_id(httpx_mock)
        httpx_mock.add_response(status_code=404, text="Page not found")

        result = await atlassian_confluence_get_child_pages(
            GetChildPagesParams(page_id="99999"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = atlassian_confluence_get_child_pages._tool_definition
        assert defn.name == "atlassian_confluence_get_child_pages"
        assert defn.provider == "atlassian_confluence"
        assert "read:confluence-content.all" in defn.scopes
