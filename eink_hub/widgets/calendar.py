"""Calendar events widget."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("calendar")
class CalendarWidget(BaseWidget):
    """
    Calendar events display widget.

    Shows upcoming events from calendar provider.

    Options:
    - max_events: int (default: 5)
    - show_time: bool (default: True)
    - show_tomorrow: bool (default: True)
    - show_location: bool (default: False)
    """

    name = "calendar"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render calendar events."""
        if not data:
            self._render_no_data(draw, "No calendar data")
            return

        max_events = self.options.get("max_events", 5)
        show_time = self.options.get("show_time", True)
        show_tomorrow = self.options.get("show_tomorrow", True)
        show_location = self.options.get("show_location", False)

        today_events = data.get("today_events", [])
        tomorrow_events = data.get("tomorrow_events", [])

        title_font = self._load_font(16, bold=True)
        event_font = self._load_font(14)
        time_font = self._load_font(12)

        y = self.bounds.y
        events_shown = 0

        # Today's events
        if today_events:
            draw.text((self.bounds.x, y), "Today", font=title_font, fill=0)
            y += 22

            for event in today_events:
                if events_shown >= max_events:
                    break
                y = self._render_event(
                    draw, event, y, event_font, time_font, show_time, show_location
                )
                events_shown += 1

        # Tomorrow's events
        if show_tomorrow and tomorrow_events and events_shown < max_events:
            if today_events:
                y += 8  # Spacing between sections

            draw.text((self.bounds.x, y), "Tomorrow", font=title_font, fill=0)
            y += 22

            for event in tomorrow_events:
                if events_shown >= max_events:
                    break
                y = self._render_event(
                    draw, event, y, event_font, time_font, show_time, show_location
                )
                events_shown += 1

        # No events message
        if events_shown == 0:
            msg_font = self._load_font(14)
            draw.text(
                (self.bounds.x, self.bounds.y + 20),
                "No upcoming events",
                font=msg_font,
                fill=128,
            )

    def _render_event(
        self,
        draw: ImageDraw.ImageDraw,
        event: Dict[str, Any],
        y: int,
        event_font,
        time_font,
        show_time: bool,
        show_location: bool,
    ) -> int:
        """
        Render a single event.

        Returns the new y position after rendering.
        """
        x = self.bounds.x
        max_width = self.bounds.width

        title = event.get("title", "Untitled")
        time_str = event.get("time", "")
        all_day = event.get("all_day", False)
        location = event.get("location")

        # Time prefix
        if show_time and time_str and not all_day:
            time_text = f"{time_str}  "
            draw.text((x, y), time_text, font=time_font, fill=0)
            time_w, _ = self._text_size(draw, time_text, time_font)
            title_x = x + time_w
            title_max_w = max_width - time_w
        elif all_day:
            draw.text((x, y), "All day  ", font=time_font, fill=128)
            time_w, _ = self._text_size(draw, "All day  ", time_font)
            title_x = x + time_w
            title_max_w = max_width - time_w
        else:
            title_x = x
            title_max_w = max_width

        # Event title (truncated if needed)
        title = self._truncate_text(draw, title, event_font, title_max_w)
        draw.text((title_x, y), title, font=event_font, fill=0)
        y += 20

        # Location (optional)
        if show_location and location:
            loc_font = self._load_font(11)
            location = self._truncate_text(draw, f"📍 {location}", loc_font, max_width)
            draw.text((x + 10, y), location, font=loc_font, fill=128)
            y += 14

        return y

    def get_required_provider(self) -> Optional[str]:
        return "calendar"
