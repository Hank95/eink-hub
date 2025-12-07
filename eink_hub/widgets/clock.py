"""Clock/datetime widget."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("clock")
class ClockWidget(BaseWidget):
    """
    Date and time display widget.

    Options:
    - format: "12h" | "24h" (default: "12h")
    - show_date: bool (default: True)
    - show_day: bool (default: True)
    - show_seconds: bool (default: False)
    """

    name = "clock"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render the clock widget."""
        now = datetime.now()

        time_format = self.options.get("format", "12h")
        show_date = self.options.get("show_date", True)
        show_day = self.options.get("show_day", True)
        show_seconds = self.options.get("show_seconds", False)

        y = self.bounds.y

        # Time
        if time_format == "24h":
            if show_seconds:
                time_str = now.strftime("%H:%M:%S")
            else:
                time_str = now.strftime("%H:%M")
        else:
            if show_seconds:
                time_str = now.strftime("%I:%M:%S %p").lstrip("0")
            else:
                time_str = now.strftime("%I:%M %p").lstrip("0")

        time_font = self._load_font(36, bold=True)
        draw.text((self.bounds.x, y), time_str, font=time_font, fill=0)
        y += 44

        # Date
        if show_date:
            date_font = self._load_font(18)
            if show_day:
                date_str = now.strftime("%A, %B %d")
            else:
                date_str = now.strftime("%B %d, %Y")
            draw.text((self.bounds.x, y), date_str, font=date_font, fill=0)

    def get_required_provider(self) -> Optional[str]:
        return None  # Clock doesn't need a provider
