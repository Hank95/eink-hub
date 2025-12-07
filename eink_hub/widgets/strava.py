"""Strava widgets - compact view and chart."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("strava_compact")
class StravaCompactWidget(BaseWidget):
    """
    Compact Strava display showing weekly total and recent runs.

    Options:
    - show_recent: bool (default: True) - Show recent runs list
    - max_runs: int (default: 3) - Max recent runs to show
    """

    name = "strava_compact"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render compact Strava view."""
        if not data:
            self._render_no_data(draw, "No Strava data")
            return

        week_total = data.get("week_total_miles", 0)
        recent_runs = data.get("recent_runs", [])
        show_recent = self.options.get("show_recent", True)
        max_runs = self.options.get("max_runs", 3)

        y = self.bounds.y

        # Week total - prominent display
        total_font = self._load_font(32, bold=True)
        draw.text(
            (self.bounds.x, y),
            f"{week_total:.1f} mi",
            font=total_font,
            fill=0,
        )

        label_font = self._load_font(12)
        draw.text(
            (self.bounds.x, y + 38),
            "this week",
            font=label_font,
            fill=0,
        )

        y += 60

        # Recent runs
        if show_recent and recent_runs:
            run_font = self._load_font(13)
            detail_font = self._load_font(11)

            for run in recent_runs[:max_runs]:
                if y + 35 > self.bounds.y + self.bounds.height:
                    break

                label = run.get("label", "Run")
                miles = run.get("miles", 0)
                pace = run.get("pace", "")

                # Truncate label if needed
                label = self._truncate_text(
                    draw, label, run_font, self.bounds.width - 10
                )
                draw.text((self.bounds.x, y), label, font=run_font, fill=0)
                y += 16

                details = f"{miles:.1f} mi"
                if pace:
                    details += f"  •  {pace}"
                draw.text((self.bounds.x, y), details, font=detail_font, fill=0)
                y += 22

    def get_required_provider(self) -> Optional[str]:
        return "strava"


@WidgetRegistry.register("strava_chart")
class StravaChartWidget(BaseWidget):
    """
    Bar chart showing weekly mileage breakdown (Mon-Sun).

    Options:
    - show_labels: bool (default: True) - Show day labels
    - show_max: bool (default: True) - Show max miles label
    - bar_color: int (default: 0) - Bar fill color
    """

    name = "strava_chart"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render weekly mileage bar chart."""
        if not data:
            self._render_no_data(draw, "No Strava data")
            return

        weekly_miles = data.get("weekly_miles", [0] * 7)
        show_labels = self.options.get("show_labels", True)
        show_max = self.options.get("show_max", True)
        bar_color = self.options.get("bar_color", 0)

        days = ["M", "T", "W", "T", "F", "S", "S"]

        # Chart dimensions
        padding = 5
        label_height = 20 if show_labels else 0
        chart_top = self.bounds.y + padding
        chart_bottom = self.bounds.y + self.bounds.height - label_height - padding
        chart_left = self.bounds.x + padding
        chart_right = self.bounds.x + self.bounds.width - padding

        chart_height = chart_bottom - chart_top
        chart_width = chart_right - chart_left

        # Draw chart border
        draw.rectangle(
            [chart_left, chart_top, chart_right, chart_bottom],
            outline=0,
            width=1,
        )

        # Calculate bar dimensions
        num_days = len(weekly_miles)
        max_miles = max(weekly_miles) if any(weekly_miles) else 1
        if max_miles <= 0:
            max_miles = 1

        bar_area_height = chart_height - 10  # Padding inside chart
        bar_spacing = chart_width / num_days
        bar_width = bar_spacing * 0.6

        label_font = self._load_font(12)

        for i, miles in enumerate(weekly_miles):
            # Bar position
            x_center = chart_left + (i + 0.5) * bar_spacing
            x0 = int(x_center - bar_width / 2)
            x1 = int(x_center + bar_width / 2)

            # Bar height
            if miles > 0:
                frac = miles / max_miles
                bar_h = int(frac * bar_area_height)
                y1 = chart_bottom - 5
                y0 = y1 - bar_h

                draw.rectangle([x0, y0, x1, y1], fill=bar_color, outline=bar_color)

            # Day label
            if show_labels:
                day_label = days[i] if i < len(days) else "?"
                lw, _ = self._text_size(draw, day_label, label_font)
                label_x = int(x_center - lw / 2)
                draw.text(
                    (label_x, chart_bottom + 3),
                    day_label,
                    font=label_font,
                    fill=0,
                )

        # Max miles label
        if show_max:
            max_font = self._load_font(10)
            max_label = f"Max: {max_miles:.1f} mi"
            mlw, _ = self._text_size(draw, max_label, max_font)
            draw.text(
                (chart_right - mlw - 3, chart_top + 3),
                max_label,
                font=max_font,
                fill=0,
            )

    def get_required_provider(self) -> Optional[str]:
        return "strava"
