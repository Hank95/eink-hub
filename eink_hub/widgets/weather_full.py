"""Full-screen weather display widget."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("weather_full")
class WeatherFullWidget(BaseWidget):
    """
    Full-screen weather display widget.

    Shows current conditions prominently with hourly and 5-day forecast.
    Designed for 800x480 e-ink display.

    Options:
    - show_hourly: bool (default: True) - Show hourly forecast
    - show_daily: bool (default: True) - Show 5-day forecast
    - show_details: bool (default: True) - Show humidity, wind, feels like
    """

    name = "weather_full"

    # Use pure black (0) for all text - no grays for crisp e-ink rendering
    BLACK = 0
    WHITE = 255

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render the full weather display."""
        if not data:
            self._render_no_data(draw, "No weather data")
            return

        show_hourly = self.options.get("show_hourly", True)
        show_daily = self.options.get("show_daily", True)
        show_details = self.options.get("show_details", True)

        # Layout regions
        current_section_height = 195
        hourly_section_height = 105 if show_hourly else 0

        # Draw current conditions
        self._draw_current(draw, data, current_section_height, show_details)

        # Draw hourly forecast
        if show_hourly:
            hourly_y = self.bounds.y + current_section_height
            self._draw_hourly(draw, data.get("hourly", []), hourly_y, hourly_section_height)

        # Draw daily forecast
        if show_daily:
            daily_y = self.bounds.y + current_section_height + hourly_section_height
            daily_height = self.bounds.height - current_section_height - hourly_section_height
            self._draw_daily(draw, data.get("daily", []), daily_y, daily_height)

    def _draw_current(
        self,
        draw: ImageDraw.ImageDraw,
        data: Dict[str, Any],
        section_height: int,
        show_details: bool,
    ) -> None:
        """Draw the current conditions section."""
        x = self.bounds.x
        y = self.bounds.y
        width = self.bounds.width

        # Location
        location = data.get("location", "")
        loc_font = self._load_font(18)
        draw.text((x + 20, y + 12), location, font=loc_font, fill=self.BLACK)

        # Large temperature display
        current_temp = data.get("current_temp", "--")
        temp_font = self._load_font(100, bold=True)
        temp_str = f"{current_temp}°"
        draw.text((x + 20, y + 38), temp_str, font=temp_font, fill=self.BLACK)

        # Condition and description
        condition = data.get("condition", "Unknown")
        description = data.get("description", "")

        cond_font = self._load_font(32, bold=True)
        desc_font = self._load_font(20)

        # Position condition text to the right of temperature
        cond_x = x + 260
        draw.text((cond_x, y + 55), condition, font=cond_font, fill=self.BLACK)

        if description and description.lower() != condition.lower():
            draw.text((cond_x, y + 92), description, font=desc_font, fill=self.BLACK)

        # High/Low
        high = data.get("high", "--")
        low = data.get("low", "--")
        hl_font = self._load_font(22)
        draw.text((cond_x, y + 125), f"H: {high}°   L: {low}°", font=hl_font, fill=self.BLACK)

        # Details section on the right side
        if show_details:
            details_x = x + 560
            detail_font = self._load_font(18)
            detail_y = y + 55

            feels_like = data.get("feels_like")
            humidity = data.get("humidity")
            wind_speed = data.get("wind_speed")
            wind_unit = data.get("wind_unit", "mph")

            if feels_like is not None:
                draw.text((details_x, detail_y), f"Feels like: {feels_like}°", font=detail_font, fill=self.BLACK)
                detail_y += 30

            if humidity is not None:
                draw.text((details_x, detail_y), f"Humidity: {humidity}%", font=detail_font, fill=self.BLACK)
                detail_y += 30

            if wind_speed is not None:
                draw.text((details_x, detail_y), f"Wind: {wind_speed} {wind_unit}", font=detail_font, fill=self.BLACK)

        # Separator line
        line_y = y + section_height - 2
        draw.line([(x + 20, line_y), (x + width - 20, line_y)], fill=self.BLACK, width=1)

    def _draw_hourly(
        self,
        draw: ImageDraw.ImageDraw,
        hourly: List[Dict[str, Any]],
        y: int,
        height: int,
    ) -> None:
        """Draw the hourly forecast section."""
        x = self.bounds.x
        width = self.bounds.width

        if not hourly:
            return

        # Section title
        title_font = self._load_font(16, bold=True)
        draw.text((x + 20, y + 8), "HOURLY FORECAST", font=title_font, fill=self.BLACK)

        # Draw hourly items
        item_width = (width - 40) // min(len(hourly), 8)
        time_font = self._load_font(14)
        temp_font = self._load_font(20, bold=True)
        cond_font = self._load_font(13)

        for i, hour in enumerate(hourly[:8]):
            item_x = x + 20 + i * item_width
            item_center = item_x + item_width // 2

            # Time
            time_str = hour.get("time", "")
            tw, _ = self._text_size(draw, time_str, time_font)
            draw.text((item_center - tw // 2, y + 30), time_str, font=time_font, fill=self.BLACK)

            # Temperature
            temp = hour.get("temp", "--")
            temp_str = f"{temp}°"
            tw, _ = self._text_size(draw, temp_str, temp_font)
            draw.text((item_center - tw // 2, y + 48), temp_str, font=temp_font, fill=self.BLACK)

            # Condition (abbreviated)
            cond = hour.get("condition", "")[:5]
            tw, _ = self._text_size(draw, cond, cond_font)
            draw.text((item_center - tw // 2, y + 72), cond, font=cond_font, fill=self.BLACK)

            # Rain probability if significant
            pop = hour.get("pop", 0)
            if pop >= 20:
                pop_str = f"{pop}%"
                tw, _ = self._text_size(draw, pop_str, cond_font)
                draw.text((item_center - tw // 2, y + 88), pop_str, font=cond_font, fill=self.BLACK)

        # Separator line
        line_y = y + height - 2
        draw.line([(x + 20, line_y), (x + width - 20, line_y)], fill=self.BLACK, width=1)

    def _draw_daily(
        self,
        draw: ImageDraw.ImageDraw,
        daily: List[Dict[str, Any]],
        y: int,
        height: int,
    ) -> None:
        """Draw the 5-day forecast section."""
        x = self.bounds.x
        width = self.bounds.width

        if not daily:
            return

        # Section title
        title_font = self._load_font(16, bold=True)
        draw.text((x + 20, y + 8), "5-DAY FORECAST", font=title_font, fill=self.BLACK)

        # Draw daily items as rows
        day_font = self._load_font(18, bold=True)
        cond_font = self._load_font(16)
        temp_font = self._load_font(18)

        row_height = (height - 35) // min(len(daily), 5)

        # Calculate temp range once for all days
        all_highs = [d.get("high", 0) for d in daily]
        all_lows = [d.get("low", 0) for d in daily]
        temp_min = min(all_lows) - 5
        temp_max = max(all_highs) + 5
        temp_range = temp_max - temp_min if temp_max != temp_min else 1

        for i, day in enumerate(daily[:5]):
            row_y = y + 32 + i * row_height

            # Day name
            day_name = day.get("day_name", "")
            if i == 0:
                day_name = "Today"
            draw.text((x + 20, row_y), day_name, font=day_font, fill=self.BLACK)

            # Condition
            condition = day.get("condition", "")
            draw.text((x + 110, row_y), condition, font=cond_font, fill=self.BLACK)

            # Rain probability
            pop = day.get("pop", 0)
            if pop >= 20:
                pop_str = f"{pop}%"
                draw.text((x + 260, row_y), pop_str, font=cond_font, fill=self.BLACK)

            # Temperature bar visualization
            high = day.get("high", 0)
            low = day.get("low", 0)

            # Draw temp range bar
            bar_x = x + 380
            bar_width = 260
            bar_height = 14
            bar_y = row_y + 4

            # Calculate bar positions
            low_pos = int((low - temp_min) / temp_range * bar_width)
            high_pos = int((high - temp_min) / temp_range * bar_width)

            # Draw temperature range bar (outlined rectangle for crisp look)
            draw.rectangle(
                [bar_x + low_pos, bar_y, bar_x + high_pos, bar_y + bar_height],
                fill=self.BLACK
            )

            # Draw low and high temps
            low_str = f"{low}°"
            high_str = f"{high}°"

            lw, _ = self._text_size(draw, low_str, temp_font)
            draw.text((bar_x + low_pos - lw - 8, row_y), low_str, font=temp_font, fill=self.BLACK)
            draw.text((bar_x + high_pos + 8, row_y), high_str, font=temp_font, fill=self.BLACK)

    def get_required_provider(self) -> Optional[str]:
        return "weather"
