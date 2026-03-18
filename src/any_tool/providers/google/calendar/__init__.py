"""Google Calendar provider.

API docs:
  - Calendar: https://developers.google.com/workspace/calendar/api/v3/reference
"""

from .tools import (
    create_event,
    get_event,
    list_calendars,
    list_events,
    update_event,
)

__all__ = [
    "create_event",
    "get_event",
    "list_calendars",
    "list_events",
    "update_event",
]
