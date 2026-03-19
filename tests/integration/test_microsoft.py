"""Integration tests for Microsoft tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    MICROSOFT_TOKEN=... \
    uv run pytest -m integration -k microsoft -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.microsoft.outlook import microsoft_outlook_list_emails
from apron_tools.providers.microsoft.outlook.types import ListEmailsParams, ListEmailsResult
from apron_tools.providers.microsoft.teams import microsoft_teams_explore_workspace
from apron_tools.providers.microsoft.teams.types import ExploreWorkspaceParams, ExploreWorkspaceResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def microsoft_token() -> str:
    """Retrieve Microsoft OAuth token from environment or skip."""
    token = os.environ.get("MICROSOFT_TOKEN", "")
    if not token:
        pytest.skip("MICROSOFT_TOKEN required")
    return token


class TestMicrosoftTeamsExploreWorkspace:
    async def test_returns_valid_result(self, microsoft_token: str) -> None:
        result = await microsoft_teams_explore_workspace(ExploreWorkspaceParams(), token=microsoft_token)
        assert isinstance(result, ExploreWorkspaceResult)
        assert result.success is True

    async def test_str_output(self, microsoft_token: str) -> None:
        result = await microsoft_teams_explore_workspace(ExploreWorkspaceParams(), token=microsoft_token)
        assert str(result)


class TestMicrosoftOutlookListEmails:
    async def test_returns_valid_result(self, microsoft_token: str) -> None:
        result = await microsoft_outlook_list_emails(ListEmailsParams(limit=5), token=microsoft_token)
        assert isinstance(result, ListEmailsResult)
        assert result.success is True

    async def test_str_output(self, microsoft_token: str) -> None:
        result = await microsoft_outlook_list_emails(ListEmailsParams(limit=5), token=microsoft_token)
        assert str(result)
