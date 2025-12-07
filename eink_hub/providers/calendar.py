"""iCal calendar provider."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import httpx
from icalendar import Calendar

from ..core.exceptions import ProviderError
from ..core.logging import get_logger
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.calendar")


@ProviderRegistry.register("calendar")
class CalendarProvider(BaseProvider):
    """
    Calendar events provider using iCal feeds.

    Fetches:
    - Today's events
    - Tomorrow's events
    - Upcoming events (next 7 days)

    Required options:
    - ical_url: URL to .ics feed

    Optional options:
    - timezone: Timezone for event display (default: system local)
    - max_events: Maximum events to return (default: 20)
    """

    name = "calendar"

    def _validate_config(self) -> None:
        """Validate calendar config."""
        self._require_option("ical_url")

    async def fetch(self) -> ProviderData:
        """Fetch and parse iCal feed."""
        try:
            ical_url = self.options["ical_url"]

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ical_url)
                resp.raise_for_status()
                ical_text = resp.text

            events = self._parse_ical(ical_text)
            categorized = self._categorize_events(events)

            logger.info(
                f"Fetched calendar: {len(categorized['today_events'])} events today"
            )

            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data=categorized,
                ttl_seconds=900,  # 15 minutes
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Calendar fetch error: {e.response.status_code}")
            raise ProviderError(self.name, f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Calendar fetch failed: {e}")
            raise ProviderError(self.name, str(e))

    def get_default_refresh_interval(self) -> int:
        return 15

    def _parse_ical(self, ical_text: str) -> List[Dict[str, Any]]:
        """Parse iCal text into event list."""
        cal = Calendar.from_ical(ical_text)
        events = []

        # Get timezone from options or use local
        tz_name = self.options.get("timezone")
        if tz_name:
            local_tz = ZoneInfo(tz_name)
        else:
            local_tz = dt.datetime.now().astimezone().tzinfo

        now = dt.datetime.now(local_tz)
        max_date = now + dt.timedelta(days=7)

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            dtstart = component.get("dtstart")
            if not dtstart:
                continue

            start = dtstart.dt

            # Handle all-day events (date only, no time)
            if isinstance(start, dt.date) and not isinstance(start, dt.datetime):
                start = dt.datetime.combine(start, dt.time.min, tzinfo=local_tz)
                all_day = True
            else:
                # Ensure timezone-aware
                if start.tzinfo is None:
                    start = start.replace(tzinfo=local_tz)
                else:
                    start = start.astimezone(local_tz)
                all_day = False

            # Skip past events and far-future events
            if start < now - dt.timedelta(hours=1):
                continue
            if start > max_date:
                continue

            # Get end time
            dtend = component.get("dtend")
            if dtend:
                end = dtend.dt
                if isinstance(end, dt.date) and not isinstance(end, dt.datetime):
                    end = dt.datetime.combine(end, dt.time.max, tzinfo=local_tz)
                elif end.tzinfo is None:
                    end = end.replace(tzinfo=local_tz)
                else:
                    end = end.astimezone(local_tz)
            else:
                end = start + dt.timedelta(hours=1)

            summary = str(component.get("summary", "Untitled"))
            location = str(component.get("location", "")) if component.get("location") else None

            events.append({
                "title": summary,
                "start": start,
                "end": end,
                "all_day": all_day,
                "location": location,
                "time": "" if all_day else start.strftime("%I:%M %p").lstrip("0"),
            })

        # Sort by start time
        events.sort(key=lambda e: e["start"])

        max_events = self.options.get("max_events", 20)
        return events[:max_events]

    def _categorize_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize events by day."""
        now = dt.datetime.now().astimezone()
        today = now.date()
        tomorrow = today + dt.timedelta(days=1)

        today_events = []
        tomorrow_events = []
        upcoming_events = []

        for event in events:
            event_date = event["start"].date()

            # Create serializable version
            event_data = {
                "title": event["title"],
                "time": event["time"],
                "all_day": event["all_day"],
                "location": event["location"],
                "start_iso": event["start"].isoformat(),
            }

            if event_date == today:
                today_events.append(event_data)
            elif event_date == tomorrow:
                tomorrow_events.append(event_data)
            else:
                # Add day name for upcoming events
                event_data["day"] = event["start"].strftime("%A")
                upcoming_events.append(event_data)

        return {
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "upcoming_events": upcoming_events,
            "total_count": len(events),
        }
