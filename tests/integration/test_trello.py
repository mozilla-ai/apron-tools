"""Integration tests for Trello tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    TRELLO_API_KEY=xxx \
    TRELLO_TOKEN=xxx \
    uv run pytest -m integration -k trello -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.trello import trello_list_boards
from apron_tools.providers.trello.types import ListBoardsParams, ListBoardsResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def trello_api_key() -> str:
    """Retrieve Trello API key from environment or skip."""
    key = os.environ.get("TRELLO_API_KEY", "")
    if not key:
        pytest.skip("TRELLO_API_KEY required")
    return key


@pytest.fixture()
def trello_token() -> str:
    """Retrieve Trello token from environment or skip."""
    token = os.environ.get("TRELLO_TOKEN", "")
    if not token:
        pytest.skip("TRELLO_TOKEN required")
    return token


class TestTrelloListBoards:
    async def test_returns_valid_result(self, trello_token: str, trello_api_key: str) -> None:
        result = await trello_list_boards(ListBoardsParams(limit=5), token=trello_token, api_key=trello_api_key)
        assert isinstance(result, ListBoardsResult)
        assert result.success is True

    async def test_str_output(self, trello_token: str, trello_api_key: str) -> None:
        result = await trello_list_boards(ListBoardsParams(limit=5), token=trello_token, api_key=trello_api_key)
        assert str(result)
