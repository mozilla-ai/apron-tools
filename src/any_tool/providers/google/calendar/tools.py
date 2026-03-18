"""Google Calendar tool functions for interacting with the Calendar REST API."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from any_tool.providers.google.calendar.types import (
    CalendarEvent,
    CalendarListEntry,
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
from any_tool.tool import tool

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


@tool(
    scopes=SCOPES["list_calendars"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list",
    provider="google_calendar",
)
async def list_calendars(
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
    scopes=SCOPES["list_events"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/list",
    provider="google_calendar",
)
async def list_events(
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
    scopes=SCOPES["get_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/get",
    provider="google_calendar",
)
async def get_event(
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
    scopes=SCOPES["create_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/insert",
    provider="google_calendar",
)
async def create_event(
    params: CreateEventParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> CreateEventResult:
    """Create a new event in a calendar."""
    encoded_cal = quote(params.calendar_id, safe="")

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

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{base_url}/calendars/{encoded_cal}/events",
                headers=_headers(token, content_type=True),
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
    scopes=SCOPES["update_event"],
    api_docs="https://developers.google.com/workspace/calendar/api/v3/reference/events/update",
    provider="google_calendar",
)
async def update_event(
    params: UpdateEventParams,
    *,
    token: str,
    base_url: str = _CALENDAR_BASE_URL,
) -> UpdateEventResult:
    """Update an existing event in a calendar."""
    encoded_cal = quote(params.calendar_id, safe="")
    encoded_event = quote(params.event_id, safe="")

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

            resp = await client.put(
                f"{base_url}/calendars/{encoded_cal}/events/{encoded_event}",
                headers=_headers(token, content_type=True),
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
