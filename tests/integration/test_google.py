"""Integration tests for Google tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    GOOGLE_TOKEN=ya29.... \
    uv run pytest -m integration -k google -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.google.gmail import gmail_list_labels
from apron_tools.providers.google.gmail.types import ListLabelsParams, ListLabelsResult
from apron_tools.providers.google.sheets import google_sheets_list_spreadsheets
from apron_tools.providers.google.sheets.types import ListSpreadsheetsParams, ListSpreadsheetsResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def google_token() -> str:
    """Retrieve Google OAuth token from environment or skip."""
    token = os.environ.get("GOOGLE_TOKEN", "")
    if not token:
        pytest.skip("GOOGLE_TOKEN required")
    return token


class TestGoogleSheetsListSpreadsheets:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(max_results=5), token=google_token)
        assert isinstance(result, ListSpreadsheetsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(max_results=5), token=google_token)
        assert str(result)


class TestGmailListLabels:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await gmail_list_labels(ListLabelsParams(), token=google_token)
        assert isinstance(result, ListLabelsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await gmail_list_labels(ListLabelsParams(), token=google_token)
        assert str(result)
