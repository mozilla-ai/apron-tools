"""OAuth scope definitions for Google Calendar tools."""

from __future__ import annotations

from apron_tools.types import CapabilityGroup, Scope


class GoogleCalendarScope(Scope):
    """OAuth scopes for Google Calendar API access."""

    CALENDAR_READONLY = (
        "https://www.googleapis.com/auth/calendar.readonly",
        "View Calendar",
        "View your Google Calendar events and schedules",
        "read",
        False,
    )
    CALENDAR = (
        "https://www.googleapis.com/auth/calendar",
        "Full Calendar Access",
        "View, edit, share, and delete all calendars and events",
        "write",
        False,
    )


SCOPES: dict[str, list[GoogleCalendarScope]] = {
    "google_calendar_list_calendars": [GoogleCalendarScope.CALENDAR_READONLY],
    "google_calendar_list_events": [GoogleCalendarScope.CALENDAR_READONLY],
    "google_calendar_get_event": [GoogleCalendarScope.CALENDAR_READONLY],
    "google_calendar_create_event": [GoogleCalendarScope.CALENDAR],
    "google_calendar_update_event": [GoogleCalendarScope.CALENDAR],
}

CAPABILITY_GROUP = CapabilityGroup(
    provider="google_calendar",
    display_name="Google Calendar",
    scopes=sorted({s for scopes in SCOPES.values() for s in scopes}),
)
