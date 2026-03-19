"""Google Calendar provider.

API docs:
  - Calendar: https://developers.google.com/workspace/calendar/api/v3/reference
"""

from .tools import (
    google_calendar_create_event,
    google_calendar_get_event,
    google_calendar_list_calendars,
    google_calendar_list_events,
    google_calendar_update_event,
)

__all__ = [
    "google_calendar_create_event",
    "google_calendar_get_event",
    "google_calendar_list_calendars",
    "google_calendar_list_events",
    "google_calendar_update_event",
]
