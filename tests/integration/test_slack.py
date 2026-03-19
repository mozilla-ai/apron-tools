"""Integration tests for Slack tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    SLACK_TOKEN=xoxb-... \
    uv run pytest -m integration -k slack -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.slack import slack_explore_workspace
from apron_tools.providers.slack.types import ExploreWorkspaceParams, ExploreWorkspaceResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def slack_token() -> str:
    """Retrieve Slack token from environment or skip."""
    token = os.environ.get("SLACK_TOKEN", "")
    if not token:
        pytest.skip("SLACK_TOKEN required")
    return token


class TestSlackExploreWorkspace:
    async def test_returns_valid_result(self, slack_token: str) -> None:
        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=slack_token)
        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True

    async def test_str_output(self, slack_token: str) -> None:
        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=slack_token)
        assert str(result)
