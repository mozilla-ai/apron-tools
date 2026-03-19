"""Integration tests for GitHub tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    GITHUB_TOKEN=ghp_... \
    uv run pytest -m integration -k github -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.github import github_list_repositories
from apron_tools.providers.github.types import ListRepositoriesParams, ListRepositoriesResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def github_token() -> str:
    """Retrieve GitHub token from environment or skip."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        pytest.skip("GITHUB_TOKEN required")
    return token


class TestGitHubListRepositories:
    async def test_returns_valid_result(self, github_token: str) -> None:
        result = await github_list_repositories(ListRepositoriesParams(limit=5), token=github_token)
        assert isinstance(result, ListRepositoriesResult)
        assert result.success is True

    async def test_str_output(self, github_token: str) -> None:
        result = await github_list_repositories(ListRepositoriesParams(limit=5), token=github_token)
        assert str(result)
