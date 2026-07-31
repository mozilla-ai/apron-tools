# Google Calendar testdata

- **Calendar API docs:** https://developers.google.com/workspace/calendar/api/v3/reference
- **Endpoint references:**
  - List calendars: https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list
  - List events: https://developers.google.com/workspace/calendar/api/v3/reference/events/list
  - Get event: https://developers.google.com/workspace/calendar/api/v3/reference/events/get
  - Insert event: https://developers.google.com/workspace/calendar/api/v3/reference/events/insert
  - Update event: https://developers.google.com/workspace/calendar/api/v3/reference/events/update
  - Freebusy query: https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query
- **Auth:** OAuth 2.0 Bearer token
- **list_calendars.json:** Based on CalendarList.list response.
- **list_events.json:** Based on Events.list response.
- **get_event.json:** Based on Events.get response (single event resource).
- **create_event.json:** Based on Events.insert response (single event resource).
- **update_event.json:** Based on Events.update response (single event resource).
- **check_availability.json:** Based on Freebusy.query response — one busy calendar, one free.
- **check_availability_all_free.json:** Based on Freebusy.query response — all calendars free (empty busy lists).
- **check_availability_error.json:** Based on Freebusy.query response — one calendar returns a per-calendar error.
