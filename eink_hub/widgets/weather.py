"""Weather display widget."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("weather")
class WeatherWidget(BaseWidget):
    """
    Weather display widget.

    Shows current temperature, conditions, and high/low.

    Options:
    - compact: bool (default: False) - Minimal display
    - show_feels_like: bool (default: False)
    - show_humidity: bool (default: False)
    - show_wind: bool (default: False)
    """

    name = "weather"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render weather information."""
        if not data:
            self._render_no_data(draw, "No weather data")
            return

        compact = self.options.get("compact", False)

        current_temp = data.get("current_temp", "--")
        condition = data.get("condition", "Unknown")
        high = data.get("high", "--")
        low = data.get("low", "--")

        y = self.bounds.y

        if compact:
            self._render_compact(draw, current_temp, condition, high, low)
        else:
            self._render_full(draw, data)

    def _render_compact(
        self,
        draw: ImageDraw.ImageDraw,
        temp: Any,
        condition: str,
        high: Any,
        low: Any,
    ) -> None:
        """Render compact weather view."""
        y = self.bounds.y

        # Temperature
        temp_font = self._load_font(32, bold=True)
        draw.text((self.bounds.x, y), f"{temp}°", font=temp_font, fill=0)

        # Condition on same line
        cond_font = self._load_font(14)
        draw.text((self.bounds.x + 70, y + 10), condition, font=cond_font, fill=0)

        # High/Low
        hl_font = self._load_font(14)
        y += 40
        draw.text((self.bounds.x, y), f"H:{high}° L:{low}°", font=hl_font, fill=0)

    def _render_full(
        self,
        draw: ImageDraw.ImageDraw,
        data: Dict[str, Any],
    ) -> None:
        """Render full weather view."""
        y = self.bounds.y

        current_temp = data.get("current_temp", "--")
        condition = data.get("condition", "Unknown")
        description = data.get("description", "")
        high = data.get("high", "--")
        low = data.get("low", "--")
        feels_like = data.get("feels_like")
        humidity = data.get("humidity")
        wind_speed = data.get("wind_speed")
        wind_unit = data.get("wind_unit", "mph")
        location = data.get("location", "")

        # Location (if space permits)
        if location and self.bounds.height > 80:
            loc_font = self._load_font(12)
            draw.text((self.bounds.x, y), location, font=loc_font, fill=0)
            y += 16

        # Temperature
        temp_font = self._load_font(42, bold=True)
        draw.text((self.bounds.x, y), f"{current_temp}°", font=temp_font, fill=0)

        # Condition next to temp
        cond_font = self._load_font(16)
        cond_y = y + 10
        draw.text((self.bounds.x + 80, cond_y), condition, font=cond_font, fill=0)

        # Description below condition
        if description and description != condition:
            desc_font = self._load_font(12)
            draw.text(
                (self.bounds.x + 80, cond_y + 20),
                description,
                font=desc_font,
                fill=0,
            )

        y += 50

        # High/Low
        hl_font = self._load_font(14)
        draw.text((self.bounds.x, y), f"H:{high}° L:{low}°", font=hl_font, fill=0)
        y += 20

        # Additional details based on options and space
        detail_font = self._load_font(12)

        if self.options.get("show_feels_like", False) and feels_like is not None:
            draw.text(
                (self.bounds.x, y),
                f"Feels like {feels_like}°",
                font=detail_font,
                fill=0,
            )
            y += 16

        if self.options.get("show_humidity", False) and humidity is not None:
            draw.text(
                (self.bounds.x, y),
                f"Humidity: {humidity}%",
                font=detail_font,
                fill=0,
            )
            y += 16

        if self.options.get("show_wind", False) and wind_speed is not None:
            draw.text(
                (self.bounds.x, y),
                f"Wind: {wind_speed} {wind_unit}",
                font=detail_font,
                fill=0,
            )

    def get_required_provider(self) -> Optional[str]:
        return "weather"
