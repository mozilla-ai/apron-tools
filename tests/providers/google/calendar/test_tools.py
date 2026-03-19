"""Tests for Google Calendar tool functions."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_httpx import HTTPXMock

from any_tool.providers.google.calendar.tools import (
    google_calendar_create_event,
    google_calendar_get_event,
    google_calendar_list_calendars,
    google_calendar_list_events,
    google_calendar_update_event,
)
from any_tool.providers.google.calendar.types import (
    CreateEventParams,
    CreateEventResult,
    EventDateTime,
    GetEventParams,
    GetEventResult,
    ListCalendarsParams,
    ListCalendarsResult,
    ListEventsParams,
    ListEventsResult,
    UpdateEventParams,
    UpdateEventResult,
)

TESTDATA_DIR = Path(__file__).parent / "testdata"
_TOKEN = "test-oauth-token"
_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
_CALENDAR_ID = "cal-001"
_EVENT_ID = "event-001"


def _load_json(filename: str) -> dict | list:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# list_calendars
# ---------------------------------------------------------------------------


class TestListCalendars:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/users/me/calendarList?maxResults=100",
            json=_load_json("list_calendars.json"),
        )

        result = await google_calendar_list_calendars(ListCalendarsParams(), token=_TOKEN)

        assert isinstance(result, ListCalendarsResult)
        assert result.success is True
        assert len(result.calendars) == 2
        assert result.calendars[0].summary == "Work Calendar"
        assert result.calendars[0].primary is True

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_calendar_list_calendars(ListCalendarsParams(), token=_TOKEN)

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_list_calendars._tool_definition
        assert defn.name == "google_calendar_list_calendars"
        assert defn.provider == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


class TestListEvents:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events?maxResults=250",
            json=_load_json("list_events.json"),
        )

        result = await google_calendar_list_events(ListEventsParams(calendar_id=_CALENDAR_ID), token=_TOKEN)

        assert isinstance(result, ListEventsResult)
        assert result.success is True
        assert len(result.events) == 2
        assert result.events[0].summary == "Team Standup"
        assert result.events[1].summary == "Lunch with Client"

    async def test_with_time_filter(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("list_events.json"),
        )

        result = await google_calendar_list_events(
            ListEventsParams(
                calendar_id=_CALENDAR_ID,
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        request = httpx_mock.get_request()
        assert "timeMin" in str(request.url)
        assert "timeMax" in str(request.url)

    async def test_with_query(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("list_events.json"),
        )

        result = await google_calendar_list_events(
            ListEventsParams(calendar_id=_CALENDAR_ID, query="standup"),
            token=_TOKEN,
        )

        assert result.success is True
        request = httpx_mock.get_request()
        assert "q=standup" in str(request.url)

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_calendar_list_events(ListEventsParams(calendar_id="bad-id"), token=_TOKEN)

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_list_events._tool_definition
        assert defn.name == "google_calendar_list_events"
        assert defn.provider == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------


class TestGetEvent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )

        result = await google_calendar_get_event(
            GetEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID),
            token=_TOKEN,
        )

        assert isinstance(result, GetEventResult)
        assert result.success is True
        assert result.event is not None
        assert result.event.id == _EVENT_ID
        assert result.event.summary == "Team Standup"
        assert result.event.location == "Conference Room A"

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_calendar_get_event(
            GetEventParams(calendar_id=_CALENDAR_ID, event_id="bad-id"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_get_event._tool_definition
        assert defn.name == "google_calendar_get_event"
        assert defn.provider == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events",
            json=_load_json("create_event.json"),
        )

        result = await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Project Review",
                description="Quarterly project review",
                location="Conference Room B",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                attendees=["alice@example.com", "bob@example.com"],
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CreateEventResult)
        assert result.success is True
        assert result.event is not None
        assert result.event.id == "event-003"
        assert result.event.summary == "Project Review"

    async def test_sends_correct_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Test Event",
                description="A test",
                location="Room X",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                attendees=["alice@example.com"],
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["summary"] == "Test Event"
        assert body["description"] == "A test"
        assert body["location"] == "Room X"
        assert body["attendees"] == [{"email": "alice@example.com"}]
        assert "dateTime" in body["start"]

    async def test_minimal_event(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Quick Meeting",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "description" not in body
        assert "location" not in body
        assert "attendees" not in body

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=400, text="Bad Request")

        result = await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Bad Event",
                start=EventDateTime(dateTime="invalid"),
                end=EventDateTime(dateTime="invalid"),
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "400" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_create_event._tool_definition
        assert defn.name == "google_calendar_create_event"
        assert defn.provider == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar" in defn.scopes


# ---------------------------------------------------------------------------
# update_event
# ---------------------------------------------------------------------------


class TestUpdateEvent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        # First request: GET to fetch the existing event.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        # Second request: PUT with merged body.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                summary="Team Standup (Updated)",
                location="Conference Room C",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, UpdateEventResult)
        assert result.success is True
        assert result.event is not None
        assert result.event.summary == "Team Standup (Updated)"
        assert result.event.location == "Conference Room C"

    async def test_merges_with_existing(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("update_event.json"),
        )

        await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                summary="New Summary",
            ),
            token=_TOKEN,
        )

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        put_body = json.loads(requests[1].content)
        # The summary should be updated.
        assert put_body["summary"] == "New Summary"
        # The description should be preserved from the original event.
        assert put_body["description"] == "Daily standup meeting"

    async def test_get_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=404, text="Not Found")

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id="bad-id",
                summary="Update",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "404" in result.error

    async def test_put_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            status_code=403,
            text="Forbidden",
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                summary="Update",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_update_event._tool_definition
        assert defn.name == "google_calendar_update_event"
        assert defn.provider == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar" in defn.scopes
