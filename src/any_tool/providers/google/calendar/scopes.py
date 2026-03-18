"""OAuth scope definitions for Google Calendar tools."""

from __future__ import annotations

from enum import StrEnum

from any_tool.types import CapabilityGroup


class GoogleCalendarScope(StrEnum):
    """OAuth scopes for Google Calendar API access."""

    CALENDAR_READONLY = "https://www.googleapis.com/auth/calendar.readonly"
    CALENDAR = "https://www.googleapis.com/auth/calendar"


SCOPES: dict[str, list[GoogleCalendarScope]] = {
    "list_calendars": [GoogleCalendarScope.CALENDAR_READONLY],
    "list_events": [GoogleCalendarScope.CALENDAR_READONLY],
    "get_event": [GoogleCalendarScope.CALENDAR_READONLY],
    "create_event": [GoogleCalendarScope.CALENDAR],
    "update_event": [GoogleCalendarScope.CALENDAR],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_calendar",
    display_name="Google Calendar",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
