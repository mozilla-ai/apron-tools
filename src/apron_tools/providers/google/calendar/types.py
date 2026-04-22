"""Pydantic models for Google Calendar API inputs and outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apron_tools.types import ToolResult

# ---------------------------------------------------------------------------
# Shared nested models
# ---------------------------------------------------------------------------


class EventDateTime(BaseModel):
    """A date or date-time with optional timezone."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    date: str | None = None
    date_time: str | None = Field(default=None, alias="dateTime")
    time_zone: str | None = Field(default=None, alias="timeZone")


class EventPerson(BaseModel):
    """A person (creator/organizer) on a calendar event."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email: str = ""
    display_name: str | None = Field(default=None, alias="displayName")
    self_: bool | None = Field(default=None, alias="self")


class EventAttendee(BaseModel):
    """An attendee of a calendar event."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email: str = ""
    display_name: str | None = Field(default=None, alias="displayName")
    response_status: str | None = Field(default=None, alias="responseStatus")


class CalendarListEntry(BaseModel):
    """A calendar entry from the calendarList endpoint."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    summary: str = ""
    description: str | None = None
    time_zone: str | None = Field(default=None, alias="timeZone")
    color_id: str | None = Field(default=None, alias="colorId")
    background_color: str | None = Field(default=None, alias="backgroundColor")
    foreground_color: str | None = Field(default=None, alias="foregroundColor")
    selected: bool | None = None
    access_role: str | None = Field(default=None, alias="accessRole")
    primary: bool | None = None


class CalendarEvent(BaseModel):
    """A single calendar event resource."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = ""
    status: str | None = None
    html_link: str | None = Field(default=None, alias="htmlLink")
    summary: str = ""
    description: str | None = None
    location: str | None = None
    creator: EventPerson | None = None
    organizer: EventPerson | None = None
    start: EventDateTime | None = None
    end: EventDateTime | None = None
    attendees: list[EventAttendee] | None = None


# ---------------------------------------------------------------------------
# Input parameter models
# ---------------------------------------------------------------------------


class ListCalendarsParams(BaseModel):
    """Parameters for listing calendars."""

    max_results: int = 100


class ListEventsParams(BaseModel):
    """Parameters for listing events in a calendar."""

    calendar_id: str = "primary"
    max_results: int = 250
    time_min: str | None = None
    time_max: str | None = None
    query: str | None = None
    page_token: str | None = None


class GetEventParams(BaseModel):
    """Parameters for retrieving a single event."""

    calendar_id: str = "primary"
    event_id: str


class CreateEventParams(BaseModel):
    """Parameters for creating a new event."""

    calendar_id: str = "primary"
    summary: str
    description: str | None = None
    location: str | None = None
    start: EventDateTime
    end: EventDateTime
    attendees: list[str] | None = None
    generate_meet_link: bool = True


class UpdateEventParams(BaseModel):
    """Parameters for updating an existing event."""

    calendar_id: str = "primary"
    event_id: str
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: EventDateTime | None = None
    end: EventDateTime | None = None
    attendees: list[str] | None = None
    generate_meet_link: bool = False


# ---------------------------------------------------------------------------
# Output result models
# ---------------------------------------------------------------------------


class ListCalendarsResult(ToolResult):
    """Result of listing calendars."""

    model_config = ConfigDict(extra="ignore")

    calendars: list[CalendarListEntry] = []

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the calendars."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.calendars:
            return "No calendars found."
        lines = [f"Found {len(self.calendars)} calendar(s):"]
        for cal in self.calendars:
            primary = " (primary)" if cal.primary else ""
            lines.append(f"  - {cal.summary}{primary} (id={cal.id})")
        return "\n".join(lines)


class ListEventsResult(ToolResult):
    """Result of listing events in a calendar."""

    model_config = ConfigDict(extra="ignore")

    events: list[CalendarEvent] = []
    next_page_token: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the events."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.events:
            return "No events found."
        lines = [f"Found {len(self.events)} event(s):"]
        for ev in self.events:
            time_str = ""
            if ev.start:
                time_str = ev.start.date_time or ev.start.date or ""
            lines.append(f"  - {ev.summary} ({time_str}) [id={ev.id}]")
        return "\n".join(lines)


class GetEventResult(ToolResult):
    """Result of retrieving a single event."""

    model_config = ConfigDict(extra="ignore")

    event: CalendarEvent | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the event."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.event:
            return "No event found."
        ev = self.event
        time_str = ""
        if ev.start:
            time_str = ev.start.date_time or ev.start.date or ""
        location = f"\nLocation: {ev.location}" if ev.location else ""
        description = f"\nDescription: {ev.description}" if ev.description else ""
        attendee_count = len(ev.attendees) if ev.attendees else 0
        attendees = f"\nAttendees: {attendee_count}" if attendee_count else ""
        return f"Event: {ev.summary}\nTime: {time_str}{location}{description}{attendees}"


class CreateEventResult(ToolResult):
    """Result of creating a new event."""

    model_config = ConfigDict(extra="ignore")

    event: CalendarEvent | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the created event."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.event:
            return "Event created but no details returned."
        ev = self.event
        link = f"\nLink: {ev.html_link}" if ev.html_link else ""
        return f"Event '{ev.summary}' created (id={ev.id}).{link}"


class UpdateEventResult(ToolResult):
    """Result of updating an existing event."""

    model_config = ConfigDict(extra="ignore")

    event: CalendarEvent | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_success(cls, data: Any) -> Any:
        """Set success=True when parsing raw API JSON."""
        if isinstance(data, dict) and "success" not in data:
            data["success"] = True
        return data

    def __str__(self) -> str:
        """Return an LLM-readable summary of the updated event."""
        if not self.success:
            return f"Error: {self.error}"
        if not self.event:
            return "Event updated but no details returned."
        ev = self.event
        link = f"\nLink: {ev.html_link}" if ev.html_link else ""
        return f"Event '{ev.summary}' updated (id={ev.id}).{link}"
