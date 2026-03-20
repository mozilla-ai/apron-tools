"""Integration tests for Google tools against real endpoints.

Skipped by default. To run::

    APRON_TOOLS_INTEGRATION_TESTS=1 \
    GOOGLE_TOKEN=ya29.... \
    uv run pytest -m integration -k google -v
"""

from __future__ import annotations

import os

import pytest

from apron_tools.providers.google.calendar import google_calendar_list_calendars
from apron_tools.providers.google.calendar.types import ListCalendarsParams, ListCalendarsResult
from apron_tools.providers.google.docs import google_docs_list_documents
from apron_tools.providers.google.docs.types import ListDocumentsParams, ListDocumentsResult
from apron_tools.providers.google.drive import google_drive_list_files
from apron_tools.providers.google.drive.types import ListFilesParams, ListFilesResult
from apron_tools.providers.google.gmail import gmail_list_labels
from apron_tools.providers.google.gmail.types import ListLabelsParams, ListLabelsResult
from apron_tools.providers.google.sheets import google_sheets_list_spreadsheets
from apron_tools.providers.google.sheets.types import ListSpreadsheetsParams, ListSpreadsheetsResult
from apron_tools.providers.google.slides import google_slides_list_presentations
from apron_tools.providers.google.slides.types import ListPresentationsParams, ListPresentationsResult

pytestmark = pytest.mark.integration


@pytest.fixture()
def google_token() -> str:
    """Retrieve Google OAuth token from environment or skip."""
    token = os.environ.get("GOOGLE_TOKEN", "")
    if not token:
        pytest.skip("GOOGLE_TOKEN required")
    return token


class TestGoogleCalendarListCalendars:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_calendar_list_calendars(ListCalendarsParams(), token=google_token)
        assert isinstance(result, ListCalendarsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_calendar_list_calendars(ListCalendarsParams(), token=google_token)
        assert str(result)


class TestGoogleDocsListDocuments:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_docs_list_documents(ListDocumentsParams(max_results=5), token=google_token)
        assert isinstance(result, ListDocumentsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_docs_list_documents(ListDocumentsParams(max_results=5), token=google_token)
        assert str(result)


class TestGoogleDriveListFiles:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_drive_list_files(ListFilesParams(max_results=5), token=google_token)
        assert isinstance(result, ListFilesResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_drive_list_files(ListFilesParams(max_results=5), token=google_token)
        assert str(result)


class TestGmailListLabels:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await gmail_list_labels(ListLabelsParams(), token=google_token)
        assert isinstance(result, ListLabelsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await gmail_list_labels(ListLabelsParams(), token=google_token)
        assert str(result)


class TestGoogleSheetsListSpreadsheets:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(max_results=5), token=google_token)
        assert isinstance(result, ListSpreadsheetsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_sheets_list_spreadsheets(ListSpreadsheetsParams(max_results=5), token=google_token)
        assert str(result)


class TestGoogleSlidesListPresentations:
    async def test_returns_valid_result(self, google_token: str) -> None:
        result = await google_slides_list_presentations(ListPresentationsParams(max_results=5), token=google_token)
        assert isinstance(result, ListPresentationsResult)
        assert result.success is True

    async def test_str_output(self, google_token: str) -> None:
        result = await google_slides_list_presentations(ListPresentationsParams(max_results=5), token=google_token)
        assert str(result)
