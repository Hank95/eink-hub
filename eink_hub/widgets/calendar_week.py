"""Calendar week view widget - Apple Calendar style."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("calendar_week")
class CalendarWeekWidget(BaseWidget):
    """
    Week view calendar widget similar to Apple Calendar.

    Displays a 7-day grid with hours on the left and days across the top.
    Events are shown as blocks within their time slots.

    Options:
    - start_hour: int (default: 7) - First hour to display
    - end_hour: int (default: 22) - Last hour to display
    - show_current_time: bool (default: True) - Show current time indicator
    """

    name = "calendar_week"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render the week view calendar."""
        # Options
        start_hour = self.options.get("start_hour", 7)
        end_hour = self.options.get("end_hour", 22)
        show_current_time = self.options.get("show_current_time", True)

        # Layout constants
        header_height = 50
        time_column_width = 45

        # Calculate grid dimensions
        grid_x = self.bounds.x + time_column_width
        grid_y = self.bounds.y + header_height
        grid_width = self.bounds.width - time_column_width
        grid_height = self.bounds.height - header_height

        day_width = grid_width // 7
        hours = end_hour - start_hour
        hour_height = grid_height / hours if hours > 0 else grid_height

        # Get current date info
        now = dt.datetime.now()
        today = now.date()

        # Calculate week start (Monday)
        days_since_monday = today.weekday()
        week_start = today - dt.timedelta(days=days_since_monday)

        # Collect all events by date
        events_by_date = self._organize_events_by_date(data, week_start)

        # Draw header with day names and dates
        self._draw_header(draw, week_start, today, grid_x, day_width, header_height)

        # Draw time column
        self._draw_time_column(draw, start_hour, end_hour, grid_y, hour_height)

        # Draw grid lines
        self._draw_grid(draw, grid_x, grid_y, grid_width, grid_height, day_width, hour_height, hours)

        # Draw events
        self._draw_events(
            draw, events_by_date, week_start,
            grid_x, grid_y, day_width, hour_height,
            start_hour, end_hour
        )

        # Draw current time indicator
        if show_current_time and today >= week_start and today < week_start + dt.timedelta(days=7):
            self._draw_current_time(
                draw, now, week_start,
                grid_x, grid_y, day_width, hour_height,
                start_hour, end_hour
            )

    def _organize_events_by_date(
        self,
        data: Optional[Dict[str, Any]],
        week_start: dt.date
    ) -> Dict[dt.date, List[Dict]]:
        """Organize events by date for the week."""
        events_by_date: Dict[dt.date, List[Dict]] = {}

        if not data:
            return events_by_date

        # Initialize all days of the week
        for i in range(7):
            day = week_start + dt.timedelta(days=i)
            events_by_date[day] = []

        # Collect events from all categories
        all_events = []
        all_events.extend(data.get("today_events", []))
        all_events.extend(data.get("tomorrow_events", []))
        all_events.extend(data.get("upcoming_events", []))

        for event in all_events:
            start_iso = event.get("start_iso")
            if not start_iso:
                continue

            try:
                start_dt = dt.datetime.fromisoformat(start_iso)
                event_date = start_dt.date()

                if event_date in events_by_date:
                    events_by_date[event_date].append({
                        "title": event.get("title", ""),
                        "start": start_dt,
                        "time": event.get("time", ""),
                        "all_day": event.get("all_day", False),
                    })
            except (ValueError, TypeError):
                continue

        return events_by_date

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        week_start: dt.date,
        today: dt.date,
        grid_x: int,
        day_width: int,
        header_height: int,
    ) -> None:
        """Draw the day headers."""
        day_font = self._load_font(12, bold=True)
        date_font = self._load_font(18, bold=False)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(7):
            day = week_start + dt.timedelta(days=i)
            x_center = grid_x + i * day_width + day_width // 2

            # Day name
            day_name = day_names[i]
            w, _ = self._text_size(draw, day_name, day_font)
            draw.text((x_center - w // 2, self.bounds.y + 5), day_name, font=day_font, fill=0)

            # Date number
            date_str = str(day.day)
            w, h = self._text_size(draw, date_str, date_font)
            date_y = self.bounds.y + 22

            # Highlight today with a filled circle
            if day == today:
                circle_r = max(w, h) // 2 + 4
                draw.ellipse(
                    [x_center - circle_r, date_y - 2,
                     x_center + circle_r, date_y + h + 2],
                    fill=0
                )
                draw.text((x_center - w // 2, date_y), date_str, font=date_font, fill=255)
            else:
                draw.text((x_center - w // 2, date_y), date_str, font=date_font, fill=0)

    def _draw_time_column(
        self,
        draw: ImageDraw.ImageDraw,
        start_hour: int,
        end_hour: int,
        grid_y: int,
        hour_height: float,
    ) -> None:
        """Draw the time labels on the left."""
        time_font = self._load_font(10)

        for hour in range(start_hour, end_hour + 1):
            y = grid_y + (hour - start_hour) * hour_height

            # Format time (12-hour)
            if hour == 0:
                time_str = "12 AM"
            elif hour < 12:
                time_str = f"{hour} AM"
            elif hour == 12:
                time_str = "12 PM"
            else:
                time_str = f"{hour - 12} PM"

            w, h = self._text_size(draw, time_str, time_font)
            draw.text(
                (self.bounds.x + 40 - w, y - h // 2),
                time_str,
                font=time_font,
                fill=128
            )

    def _draw_grid(
        self,
        draw: ImageDraw.ImageDraw,
        grid_x: int,
        grid_y: int,
        grid_width: int,
        grid_height: int,
        day_width: int,
        hour_height: float,
        hours: int,
    ) -> None:
        """Draw the grid lines."""
        # Vertical lines between days
        for i in range(8):
            x = grid_x + i * day_width
            draw.line([(x, grid_y), (x, grid_y + grid_height)], fill=200, width=1)

        # Horizontal lines for hours
        for i in range(hours + 1):
            y = grid_y + i * hour_height
            draw.line([(grid_x, y), (grid_x + grid_width, y)], fill=200, width=1)

    def _draw_events(
        self,
        draw: ImageDraw.ImageDraw,
        events_by_date: Dict[dt.date, List[Dict]],
        week_start: dt.date,
        grid_x: int,
        grid_y: int,
        day_width: int,
        hour_height: float,
        start_hour: int,
        end_hour: int,
    ) -> None:
        """Draw events on the grid."""
        event_font = self._load_font(9)

        for i in range(7):
            day = week_start + dt.timedelta(days=i)
            events = events_by_date.get(day, [])

            day_x = grid_x + i * day_width + 2
            available_width = day_width - 4

            # Separate all-day and timed events
            all_day_events = [e for e in events if e.get("all_day")]
            timed_events = [e for e in events if not e.get("all_day")]

            # Draw all-day events at top of column
            all_day_y = grid_y + 2
            for event in all_day_events[:2]:  # Max 2 all-day events shown
                title = self._truncate_text(draw, event["title"], event_font, available_width - 4)
                # Draw small bar for all-day event
                draw.rectangle(
                    [day_x, all_day_y, day_x + available_width, all_day_y + 12],
                    fill=180
                )
                draw.text((day_x + 2, all_day_y + 1), title, font=event_font, fill=0)
                all_day_y += 14

            # Draw timed events
            for event in timed_events:
                start_dt = event.get("start")
                if not start_dt:
                    continue

                event_hour = start_dt.hour + start_dt.minute / 60.0

                # Skip if outside visible hours
                if event_hour < start_hour or event_hour >= end_hour:
                    continue

                # Calculate position
                y_offset = (event_hour - start_hour) * hour_height
                event_y = grid_y + y_offset

                # Event block height (assume 1 hour if no end time)
                block_height = max(hour_height * 0.9, 14)

                # Draw event block
                draw.rectangle(
                    [day_x, event_y + 1, day_x + available_width, event_y + block_height],
                    fill=220,
                    outline=100
                )

                # Draw event title
                title = self._truncate_text(draw, event["title"], event_font, available_width - 4)
                draw.text((day_x + 2, event_y + 2), title, font=event_font, fill=0)

    def _draw_current_time(
        self,
        draw: ImageDraw.ImageDraw,
        now: dt.datetime,
        week_start: dt.date,
        grid_x: int,
        grid_y: int,
        day_width: int,
        hour_height: float,
        start_hour: int,
        end_hour: int,
    ) -> None:
        """Draw the current time indicator line."""
        current_hour = now.hour + now.minute / 60.0

        # Only show if within visible hours
        if current_hour < start_hour or current_hour > end_hour:
            return

        # Calculate which day column
        days_from_start = (now.date() - week_start).days
        if days_from_start < 0 or days_from_start >= 7:
            return

        # Calculate y position
        y_offset = (current_hour - start_hour) * hour_height
        y = grid_y + y_offset

        # Calculate x range for current day
        day_x_start = grid_x + days_from_start * day_width
        day_x_end = day_x_start + day_width

        # Draw red line with circle at start
        draw.ellipse([day_x_start - 3, y - 3, day_x_start + 3, y + 3], fill=0)
        draw.line([(day_x_start, y), (day_x_end, y)], fill=0, width=2)

    def get_required_provider(self) -> Optional[str]:
        return "calendar"
