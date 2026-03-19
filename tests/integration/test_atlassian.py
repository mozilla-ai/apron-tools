"""Integration tests for Atlassian tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    ATLASSIAN_TOKEN=... \
    uv run pytest -m integration -k atlassian -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.atlassian.confluence import atlassian_confluence_explore_spaces
from apron_tools.providers.atlassian.confluence.types import ExploreSpacesParams, ExploreSpacesResult
from apron_tools.providers.atlassian.jira import atlassian_jira_explore_projects
from apron_tools.providers.atlassian.jira.types import ExploreProjectsParams, ExploreProjectsResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def atlassian_token() -> str:
    """Retrieve Atlassian OAuth token from environment or skip."""
    token = os.environ.get("ATLASSIAN_TOKEN", "")
    if not token:
        pytest.skip("ATLASSIAN_TOKEN required")
    return token


class TestAtlassianJiraExploreProjects:
    async def test_returns_valid_result(self, atlassian_token: str) -> None:
        result = await atlassian_jira_explore_projects(ExploreProjectsParams(), token=atlassian_token)
        assert isinstance(result, ExploreProjectsResult)
        assert result.success is True

    async def test_str_output(self, atlassian_token: str) -> None:
        result = await atlassian_jira_explore_projects(ExploreProjectsParams(), token=atlassian_token)
        assert str(result)


class TestAtlassianConfluenceExploreSpaces:
    async def test_returns_valid_result(self, atlassian_token: str) -> None:
        result = await atlassian_confluence_explore_spaces(ExploreSpacesParams(), token=atlassian_token)
        assert isinstance(result, ExploreSpacesResult)
        assert result.success is True

    async def test_str_output(self, atlassian_token: str) -> None:
        result = await atlassian_confluence_explore_spaces(ExploreSpacesParams(), token=atlassian_token)
        assert str(result)
