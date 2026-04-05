from datetime import datetime
from typing import Any, Dict, List, Optional


class GoogleCalendarProxy:
    """Lightweight proxy for common Google Calendar API operations.

    Usage:
        proxy = GoogleCalendarProxy(service, calendar_id)
        events = proxy.list_events(time_min=rfc3339_string)
        mapping = proxy.events_map_by_start(events)
        body = proxy.build_event_body(...)
        proxy.insert_event(body)
    """

    def __init__(self, service: Any, calendar_id: str):
        self.service = service
        self.calendar_id = calendar_id

    def list_events(
        self,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        single_events: bool = True,
        order_by: str = "startTime",
        max_results: int = 250,
    ) -> List[Dict]:
        params: Dict[str, Any] = {
            "calendarId": self.calendar_id,
            "singleEvents": single_events,
            "orderBy": order_by,
            "maxResults": max_results,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        resp = self.service.events().list(**params).execute()
        return resp.get("items", [])

    def insert_event(self, event_body: Dict) -> Dict:
        """Insert an event body into the configured calendar."""
        return self.service.events().insert(calendarId=self.calendar_id, body=event_body).execute()

    def events_map_by_start(self, events_list: List[Dict]) -> Dict[datetime, List[Dict]]:
        """Return a mapping from aware datetime -> list of events starting at that time.

        The function expects event['start']['dateTime'] to be an RFC3339 string; 'Z' is accepted.
        """
        mapping: Dict[datetime, List[Dict]] = {}
        for ev in events_list:
            start_str = ev.get("start", {}).get("dateTime")
            if not start_str:
                continue
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except Exception:
                # ignore unparsable timestamps
                continue
            mapping.setdefault(start_dt, []).append(ev)
        return mapping

    def build_event_body(
        self,
        summary: str,
        location: str,
        start: datetime,
        end: datetime,
        description: str = "",
        reminders: Optional[List[Dict]] = None,
        time_zone: str = "America/New_York",
    ) -> Dict:
        """Builds a Calendar API event body from the provided fields.

        Note: `start` and `end` are naive or aware datetimes. This formats them as
        YYYY-MM-DDTHH:MM:SS and sets the provided `time_zone` for the API.
        """
        if reminders is None:
            reminders = []

        body = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": time_zone},
            "end": {"dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": time_zone},
            "reminders": {"useDefault": False, "overrides": reminders},
        }
        return body

    def event_exists(self, summary: str, start: datetime, calendar_events_map: Dict[datetime, List[Dict]]) -> bool:
        """Return True if an event with the same summary exists at `start` in the provided map."""
        existing = calendar_events_map.get(start, [])
        for ev in existing:
            if ev.get("summary", "") == summary:
                return True
        return False
