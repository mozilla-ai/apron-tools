"""Google Calendar tool functions for interacting with the Calendar REST API."""

from __future__ import annotations

import uuid
from urllib.parse import quote

import httpx

from apron_tools.providers.google.calendar.types import (
    CalendarAvailability,
    CalendarEvent,
    CalendarListEntry,
    CheckAvailabilityParams,
    CheckAvailabilityResult,
    CreateEventParams,
    CreateEventResult,
    GetEventParams,
    GetEventResult,
    ListCalendarsParams,
    ListCalendarsResult,
    ListEventsParams,
    ListEventsResult,
    UpdateEventParams,
    UpdateEventResult,
)
from apron_tools.tool import tool

from .scopes import SCOPES

_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3"
_TIMEOUT = 60.0


def _headers(token: str, *, content_type: bool = False) -> dict[str, str]:
    """Build authorization headers for a Google API request."""
    h: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def _build_meet_conference_data() -> dict:
    """Build conferenceData payload that requests a new Google Meet link.

    The Calendar API only accepts conferenceData with an associated
    conferenceSolution. Custom video URLs (Zoom, Teams, etc.) must be
    handled separately rather than via bare entryPoints.
    """
    return {
        "createRequest": {
            "requestId": str(uuid.uuid4()),
            "conferenceSolutionKey": {"type": "hangoutsMeet"},
        }
    }


def _is_valid_video_call_url(url: str | None) -> bool:
    """Return True when *url* is a non-empty http(s) URL.

    Keeps Meet-suppression and description-append in lockstep so an invalid
    URL never disables Meet generation without leaving a usable alternative
    behind.
    """
    return bool(url) and url.startswith(("https://", "http://"))


def _append_video_url_to_description(description: str, video_call_url: str) -> str:
    """Append a custom video call URL to the event description.

    Used for non-Meet URLs (Zoom, Teams, etc.) that cannot be set via
    conferenceData. Skips URLs without an http(s) prefix and avoids
    duplicating the URL if it is already present in the description.
    """
    if not _is_valid_video_call_url(video_call_url):
        return description
    if video_call_url in description:
        return description
    separator = "\n\n" if description else ""
    return f"{description}{separator}Video Call: {video_call_url}"


@tool(
    scopes=SCOPES["google_calendar_list_calendars"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list",
    provider="google",
    service="google_calendar",
)
async def google_calendar_list_calendars(
    params: ListCalendarsParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> ListCalendarsResult:
    """List all calendars accessible by the user."""
    query_params: dict[str, str | int] = {
        "maxResults": params.max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/users/me/calendarList",
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListCalendarsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListCalendarsResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    calendars = [CalendarListEntry.model_validate(c) for c in data.get("items", [])]
    return ListCalendarsResult(success=True, calendars=calendars)


@tool(
    scopes=SCOPES["google_calendar_list_events"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/list",
    provider="google",
    service="google_calendar",
)
async def google_calendar_list_events(
    params: ListEventsParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> ListEventsResult:
    """List events in a calendar."""
    encoded_cal = quote(params.calendar_id, safe="")
    query_params: dict[str, str | int] = {
        "maxResults": params.max_results,
    }
    if params.time_min:
        query_params["timeMin"] = params.time_min
    if params.time_max:
        query_params["timeMax"] = params.time_max
    if params.query:
        query_params["q"] = params.query
    if params.page_token:
        query_params["pageToken"] = params.page_token

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/calendars/{encoded_cal}/events",
                headers=_headers(token),
                params=query_params,
            )
    except httpx.HTTPError as exc:
        return ListEventsResult(success=False, error=str(exc))

    if not resp.is_success:
        return ListEventsResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    data = resp.json()
    events = [CalendarEvent.model_validate(e) for e in data.get("items", [])]
    next_page_token = data.get("nextPageToken")
    return ListEventsResult(success=True, events=events, next_page_token=next_page_token)


@tool(
    scopes=SCOPES["google_calendar_get_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/get",
    provider="google",
    service="google_calendar",
)
async def google_calendar_get_event(
    params: GetEventParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> GetEventResult:
    """Retrieve a single event by ID."""
    encoded_cal = quote(params.calendar_id, safe="")
    encoded_event = quote(params.event_id, safe="")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{base_url}/calendars/{encoded_cal}/events/{encoded_event}",
                headers=_headers(token),
            )
    except httpx.HTTPError as exc:
        return GetEventResult(success=False, error=str(exc))

    if not resp.is_success:
        return GetEventResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    event = CalendarEvent.model_validate(resp.json())
    return GetEventResult(success=True, event=event)


@tool(
    scopes=SCOPES["google_calendar_check_availability"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query",
    provider="google",
    service="google_calendar",
)
async def google_calendar_check_availability(
    params: CheckAvailabilityParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> CheckAvailabilityResult:
    """Query free/busy time blocks for a set of calendars over a time window.

    Results follow the requested attendee order, which the API does not
    guarantee in its response; any calendars the API returns that were not
    requested (e.g. group-expanded members) are appended rather than dropped.
    Per-calendar errors are surfaced on each entry instead of failing the whole
    call, and a malformed response yields ``success=False`` rather than raising.
    """
    body = {
        "timeMin": params.time_min,
        "timeMax": params.time_max,
        "items": [{"id": attendee} for attendee in params.attendees],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/freeBusy",
                headers=_headers(token, content_type=True),
                json=body,
            )
    except httpx.HTTPError as exc:
        return CheckAvailabilityResult(success=False, error=str(exc))

    if not resp.is_success:
        return CheckAvailabilityResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    try:
        data = resp.json()
    except ValueError:
        return CheckAvailabilityResult(
            success=False,
            error="Calendar response was not valid JSON.",
        )

    if not isinstance(data, dict):
        return CheckAvailabilityResult(
            success=False,
            error="Calendar response had an unexpected shape.",
        )

    # The API keys each calendar's free/busy block by its ID. Order the result
    # to follow the requested attendees for predictable output, appending any
    # calendars Google returns that were not requested (e.g. group-expanded
    # members) rather than dropping them. The guard turns a well-formed but
    # wrong-shaped body (non-dict calendars or non-mapping blocks) into a
    # structured failure instead of an uncaught error.
    try:
        raw = data.get("calendars", {})
        requested_ids = list(params.attendees)
        requested_set = set(requested_ids)
        extra_ids = [cal_id for cal_id in raw if cal_id not in requested_set]
        calendars = [
            CalendarAvailability.model_validate({"calendar_id": cal_id, **raw[cal_id]})
            for cal_id in requested_ids + extra_ids
            if cal_id in raw
        ]
    except (ValueError, TypeError):
        return CheckAvailabilityResult(
            success=False,
            error="Calendar response had an unexpected shape.",
        )

    return CheckAvailabilityResult(success=True, calendars=calendars)


@tool(
    scopes=SCOPES["google_calendar_create_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/insert",
    provider="google",
    service="google_calendar",
)
async def google_calendar_create_event(
    params: CreateEventParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> CreateEventResult:
    """Create a new event in a calendar."""
    encoded_cal = quote(params.calendar_id, safe="")

    # A valid custom video_call_url takes precedence over auto-generated Meet
    # links, otherwise a provided URL would be silently dropped. Invalid URLs
    # fall through to the default generate_meet_link behaviour so the event
    # never ends up with neither a Meet link nor a usable custom URL.
    generate_meet_link = params.generate_meet_link
    if _is_valid_video_call_url(params.video_call_url):
        generate_meet_link = False

    body: dict = {
        "summary": params.summary,
        "start": params.start.model_dump(by_alias=True, exclude_none=True),
        "end": params.end.model_dump(by_alias=True, exclude_none=True),
    }
    if params.description is not None:
        body["description"] = params.description
    if params.location is not None:
        body["location"] = params.location
    if params.attendees is not None:
        body["attendees"] = [{"email": email} for email in params.attendees]

    # Custom video URLs go into the description because the Calendar API rejects
    # bare entryPoints without an associated conferenceSolution.
    if params.video_call_url and not generate_meet_link:
        body["description"] = _append_video_url_to_description(body.get("description", "") or "", params.video_call_url)

    # Send email invitations when the event has attendees, so Google notifies them.
    query_params: dict[str, str | int] = {}
    if params.attendees:
        query_params["sendUpdates"] = "all"

    # Request a Google Meet link via createRequest when enabled.
    if generate_meet_link:
        body["conferenceData"] = _build_meet_conference_data()
        query_params["conferenceDataVersion"] = 1

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/calendars/{encoded_cal}/events",
                headers=_headers(token, content_type=True),
                params=query_params,
                json=body,
            )
    except httpx.HTTPError as exc:
        return CreateEventResult(success=False, error=str(exc))

    if not resp.is_success:
        return CreateEventResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    event = CalendarEvent.model_validate(resp.json())
    return CreateEventResult(success=True, event=event)


@tool(
    scopes=SCOPES["google_calendar_update_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/update",
    provider="google",
    service="google_calendar",
)
async def google_calendar_update_event(
    params: UpdateEventParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> UpdateEventResult:
    """Update an existing event in a calendar."""
    encoded_cal = quote(params.calendar_id, safe="")
    encoded_event = quote(params.event_id, safe="")

    # A valid custom video_call_url takes precedence over auto-generated Meet
    # links, otherwise a provided URL would be silently dropped. Invalid URLs
    # fall through to the default generate_meet_link behaviour so the event
    # never ends up with neither a Meet link nor a usable custom URL.
    generate_meet_link = params.generate_meet_link
    if _is_valid_video_call_url(params.video_call_url):
        generate_meet_link = False

    # Fetch the existing event to merge with provided updates.
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            get_resp = await client.get(
                f"{base_url}/calendars/{encoded_cal}/events/{encoded_event}",
                headers=_headers(token),
            )
            if not get_resp.is_success:
                return UpdateEventResult(
                    success=False,
                    error=(f"Calendar API error {get_resp.status_code}: {get_resp.text}"),
                )

            body = get_resp.json()

            # Apply only the fields the caller provided.
            if params.summary is not None:
                body["summary"] = params.summary
            if params.description is not None:
                body["description"] = params.description
            if params.location is not None:
                body["location"] = params.location
            if params.start is not None:
                body["start"] = params.start.model_dump(by_alias=True, exclude_none=True)
            if params.end is not None:
                body["end"] = params.end.model_dump(by_alias=True, exclude_none=True)
            if params.attendees is not None:
                body["attendees"] = [{"email": email} for email in params.attendees]

            # Custom video URLs go into the description because the Calendar API
            # rejects bare entryPoints without an associated conferenceSolution.
            # Coerce None to empty string since the API may return explicit null.
            if params.video_call_url and not generate_meet_link:
                body["description"] = _append_video_url_to_description(
                    body.get("description") or "", params.video_call_url
                )

            # Notify attendees only when the attendee list is explicitly changed,
            # avoiding noisy emails on title- or time-only edits.
            query_params: dict[str, str | int] = {}
            if params.attendees is not None:
                query_params["sendUpdates"] = "all"

            # Request a Google Meet link when enabled.
            if generate_meet_link:
                body["conferenceData"] = _build_meet_conference_data()
                query_params["conferenceDataVersion"] = 1

            resp = await client.put(
                f"{base_url}/calendars/{encoded_cal}/events/{encoded_event}",
                headers=_headers(token, content_type=True),
                params=query_params,
                json=body,
            )
    except httpx.HTTPError as exc:
        return UpdateEventResult(success=False, error=str(exc))

    if not resp.is_success:
        return UpdateEventResult(
            success=False,
            error=f"Calendar API error {resp.status_code}: {resp.text}",
        )

    event = CalendarEvent.model_validate(resp.json())
    return UpdateEventResult(success=True, event=event)
