"""Indoor sensor display widget for ESP32 DHT11 data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("indoor_sensor")
class IndoorSensorWidget(BaseWidget):
    """
    Indoor sensor display widget.

    Shows temperature and humidity from ESP32 DHT11 sensors.

    Options:
    - compact: bool (default: False) - Minimal display
    - show_stats: bool (default: False) - Show 24h min/max/avg
    - show_sensor_id: bool (default: False) - Show sensor identifier
    - show_graph: bool (default: False) - Show historical graph
    - title: str (default: "Indoor") - Label for the widget
    - use_fahrenheit: bool (default: True) - Display in Fahrenheit
    """

    name = "indoor_sensor"

    def render(
        self,
        draw: ImageDraw.ImageDraw,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Render indoor sensor information."""
        if not data or not data.get("available", False):
            error_msg = data.get("error", "No sensor data") if data else "No sensor data"
            self._render_no_data(draw, error_msg)
            return

        compact = self.options.get("compact", False)

        if compact:
            self._render_compact(draw, data)
        else:
            self._render_full(draw, data)

    def _render_compact(
        self,
        draw: ImageDraw.ImageDraw,
        data: Dict[str, Any],
    ) -> None:
        """Render compact indoor sensor view."""
        y = self.bounds.y
        x = self.bounds.x

        use_f = self.options.get("use_fahrenheit", True)
        temp = data.get("temperature_f" if use_f else "temperature_c", "--")
        humidity = data.get("humidity", "--")
        unit = "F" if use_f else "C"
        title = self.options.get("title", "Indoor")

        # Title
        title_font = self._load_font(12)
        draw.text((x, y), title, font=title_font, fill=0)
        y += 16

        # Temperature
        temp_font = self._load_font(28, bold=True)
        draw.text((x, y), f"{temp}°{unit}", font=temp_font, fill=0)
        y += 34

        # Humidity
        hum_font = self._load_font(14)
        draw.text((x, y), f"{humidity}%", font=hum_font, fill=0)

        # Stale indicator
        if data.get("is_stale", False):
            warn_font = self._load_font(10)
            draw.text((x + 50, y), "(stale)", font=warn_font, fill=128)

    def _render_full(
        self,
        draw: ImageDraw.ImageDraw,
        data: Dict[str, Any],
    ) -> None:
        """Render full indoor sensor view."""
        y = self.bounds.y
        x = self.bounds.x

        use_f = self.options.get("use_fahrenheit", True)
        temp = data.get("temperature_f" if use_f else "temperature_c", "--")
        humidity = data.get("humidity", "--")
        unit = "F" if use_f else "C"
        title = self.options.get("title", "Indoor")
        sensor_id = data.get("sensor_id", "unknown")
        age_minutes = data.get("age_minutes", 0)
        is_stale = data.get("is_stale", False)
        show_graph = self.options.get("show_graph", False)

        # Title
        title_font = self._load_font(14, bold=True)
        draw.text((x, y), title, font=title_font, fill=0)
        y += 20

        # Temperature (large)
        temp_font = self._load_font(42, bold=True)
        draw.text((x, y), f"{temp}°", font=temp_font, fill=0)

        # Unit next to temp
        unit_font = self._load_font(18)
        draw.text((x + 75, y + 5), unit, font=unit_font, fill=0)

        y += 50

        # Humidity
        hum_label_font = self._load_font(12)
        hum_value_font = self._load_font(24, bold=True)

        draw.text((x, y), "Humidity", font=hum_label_font, fill=0)
        y += 14
        draw.text((x, y), f"{humidity}%", font=hum_value_font, fill=0)
        y += 30

        # Last updated
        detail_font = self._load_font(10)
        if age_minutes == 0:
            age_text = "Just now"
        elif age_minutes == 1:
            age_text = "1 min ago"
        else:
            age_text = f"{age_minutes} min ago"

        if is_stale:
            age_text = f"{age_text} (stale!)"

        draw.text((x, y), age_text, font=detail_font, fill=128 if is_stale else 0)
        y += 14

        # Sensor ID if enabled
        if self.options.get("show_sensor_id", False):
            draw.text((x, y), sensor_id, font=detail_font, fill=128)
            y += 14

        # Stats if enabled and available
        if self.options.get("show_stats", False) and "stats" in data:
            stats = data["stats"]
            temp_stats = stats.get("temperature", {})
            hum_stats = stats.get("humidity", {})

            y += 4
            stats_font = self._load_font(10)

            # Temperature range
            temp_key = "min_f" if use_f else "min_c"
            temp_max_key = "max_f" if use_f else "max_c"
            t_min = temp_stats.get(temp_key, "--")
            t_max = temp_stats.get(temp_max_key, "--")

            if t_min is not None and t_max is not None:
                draw.text(
                    (x, y),
                    f"24h: {t_min}°-{t_max}°{unit}",
                    font=stats_font,
                    fill=0
                )
                y += 12

            # Humidity range
            h_min = hum_stats.get("min", "--")
            h_max = hum_stats.get("max", "--")

            if h_min is not None and h_max is not None:
                draw.text(
                    (x, y),
                    f"Hum: {h_min}%-{h_max}%",
                    font=stats_font,
                    fill=0
                )
                y += 16

        # Draw historical graphs if enabled
        if show_graph and "history" in data and len(data["history"]) >= 2:
            history = data["history"]

            # Extract temperature and humidity series
            temp_key = "temperature_f" if use_f else "temperature_c"
            temp_series = [h[temp_key] for h in history]
            humidity_series = [h["humidity"] for h in history]

            # Calculate graph dimensions
            graph_width = min(self.bounds.width - 10, 200)
            graph_height = 50

            y += 8

            # Temperature graph
            self._draw_sparkline(
                draw,
                temp_series,
                x,
                y,
                graph_width,
                graph_height,
                label=f"Temp °{unit}",
                show_range=True,
            )
            y += graph_height + 18

            # Humidity graph
            self._draw_sparkline(
                draw,
                humidity_series,
                x,
                y,
                graph_width,
                graph_height,
                label="Humidity %",
                show_range=True,
            )

    def _draw_sparkline(
        self,
        draw: ImageDraw.ImageDraw,
        data: List[float],
        x: int,
        y: int,
        width: int,
        height: int,
        label: str = "",
        show_range: bool = True,
    ) -> None:
        """Draw a sparkline graph."""
        if not data or len(data) < 2:
            return

        # Calculate min/max for scaling
        data_min = min(data)
        data_max = max(data)
        data_range = data_max - data_min

        # Add padding to range
        if data_range == 0:
            data_range = 1
            data_min -= 0.5
            data_max += 0.5

        # Reserve space for labels
        label_width = 35 if show_range else 0
        graph_width = width - label_width - 4
        graph_height = height - 4

        # Draw border
        draw.rectangle(
            [x, y, x + width - label_width, y + height],
            outline=180,
            width=1
        )

        # Calculate points
        points: List[Tuple[float, float]] = []
        for i, value in enumerate(data):
            px = x + 2 + (i / (len(data) - 1)) * graph_width
            # Invert Y (0 at top)
            normalized = (value - data_min) / data_range
            py = y + height - 2 - (normalized * graph_height)
            points.append((px, py))

        # Draw the line
        if len(points) >= 2:
            draw.line(points, fill=0, width=1)

        # Draw current value dot at the end
        if points:
            last_point = points[-1]
            draw.ellipse(
                [last_point[0] - 2, last_point[1] - 2,
                 last_point[0] + 2, last_point[1] + 2],
                fill=0
            )

        # Draw range labels
        if show_range:
            range_font = self._load_font(9)
            label_x = x + width - label_width + 4

            # Max value at top
            draw.text(
                (label_x, y),
                f"{data_max:.1f}",
                font=range_font,
                fill=0
            )

            # Min value at bottom
            draw.text(
                (label_x, y + height - 10),
                f"{data_min:.1f}",
                font=range_font,
                fill=0
            )

        # Draw label if provided
        if label:
            label_font = self._load_font(9)
            draw.text((x + 2, y - 11), label, font=label_font, fill=0)

    def get_required_provider(self) -> Optional[str]:
        return "indoor_sensor"
