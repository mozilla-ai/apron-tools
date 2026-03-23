"""Integration tests for Linear tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    LINEAR_TOKEN=lin_api_... \
    uv run pytest -m integration -k linear -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.linear.tools import linear_list_issues, linear_list_teams, linear_whoami
from apron_tools.providers.linear.types import (
    ListIssuesParams,
    ListIssuesResult,
    ListTeamsParams,
    ListTeamsResult,
    WhoamiParams,
    WhoamiResult,
)

pytestmark = pytest.mark.integration


@pytest.fixture()
def linear_token() -> str:
    """Retrieve Linear token from environment or skip."""
    token = os.environ.get("LINEAR_TOKEN", "")
    if not token:
        pytest.skip("LINEAR_TOKEN required")
    return token


class TestLinearWhoami:
    async def test_returns_valid_result(self, linear_token: str) -> None:
        result = await linear_whoami(WhoamiParams(), token=linear_token)
        assert isinstance(result, WhoamiResult)
        assert result.success is True

    async def test_str_output(self, linear_token: str) -> None:
        result = await linear_whoami(WhoamiParams(), token=linear_token)
        assert str(result)


class TestLinearListTeams:
    async def test_returns_valid_result(self, linear_token: str) -> None:
        result = await linear_list_teams(ListTeamsParams(), token=linear_token)
        assert isinstance(result, ListTeamsResult)
        assert result.success is True

    async def test_str_output(self, linear_token: str) -> None:
        result = await linear_list_teams(ListTeamsParams(), token=linear_token)
        assert str(result)


class TestLinearListIssues:
    async def test_returns_valid_result(self, linear_token: str) -> None:
        result = await linear_list_issues(ListIssuesParams(limit=5), token=linear_token)
        assert isinstance(result, ListIssuesResult)
        assert result.success is True

    async def test_str_output(self, linear_token: str) -> None:
        result = await linear_list_issues(ListIssuesParams(limit=5), token=linear_token)
        assert str(result)
