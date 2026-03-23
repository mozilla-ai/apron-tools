"""Integration tests for Slack tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    SLACK_TOKEN=xoxb-... \
    uv run pytest -m integration -k slack -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.slack.tools import slack_explore_workspace, slack_get_file_info
from apron_tools.providers.slack.types import (
    ExploreWorkspaceParams,
    ExploreWorkspaceResult,
    GetFileInfoParams,
    GetFileInfoResult,
)

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
        assert result.workspace_name

    async def test_str_output(self, slack_token: str) -> None:
        result = await slack_explore_workspace(ExploreWorkspaceParams(), token=slack_token)
        text = str(result)
        assert text
        assert "Channels" in text or "Users" in text or result.workspace_name in text


class TestSlackGetFileInfo:
    async def test_invalid_file_returns_error(self, slack_token: str) -> None:
        result = await slack_get_file_info(GetFileInfoParams(file_id="F_NONEXISTENT"), token=slack_token)
        assert isinstance(result, GetFileInfoResult)
        assert result.success is False
