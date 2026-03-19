"""Tests for Atlassian Confluence provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.atlassian.confluence.types import (
    ChildPageSummary,
    CreatePageParams,
    CreatePageResult,
    ExploreSpacesParams,
    ExploreSpacesResult,
    GetChildPagesParams,
    GetChildPagesResult,
    GetPageContentParams,
    GetPageContentResult,
    PageSummary,
    SearchContentParams,
    SearchContentResult,
    SearchResult,
    SpaceSummary,
    UpdatePageParams,
    UpdatePageResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestExploreSpacesParams:
    def test_defaults(self):
        params = ExploreSpacesParams()
        assert params.max_results == 25

    def test_custom(self):
        params = ExploreSpacesParams(max_results=10)
        assert params.max_results == 10


class TestGetPageContentParams:
    def test_required(self):
        params = GetPageContentParams(page_id="98304")
        assert params.page_id == "98304"


class TestCreatePageParams:
    def test_required(self):
        params = CreatePageParams(space_id="65541", title="My Page")
        assert params.space_id == "65541"
        assert params.title == "My Page"
        assert params.body == ""
        assert params.parent_id is None
        assert params.status == "current"

    def test_custom(self):
        params = CreatePageParams(
            space_id="65541",
            title="My Page",
            body="<p>Hello</p>",
            parent_id="98304",
            status="draft",
        )
        assert params.body == "<p>Hello</p>"
        assert params.parent_id == "98304"
        assert params.status == "draft"


class TestUpdatePageParams:
    def test_required(self):
        params = UpdatePageParams(
            page_id="98304",
            title="Updated Title",
            body="<p>New content</p>",
        )
        assert params.page_id == "98304"
        assert params.title == "Updated Title"
        assert params.body == "<p>New content</p>"
        assert params.status == "current"


class TestSearchContentParams:
    def test_required(self):
        params = SearchContentParams(cql="type=page AND space=ENG")
        assert params.cql == "type=page AND space=ENG"
        assert params.limit == 25

    def test_custom(self):
        params = SearchContentParams(cql="type=page", limit=10)
        assert params.limit == 10


class TestGetChildPagesParams:
    def test_required(self):
        params = GetChildPagesParams(page_id="98304")
        assert params.page_id == "98304"


# ---------------------------------------------------------------------------
# ExploreSpacesResult
# ---------------------------------------------------------------------------


class TestExploreSpacesResult:
    def test_parse_spaces(self):
        data = _load_json("explore_spaces.json")
        spaces = [SpaceSummary.model_validate(s) for s in data["results"]]
        result = ExploreSpacesResult(success=True, spaces=spaces)

        assert result.success is True
        assert len(result.spaces) == 2

    def test_space_fields(self):
        data = _load_json("explore_spaces.json")
        space = SpaceSummary.model_validate(data["results"][0])

        assert space.id == "65541"
        assert space.key == "ENG"
        assert space.name == "Engineering"
        assert space.type == "global"
        assert space.status == "current"
        assert space.homepage_id == "98304"

    def test_str_output(self):
        data = _load_json("explore_spaces.json")
        spaces = [SpaceSummary.model_validate(s) for s in data["results"]]
        result = ExploreSpacesResult(success=True, spaces=spaces)
        text = str(result)

        assert "2 space(s)" in text
        assert "Engineering" in text
        assert "ENG" in text
        assert "Human Resources" in text

    def test_str_on_error(self):
        result = ExploreSpacesResult(success=False, error="Cloud ID not found")
        assert str(result) == "Error: Cloud ID not found"

    def test_str_empty(self):
        result = ExploreSpacesResult(success=True, spaces=[])
        assert str(result) == "No spaces found."


# ---------------------------------------------------------------------------
# GetPageContentResult
# ---------------------------------------------------------------------------


class TestGetPageContentResult:
    def test_parse_page(self):
        data = _load_json("get_page.json")
        page = PageSummary.model_validate(data)
        result = GetPageContentResult(success=True, page=page)

        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98304"

    def test_page_fields(self):
        data = _load_json("get_page.json")
        page = PageSummary.model_validate(data)

        assert page.id == "98304"
        assert page.title == "Engineering Home"
        assert page.space_id == "65541"
        assert page.parent_id is None
        assert page.version.number == 5
        assert page.version.message == "Updated project links"
        assert "<h1>Welcome to Engineering</h1>" in page.body_storage

    def test_str_output(self):
        data = _load_json("get_page.json")
        page = PageSummary.model_validate(data)
        result = GetPageContentResult(success=True, page=page)
        text = str(result)

        assert "Engineering Home" in text
        assert "id=98304" in text
        assert "version=5" in text
        assert "<h1>Welcome to Engineering</h1>" in text

    def test_str_on_error(self):
        result = GetPageContentResult(success=False, error="Page not found")
        assert str(result) == "Error: Page not found"

    def test_str_no_page(self):
        result = GetPageContentResult(success=True, page=None)
        assert str(result) == "No page found."


# ---------------------------------------------------------------------------
# CreatePageResult
# ---------------------------------------------------------------------------


class TestCreatePageResult:
    def test_parse_created_page(self):
        data = _load_json("create_page.json")
        page = PageSummary.model_validate(data)
        result = CreatePageResult(success=True, page=page)

        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98400"
        assert result.page.title == "New Design Doc"

    def test_str_output(self):
        data = _load_json("create_page.json")
        page = PageSummary.model_validate(data)
        result = CreatePageResult(success=True, page=page)
        text = str(result)

        assert "Page created" in text
        assert "New Design Doc" in text
        assert "id=98400" in text

    def test_str_on_error(self):
        result = CreatePageResult(success=False, error="Space not found")
        assert str(result) == "Error: Space not found"

    def test_str_no_page(self):
        result = CreatePageResult(success=True, page=None)
        assert str(result) == "Page created (no details returned)."


# ---------------------------------------------------------------------------
# UpdatePageResult
# ---------------------------------------------------------------------------


class TestUpdatePageResult:
    def test_parse_updated_page(self):
        data = _load_json("update_page.json")
        page = PageSummary.model_validate(data)
        result = UpdatePageResult(success=True, page=page)

        assert result.success is True
        assert result.page is not None
        assert result.page.id == "98304"
        assert result.page.version.number == 6

    def test_str_output(self):
        data = _load_json("update_page.json")
        page = PageSummary.model_validate(data)
        result = UpdatePageResult(success=True, page=page)
        text = str(result)

        assert "Page updated" in text
        assert "Engineering Home (Updated)" in text
        assert "version=6" in text

    def test_str_on_error(self):
        result = UpdatePageResult(success=False, error="Conflict")
        assert str(result) == "Error: Conflict"

    def test_str_no_page(self):
        result = UpdatePageResult(success=True, page=None)
        assert str(result) == "Page updated (no details returned)."


# ---------------------------------------------------------------------------
# SearchContentResult
# ---------------------------------------------------------------------------


class TestSearchContentResult:
    def test_parse_results(self):
        data = _load_json("search_content.json")
        results = [SearchResult.model_validate(r) for r in data["results"]]
        result = SearchContentResult(
            success=True,
            results=results,
            total_size=data["totalSize"],
            cql_query=data["cqlQuery"],
        )

        assert result.success is True
        assert len(result.results) == 3
        assert result.total_size == 3

    def test_search_result_fields(self):
        data = _load_json("search_content.json")
        sr = SearchResult.model_validate(data["results"][0])

        assert sr.content.id == "98304"
        assert sr.content.type == "page"
        assert sr.content.title == "Engineering Home"
        assert sr.content.space.key == "ENG"
        assert sr.title == "Engineering Home"
        assert "engineering team" in sr.excerpt
        assert sr.entity_type == "content"

    def test_str_output(self):
        data = _load_json("search_content.json")
        results = [SearchResult.model_validate(r) for r in data["results"]]
        result = SearchContentResult(
            success=True,
            results=results,
            total_size=3,
            cql_query="type=page AND space=ENG",
        )
        text = str(result)

        assert "3 result(s)" in text
        assert "Engineering Home" in text
        assert "ENG" in text
        assert "engineering team" in text

    def test_str_on_error(self):
        result = SearchContentResult(success=False, error="Invalid CQL")
        assert str(result) == "Error: Invalid CQL"

    def test_str_empty(self):
        result = SearchContentResult(success=True, results=[])
        assert str(result) == "No results found."


# ---------------------------------------------------------------------------
# GetChildPagesResult
# ---------------------------------------------------------------------------


class TestGetChildPagesResult:
    def test_parse_children(self):
        data = _load_json("get_child_pages.json")
        children = [ChildPageSummary.model_validate(c) for c in data["results"]]
        result = GetChildPagesResult(success=True, children=children)

        assert result.success is True
        assert len(result.children) == 3

    def test_child_fields(self):
        data = _load_json("get_child_pages.json")
        child = ChildPageSummary.model_validate(data["results"][0])

        assert child.id == "98310"
        assert child.title == "Architecture Overview"
        assert child.space_id == "65541"
        assert child.child_position == 0

    def test_str_output(self):
        data = _load_json("get_child_pages.json")
        children = [ChildPageSummary.model_validate(c) for c in data["results"]]
        result = GetChildPagesResult(success=True, children=children)
        text = str(result)

        assert "3 child page(s)" in text
        assert "Architecture Overview" in text
        assert "Development Guidelines" in text
        assert "API Reference" in text

    def test_str_on_error(self):
        result = GetChildPagesResult(success=False, error="Page not found")
        assert str(result) == "Error: Page not found"

    def test_str_empty(self):
        result = GetChildPagesResult(success=True, children=[])
        assert str(result) == "No child pages found."
