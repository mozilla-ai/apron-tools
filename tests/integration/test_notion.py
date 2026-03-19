"""Integration tests for Notion tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    NOTION_TOKEN=ntn_... \
    uv run pytest -m integration -k notion -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.notion import notion_explore_teamspace
from apron_tools.providers.notion.types import ExploreTeamspaceParams, ExploreTeamspaceResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def notion_token() -> str:
    """Retrieve Notion token from environment or skip."""
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        pytest.skip("NOTION_TOKEN required")
    return token


class TestNotionExploreTeamspace:
    async def test_returns_valid_result(self, notion_token: str) -> None:
        result = await notion_explore_teamspace(ExploreTeamspaceParams(), token=notion_token)
        assert isinstance(result, ExploreTeamspaceResult)
        assert result.success is True

    async def test_str_output(self, notion_token: str) -> None:
        result = await notion_explore_teamspace(ExploreTeamspaceParams(), token=notion_token)
        assert str(result)
