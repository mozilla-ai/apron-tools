"""Tests for Google Calendar provider Pydantic types."""

from __future__ import annotations

import json
from pathlib import Path

from apron_tools.providers.google.calendar.types import (
    CalendarEvent,
    CalendarListEntry,
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


def _load_json(filename: str) -> dict:
    return json.loads((TESTDATA_DIR / filename).read_text())


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class TestListCalendarsParams:
    def test_defaults(self):
        params = ListCalendarsParams()
        assert params.max_results == 100

    def test_custom(self):
        params = ListCalendarsParams(max_results=10)
        assert params.max_results == 10


class TestListEventsParams:
    def test_defaults(self):
        params = ListEventsParams()
        assert params.calendar_id == "primary"
        assert params.max_results == 250
        assert params.time_min is None
        assert params.time_max is None
        assert params.query is None
        assert params.page_token is None

    def test_custom(self):
        params = ListEventsParams(
            calendar_id="cal-001",
            max_results=10,
            time_min="2024-03-01T00:00:00Z",
            time_max="2024-03-31T23:59:59Z",
            query="standup",
        )
        assert params.calendar_id == "cal-001"
        assert params.max_results == 10
        assert params.time_min == "2024-03-01T00:00:00Z"
        assert params.query == "standup"


class TestGetEventParams:
    def test_required(self):
        params = GetEventParams(event_id="event-001")
        assert params.calendar_id == "primary"
        assert params.event_id == "event-001"

    def test_custom_calendar(self):
        params = GetEventParams(calendar_id="cal-001", event_id="event-001")
        assert params.calendar_id == "cal-001"


class TestCreateEventParams:
    def test_required(self):
        params = CreateEventParams(
            summary="Team Meeting",
            start=EventDateTime(dateTime="2024-03-15T09:00:00-04:00"),
            end=EventDateTime(dateTime="2024-03-15T10:00:00-04:00"),
        )
        assert params.calendar_id == "primary"
        assert params.summary == "Team Meeting"
        assert params.description is None
        assert params.location is None
        assert params.attendees is None

    def test_full(self):
        params = CreateEventParams(
            calendar_id="cal-001",
            summary="Team Meeting",
            description="Weekly sync",
            location="Room A",
            start=EventDateTime(dateTime="2024-03-15T09:00:00-04:00"),
            end=EventDateTime(dateTime="2024-03-15T10:00:00-04:00"),
            attendees=["alice@example.com", "bob@example.com"],
        )
        assert params.location == "Room A"
        assert params.attendees == ["alice@example.com", "bob@example.com"]


class TestUpdateEventParams:
    def test_required(self):
        params = UpdateEventParams(event_id="event-001")
        assert params.calendar_id == "primary"
        assert params.event_id == "event-001"
        assert params.summary is None
        assert params.start is None

    def test_partial(self):
        params = UpdateEventParams(
            event_id="event-001",
            summary="Updated Title",
            location="New Room",
        )
        assert params.summary == "Updated Title"
        assert params.location == "New Room"
        assert params.description is None


# ---------------------------------------------------------------------------
# CalendarListEntry
# ---------------------------------------------------------------------------


class TestCalendarListEntry:
    def test_parse_from_api(self):
        data = _load_json("list_calendars.json")
        entry = CalendarListEntry.model_validate(data["items"][0])

        assert entry.id == "cal-001"
        assert entry.summary == "Work Calendar"
        assert entry.description == "Team meetings and deadlines"
        assert entry.time_zone == "America/New_York"
        assert entry.access_role == "owner"
        assert entry.primary is True

    def test_parse_minimal(self):
        data = _load_json("list_calendars.json")
        entry = CalendarListEntry.model_validate(data["items"][1])

        assert entry.id == "cal-002"
        assert entry.summary == "Personal"
        assert entry.description is None
        assert entry.primary is False


# ---------------------------------------------------------------------------
# CalendarEvent
# ---------------------------------------------------------------------------


class TestCalendarEvent:
    def test_parse_full_event(self):
        data = _load_json("get_event.json")
        event = CalendarEvent.model_validate(data)

        assert event.id == "event-001"
        assert event.status == "confirmed"
        assert event.summary == "Team Standup"
        assert event.description == "Daily standup meeting"
        assert event.location == "Conference Room A"
        assert event.creator is not None
        assert event.creator.email == "alice@example.com"
        assert event.start is not None
        assert event.start.date_time == "2024-03-15T09:00:00-04:00"
        assert event.attendees is not None
        assert len(event.attendees) == 2

    def test_parse_allday_event(self):
        data = _load_json("list_events.json")
        event = CalendarEvent.model_validate(data["items"][1])

        assert event.id == "event-002"
        assert event.summary == "Lunch with Client"
        assert event.start is not None
        assert event.start.date == "2024-03-15"
        assert event.start.date_time is None


# ---------------------------------------------------------------------------
# ListCalendarsResult
# ---------------------------------------------------------------------------


class TestListCalendarsResult:
    def test_parse_calendars(self):
        data = _load_json("list_calendars.json")
        calendars = [CalendarListEntry.model_validate(c) for c in data["items"]]
        result = ListCalendarsResult(success=True, calendars=calendars)

        assert result.success is True
        assert len(result.calendars) == 2

    def test_str_output(self):
        data = _load_json("list_calendars.json")
        calendars = [CalendarListEntry.model_validate(c) for c in data["items"]]
        result = ListCalendarsResult(success=True, calendars=calendars)
        text = str(result)

        assert "2 calendar(s)" in text
        assert "Work Calendar" in text
        assert "(primary)" in text
        assert "Personal" in text

    def test_str_on_error(self):
        result = ListCalendarsResult(success=False, error="Forbidden")
        assert str(result) == "Error: Forbidden"

    def test_str_empty(self):
        result = ListCalendarsResult(success=True, calendars=[])
        assert str(result) == "No calendars found."


# ---------------------------------------------------------------------------
# ListEventsResult
# ---------------------------------------------------------------------------


class TestListEventsResult:
    def test_parse_events(self):
        data = _load_json("list_events.json")
        events = [CalendarEvent.model_validate(e) for e in data["items"]]
        result = ListEventsResult(success=True, events=events)

        assert result.success is True
        assert len(result.events) == 2

    def test_str_output(self):
        data = _load_json("list_events.json")
        events = [CalendarEvent.model_validate(e) for e in data["items"]]
        result = ListEventsResult(success=True, events=events)
        text = str(result)

        assert "2 event(s)" in text
        assert "Team Standup" in text
        assert "Lunch with Client" in text

    def test_str_on_error(self):
        result = ListEventsResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"

    def test_str_empty(self):
        result = ListEventsResult(success=True, events=[])
        assert str(result) == "No events found."


# ---------------------------------------------------------------------------
# GetEventResult
# ---------------------------------------------------------------------------


class TestGetEventResult:
    def test_parse_event(self):
        data = _load_json("get_event.json")
        event = CalendarEvent.model_validate(data)
        result = GetEventResult(success=True, event=event)

        assert result.success is True
        assert result.event is not None
        assert result.event.id == "event-001"

    def test_str_output(self):
        data = _load_json("get_event.json")
        event = CalendarEvent.model_validate(data)
        result = GetEventResult(success=True, event=event)
        text = str(result)

        assert "Team Standup" in text
        assert "Conference Room A" in text
        assert "Daily standup meeting" in text
        assert "Attendees: 2" in text

    def test_str_on_error(self):
        result = GetEventResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"

    def test_str_no_event(self):
        result = GetEventResult(success=True, event=None)
        assert str(result) == "No event found."


# ---------------------------------------------------------------------------
# CreateEventResult
# ---------------------------------------------------------------------------


class TestCreateEventResult:
    def test_parse_event(self):
        data = _load_json("create_event.json")
        event = CalendarEvent.model_validate(data)
        result = CreateEventResult(success=True, event=event)

        assert result.success is True
        assert result.event is not None
        assert result.event.id == "event-003"
        assert result.event.summary == "Project Review"

    def test_str_output(self):
        data = _load_json("create_event.json")
        event = CalendarEvent.model_validate(data)
        result = CreateEventResult(success=True, event=event)
        text = str(result)

        assert "Project Review" in text
        assert "created" in text
        assert "event-003" in text

    def test_str_on_error(self):
        result = CreateEventResult(success=False, error="Quota exceeded")
        assert str(result) == "Error: Quota exceeded"

    def test_str_no_event(self):
        result = CreateEventResult(success=True, event=None)
        assert str(result) == "Event created but no details returned."


# ---------------------------------------------------------------------------
# UpdateEventResult
# ---------------------------------------------------------------------------


class TestUpdateEventResult:
    def test_parse_event(self):
        data = _load_json("update_event.json")
        event = CalendarEvent.model_validate(data)
        result = UpdateEventResult(success=True, event=event)

        assert result.success is True
        assert result.event is not None
        assert result.event.id == "event-001"
        assert result.event.summary == "Team Standup (Updated)"

    def test_str_output(self):
        data = _load_json("update_event.json")
        event = CalendarEvent.model_validate(data)
        result = UpdateEventResult(success=True, event=event)
        text = str(result)

        assert "Team Standup (Updated)" in text
        assert "updated" in text
        assert "event-001" in text

    def test_str_on_error(self):
        result = UpdateEventResult(success=False, error="Not Found")
        assert str(result) == "Error: Not Found"

    def test_str_no_event(self):
        result = UpdateEventResult(success=True, event=None)
        assert str(result) == "Event updated but no details returned."
