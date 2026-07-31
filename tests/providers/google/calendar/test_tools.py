"""Tests for Google Calendar tool functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from apron_tools.providers.google.calendar.tools import (
    google_calendar_check_availability,
    google_calendar_create_event,
    google_calendar_get_event,
    google_calendar_list_calendars,
    google_calendar_list_events,
    google_calendar_update_event,
)
from apron_tools.providers.google.calendar.types import (
    CheckAvailabilityParams,
    CheckAvailabilityResult,
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

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # A 2xx body that is not JSON (e.g. a proxy/CDN interstitial) must yield
        # a structured failure rather than an uncaught decode error.
        httpx_mock.add_response(status_code=200, text="<html>not json</html>")

        result = await google_calendar_list_calendars(ListCalendarsParams(), token=_TOKEN)

        assert result.success is False
        assert "JSON" in result.error

    @pytest.mark.parametrize(
        "body",
        [
            [],
            {"items": None},
            {"items": "not-a-list"},
            {"items": [123]},
        ],
    )
    async def test_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock, body: object) -> None:
        # A 2xx body that is valid JSON but not the expected object shape must
        # yield a structured failure, not an uncaught AttributeError/TypeError.
        httpx_mock.add_response(status_code=200, json=body)

        result = await google_calendar_list_calendars(ListCalendarsParams(), token=_TOKEN)

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_list_calendars._tool_definition
        assert defn.name == "google_calendar_list_calendars"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
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

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # A 2xx body that is not JSON must yield a structured failure rather than
        # an uncaught decode error.
        httpx_mock.add_response(status_code=200, text="<html>not json</html>")

        result = await google_calendar_list_events(ListEventsParams(calendar_id=_CALENDAR_ID), token=_TOKEN)

        assert result.success is False
        assert "JSON" in result.error

    @pytest.mark.parametrize(
        "body",
        [
            [],
            {"items": None},
            {"items": "not-a-list"},
            {"items": [123]},
        ],
    )
    async def test_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock, body: object) -> None:
        # A 2xx body that is valid JSON but not the expected object shape must
        # yield a structured failure, not an uncaught AttributeError/TypeError.
        httpx_mock.add_response(status_code=200, json=body)

        result = await google_calendar_list_events(ListEventsParams(calendar_id=_CALENDAR_ID), token=_TOKEN)

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_list_events._tool_definition
        assert defn.name == "google_calendar_list_events"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
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

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # A 2xx body that is not JSON must yield a structured failure rather than
        # an uncaught decode error.
        httpx_mock.add_response(status_code=200, text="<html>not json</html>")

        result = await google_calendar_get_event(
            GetEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID),
            token=_TOKEN,
        )

        assert result.success is False
        assert "JSON" in result.error

    @pytest.mark.parametrize("body", [[], "not-an-object", 123])
    async def test_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock, body: object) -> None:
        # A 2xx body that is valid JSON but not an event object must yield a
        # structured failure, not an uncaught ValidationError.
        httpx_mock.add_response(status_code=200, json=body)

        result = await google_calendar_get_event(
            GetEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID),
            token=_TOKEN,
        )

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_get_event._tool_definition
        assert defn.name == "google_calendar_get_event"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# check_availability
# ---------------------------------------------------------------------------


class TestCheckAvailability:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json=_load_json("check_availability.json"),
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com", "bob@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert isinstance(result, CheckAvailabilityResult)
        assert result.success is True
        assert len(result.calendars) == 2

        alice = result.calendars[0]
        assert alice.calendar_id == "alice@example.com"
        assert len(alice.busy) == 1
        assert alice.busy[0].start == "2024-03-15T09:00:00Z"
        assert alice.busy[0].end == "2024-03-15T10:00:00Z"
        assert alice.errors == []

        bob = result.calendars[1]
        assert bob.calendar_id == "bob@example.com"
        assert bob.busy == []

    async def test_no_overlapping_events_returns_empty_busy(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json=_load_json("check_availability_all_free.json"),
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com", "bob@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert all(cal.busy == [] for cal in result.calendars)

    async def test_per_calendar_error_surfaced_without_failing(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json=_load_json("check_availability_error.json"),
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com", "hidden@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        # A calendar the token can't read surfaces as a per-calendar error,
        # while the overall call and the readable calendar still succeed.
        assert result.success is True
        by_id = {cal.calendar_id: cal for cal in result.calendars}
        assert len(by_id["alice@example.com"].busy) == 1
        hidden = by_id["hidden@example.com"]
        assert hidden.busy == []
        assert len(hidden.errors) == 1
        assert hidden.errors[0].reason == "notFound"

    async def test_sends_correct_body(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json=_load_json("check_availability.json"),
        )

        await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com", "bob@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body["timeMin"] == "2024-03-15T00:00:00Z"
        assert body["timeMax"] == "2024-03-16T00:00:00Z"
        assert body["items"] == [
            {"id": "alice@example.com"},
            {"id": "bob@example.com"},
        ]

    async def test_api_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(status_code=403, text="Forbidden")

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "403" in result.error

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # A 2xx body that is not JSON (e.g. a proxy/CDN interstitial) must yield
        # a structured failure rather than an uncaught decode error.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            status_code=200,
            text="<html>not json</html>",
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "JSON" in result.error

    async def test_orders_by_requested_attendees(self, httpx_mock: HTTPXMock) -> None:
        # Google may key the calendars map in any order; the result must follow
        # the requested attendee order, which the API does not guarantee.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json={
                "calendars": {
                    "bob@example.com": {"busy": []},
                    "alice@example.com": {"busy": [{"start": "2024-03-15T09:00:00Z", "end": "2024-03-15T10:00:00Z"}]},
                }
            },
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com", "bob@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert [c.calendar_id for c in result.calendars] == ["alice@example.com", "bob@example.com"]

    async def test_includes_unrequested_calendars_after_requested(self, httpx_mock: HTTPXMock) -> None:
        # Calendars Google returns that were not requested (e.g. group-expanded
        # members) are appended rather than dropped.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/freeBusy",
            json={
                "calendars": {
                    "team@example.com": {"busy": []},
                    "alice@example.com": {"busy": []},
                }
            },
        )

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        assert [c.calendar_id for c in result.calendars] == ["alice@example.com", "team@example.com"]

    @pytest.mark.parametrize(
        "body",
        [
            [],
            {"calendars": None},
            {"calendars": ["alice@example.com"]},
            {"calendars": {"alice@example.com": "busy"}},
            {"calendars": {"alice@example.com": {"busy": "not-a-list"}}},
        ],
    )
    async def test_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock, body: object) -> None:
        # A 2xx body that is valid JSON but not the expected object shape must
        # yield a structured failure, not an uncaught AttributeError/TypeError.
        httpx_mock.add_response(url=f"{_CALENDAR_BASE}/freeBusy", status_code=200, json=body)

        result = await google_calendar_check_availability(
            CheckAvailabilityParams(
                attendees=["alice@example.com"],
                time_min="2024-03-15T00:00:00Z",
                time_max="2024-03-16T00:00:00Z",
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_check_availability._tool_definition
        assert defn.name == "google_calendar_check_availability"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar.readonly" in defn.scopes


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    async def test_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events?sendUpdates=all&conferenceDataVersion=1",
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

    async def test_with_attendees_sends_invites(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Team Sync",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                attendees=["alice@example.com"],
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert "sendUpdates=all" in str(request.url)

    async def test_without_attendees_omits_send_updates(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Solo Focus",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        assert "sendUpdates" not in str(request.url)

    async def test_default_generates_meet_link(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Auto Meet",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["conferenceData"]["createRequest"]["conferenceSolutionKey"] == {"type": "hangoutsMeet"}
        assert "requestId" in body["conferenceData"]["createRequest"]
        assert "conferenceDataVersion=1" in str(request.url)

    async def test_opt_out_of_meet_link(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="No Meet",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                generate_meet_link=False,
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "conferenceData" not in body
        assert "conferenceDataVersion" not in str(request.url)

    async def test_video_call_url_appended_to_description(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Zoom Meeting",
                description="Quarterly review",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                video_call_url="https://zoom.us/j/12345",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "Quarterly review" in body["description"]
        assert "https://zoom.us/j/12345" in body["description"]

    async def test_video_call_url_takes_precedence_over_meet(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Zoom Meeting",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                video_call_url="https://zoom.us/j/12345",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert "conferenceData" not in body
        assert "conferenceDataVersion" not in str(request.url)
        assert "https://zoom.us/j/12345" in body["description"]

    async def test_video_call_url_without_existing_description(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Teams Meeting",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                video_call_url="https://teams.microsoft.com/l/meetup-join/abc",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["description"] == "Video Call: https://teams.microsoft.com/l/meetup-join/abc"

    async def test_invalid_video_call_url_not_appended(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Bad URL",
                description="Existing notes",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                video_call_url="not-a-real-url",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["description"] == "Existing notes"
        # Invalid URL must not disable Meet generation — otherwise the event
        # ends up with neither a Meet link nor a usable custom URL.
        assert "conferenceData" in body
        assert request.url.params.get("conferenceDataVersion") == "1"

    async def test_video_call_url_not_duplicated_in_description(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            json=_load_json("create_event.json"),
        )

        await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Zoom Meeting",
                description="Join here: https://zoom.us/j/12345",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
                video_call_url="https://zoom.us/j/12345",
            ),
            token=_TOKEN,
        )

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["description"].count("https://zoom.us/j/12345") == 1

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

    async def test_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # A 2xx body that is not JSON must yield a structured failure rather than
        # an uncaught decode error.
        httpx_mock.add_response(status_code=200, text="<html>not json</html>")

        result = await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Event",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "JSON" in result.error

    @pytest.mark.parametrize("body", [[], "not-an-object", 123])
    async def test_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock, body: object) -> None:
        # A 2xx body that is valid JSON but not an event object must yield a
        # structured failure, not an uncaught ValidationError.
        httpx_mock.add_response(status_code=200, json=body)

        result = await google_calendar_create_event(
            CreateEventParams(
                calendar_id=_CALENDAR_ID,
                summary="Event",
                start=EventDateTime(dateTime="2024-03-20T14:00:00-04:00"),
                end=EventDateTime(dateTime="2024-03-20T15:00:00-04:00"),
            ),
            token=_TOKEN,
        )

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_create_event._tool_definition
        assert defn.name == "google_calendar_create_event"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
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

    async def test_with_attendees_sends_invites(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}?sendUpdates=all",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                attendees=["bob@example.com"],
            ),
            token=_TOKEN,
        )

        assert result.success is True
        put_request = httpx_mock.get_requests()[1]
        assert "sendUpdates=all" in str(put_request.url)

    async def test_without_attendees_omits_send_updates(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                summary="Only title change",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        put_request = httpx_mock.get_requests()[1]
        assert "sendUpdates" not in str(put_request.url)

    async def test_generate_meet_link_adds_conference_data(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}?conferenceDataVersion=1",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                generate_meet_link=True,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        put_request = httpx_mock.get_requests()[1]
        put_body = json.loads(put_request.content)
        assert put_body["conferenceData"]["createRequest"]["conferenceSolutionKey"] == {"type": "hangoutsMeet"}

    async def test_video_call_url_appended_to_existing_description(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                video_call_url="https://zoom.us/j/99999",
            ),
            token=_TOKEN,
        )

        assert result.success is True
        put_request = httpx_mock.get_requests()[1]
        put_body = json.loads(put_request.content)
        # The existing description from get_event.json is "Daily standup meeting".
        assert "Daily standup meeting" in put_body["description"]
        assert "https://zoom.us/j/99999" in put_body["description"]
        assert "conferenceData" not in put_body or "createRequest" not in put_body.get("conferenceData", {})

    async def test_video_call_url_on_update_suppresses_meet(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("update_event.json"),
        )

        result = await google_calendar_update_event(
            UpdateEventParams(
                calendar_id=_CALENDAR_ID,
                event_id=_EVENT_ID,
                video_call_url="https://zoom.us/j/11111",
                generate_meet_link=True,
            ),
            token=_TOKEN,
        )

        assert result.success is True
        put_request = httpx_mock.get_requests()[1]
        put_body = json.loads(put_request.content)
        assert "conferenceDataVersion" not in str(put_request.url)
        # Custom video URL is appended to description; meet link is suppressed.
        assert "https://zoom.us/j/11111" in put_body["description"]

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

    async def test_get_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # The GET fetch returning a non-JSON 2xx body must yield a structured
        # failure rather than an uncaught decode error.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            status_code=200,
            text="<html>not json</html>",
        )

        result = await google_calendar_update_event(
            UpdateEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID, summary="Update"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "JSON" in result.error

    async def test_get_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock) -> None:
        # The GET fetch returning valid JSON that is not an event object must
        # yield a structured failure, not an uncaught TypeError when merging.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            status_code=200,
            json=[],
        )

        result = await google_calendar_update_event(
            UpdateEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID, summary="Update"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "shape" in result.error

    async def test_put_non_json_response(self, httpx_mock: HTTPXMock) -> None:
        # The PUT response being a non-JSON 2xx body must yield a structured
        # failure rather than an uncaught decode error.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            status_code=200,
            text="<html>not json</html>",
        )

        result = await google_calendar_update_event(
            UpdateEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID, summary="Update"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "JSON" in result.error

    async def test_put_unexpected_shape_returns_failure(self, httpx_mock: HTTPXMock) -> None:
        # The PUT response being valid JSON that is not an event object must
        # yield a structured failure, not an uncaught ValidationError.
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            json=_load_json("get_event.json"),
        )
        httpx_mock.add_response(
            url=f"{_CALENDAR_BASE}/calendars/{_CALENDAR_ID}/events/{_EVENT_ID}",
            status_code=200,
            json=[],
        )

        result = await google_calendar_update_event(
            UpdateEventParams(calendar_id=_CALENDAR_ID, event_id=_EVENT_ID, summary="Update"),
            token=_TOKEN,
        )

        assert result.success is False
        assert "shape" in result.error

    async def test_has_tool_definition(self) -> None:
        defn = google_calendar_update_event._tool_definition
        assert defn.name == "google_calendar_update_event"
        assert defn.provider == "google"
        assert defn.service == "google_calendar"
        assert "https://www.googleapis.com/auth/calendar" in defn.scopes
