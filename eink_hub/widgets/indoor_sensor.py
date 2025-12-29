"""Indoor sensor display widget for ESP32 DHT11/BME280 data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from PIL import ImageDraw

from .base import BaseWidget, WidgetBounds
from .registry import WidgetRegistry


@WidgetRegistry.register("indoor_sensor")
class IndoorSensorWidget(BaseWidget):
    """
    Sensor display widget for ESP32 DHT11/BME280 data.

    Shows temperature, humidity, and optionally pressure/dew point
    from ESP32 sensors (DHT11 or BME280).

    Options:
    - compact: bool (default: False) - Minimal display
    - show_stats: bool (default: False) - Show 24h min/max/avg
    - show_sensor_id: bool (default: False) - Show sensor identifier
    - show_graph: bool (default: False) - Show historical graph
    - show_pressure: bool (default: True) - Show barometric pressure (BME280 only)
    - show_dew_point: bool (default: False) - Show dew point temperature
    - show_device_health: bool (default: False) - Show uptime/boot count
    - show_forecast: bool (default: False) - Show pressure-based weather forecast
    - title: str (default: "Sensor") - Label for the widget
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
        title = self.options.get("title", "Sensor")

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

        # Pressure (BME280) on same line if available
        show_pressure = self.options.get("show_pressure", True)
        pressure = data.get("pressure_hpa")
        if show_pressure and pressure is not None:
            draw.text((x + 50, y), f"{pressure}hPa", font=hum_font, fill=0)

        # Stale indicator
        if data.get("is_stale", False):
            warn_font = self._load_font(10)
            stale_x = x + 120 if pressure else x + 50
            draw.text((stale_x, y), "(stale)", font=warn_font, fill=128)

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
        title = self.options.get("title", "Sensor")
        sensor_id = data.get("sensor_id", "unknown")
        age_minutes = data.get("age_minutes", 0)
        is_stale = data.get("is_stale", False)
        show_graph = self.options.get("show_graph", False)
        show_pressure = self.options.get("show_pressure", True)
        show_dew_point = self.options.get("show_dew_point", False)
        show_device_health = self.options.get("show_device_health", False)

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

        # Pressure (BME280)
        pressure = data.get("pressure_hpa")
        if show_pressure and pressure is not None:
            draw.text((x, y), "Pressure", font=hum_label_font, fill=0)
            y += 14
            pressure_font = self._load_font(18, bold=True)
            draw.text((x, y), f"{pressure} hPa", font=pressure_font, fill=0)
            y += 24

        # Dew Point (BME280)
        dew_point = data.get("dew_point_f" if use_f else "dew_point_c")
        if show_dew_point and dew_point is not None:
            draw.text((x, y), "Dew Point", font=hum_label_font, fill=0)
            y += 14
            dew_font = self._load_font(16, bold=True)
            draw.text((x, y), f"{dew_point}°{unit}", font=dew_font, fill=0)
            y += 22

        # Weather Forecast (based on pressure trend)
        show_forecast = self.options.get("show_forecast", False)
        if show_forecast and pressure is not None and "history" in data:
            forecast = self._calculate_pressure_forecast(data["history"], pressure)

            y += 4
            draw.text((x, y), "Forecast", font=hum_label_font, fill=0)
            y += 14

            # Trend with symbol
            trend_font = self._load_font(14, bold=True)
            change_str = f"{forecast['change_3hr']:+.1f}" if forecast['change_3hr'] != 0 else "0.0"
            trend_text = f"{forecast['trend_symbol']} {change_str} hPa/3hr"
            draw.text((x, y), trend_text, font=trend_font, fill=0)
            y += 18

            # Prediction
            pred_font = self._load_font(12)
            draw.text((x, y), forecast["prediction"], font=pred_font, fill=0)
            y += 16

            # Conditions context
            if "conditions" in forecast:
                cond_font = self._load_font(10)
                draw.text((x, y), forecast["conditions"], font=cond_font, fill=128)
                y += 12

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

        # Device health (uptime/boot count) if enabled
        if show_device_health:
            uptime_s = data.get("uptime_s")
            boot_count = data.get("boot_count")

            if uptime_s is not None or boot_count is not None:
                health_parts = []
                if uptime_s is not None:
                    # Format uptime nicely
                    if uptime_s >= 86400:
                        days = uptime_s // 86400
                        hours = (uptime_s % 86400) // 3600
                        health_parts.append(f"Up: {days}d {hours}h")
                    elif uptime_s >= 3600:
                        hours = uptime_s // 3600
                        mins = (uptime_s % 3600) // 60
                        health_parts.append(f"Up: {hours}h {mins}m")
                    else:
                        mins = uptime_s // 60
                        health_parts.append(f"Up: {mins}m")
                if boot_count is not None:
                    health_parts.append(f"Boots: {boot_count}")

                draw.text((x, y), " | ".join(health_parts), font=detail_font, fill=128)
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
                y += 12

            # Pressure range (BME280)
            pressure_stats = stats.get("pressure", {})
            if show_pressure and pressure_stats:
                p_min = pressure_stats.get("min")
                p_max = pressure_stats.get("max")
                if p_min is not None and p_max is not None:
                    draw.text(
                        (x, y),
                        f"Press: {p_min}-{p_max} hPa",
                        font=stats_font,
                        fill=0
                    )
                    y += 12

            y += 4

        # Draw historical graphs if enabled
        if show_graph and "history" in data and len(data["history"]) >= 2:
            history = data["history"]

            # Extract temperature and humidity series
            temp_key = "temperature_f" if use_f else "temperature_c"
            temp_series = [h[temp_key] for h in history]
            humidity_series = [h["humidity"] for h in history]

            # Calculate graph dimensions - sized to fit within widget bounds
            graph_width = min(self.bounds.width - 10, 200)
            graph_height = 40

            y += 6

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
            y += graph_height + 14

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
            y += graph_height + 14

            # Pressure graph (BME280) if available
            pressure_series = [h.get("pressure_hpa") for h in history if h.get("pressure_hpa") is not None]
            if show_pressure and len(pressure_series) >= 2:
                self._draw_sparkline(
                    draw,
                    pressure_series,
                    x,
                    y,
                    graph_width,
                    graph_height,
                    label="Pressure hPa",
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

    def _calculate_pressure_forecast(
        self,
        history: List[Dict[str, Any]],
        current_pressure: float,
    ) -> Dict[str, Any]:
        """
        Calculate weather forecast based on pressure trends.

        Uses 3-hour pressure change to predict weather:
        - Rising rapidly (>2 hPa/3hr): Fair weather coming
        - Rising slowly (0.5-2 hPa/3hr): Weather improving
        - Stable (-0.5 to 0.5 hPa/3hr): No significant change
        - Falling slowly (-2 to -0.5 hPa/3hr): Weather may deteriorate
        - Falling rapidly (<-2 hPa/3hr): Storm likely approaching

        Also considers absolute pressure for general conditions.
        """
        forecast = {
            "trend": "stable",
            "trend_symbol": "→",
            "change_3hr": 0.0,
            "prediction": "No change expected",
            "confidence": "low",
        }

        if not history or current_pressure is None:
            return forecast

        # Get pressure readings from ~3 hours ago
        pressure_readings = [
            (h.get("pressure_hpa"), h.get("timestamp"))
            for h in history
            if h.get("pressure_hpa") is not None
        ]

        if len(pressure_readings) < 2:
            return forecast

        # Find reading closest to 3 hours ago
        import datetime as dt
        now = dt.datetime.now()
        target_time = now - dt.timedelta(hours=3)

        oldest_pressure = None
        oldest_time_diff = float('inf')

        for pressure, timestamp in pressure_readings:
            if isinstance(timestamp, str):
                try:
                    ts = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if ts.tzinfo:
                        ts = ts.replace(tzinfo=None)
                except:
                    continue
            else:
                ts = timestamp

            time_diff = abs((ts - target_time).total_seconds())
            if time_diff < oldest_time_diff:
                oldest_time_diff = time_diff
                oldest_pressure = pressure

        if oldest_pressure is None:
            # Fall back to oldest reading we have
            oldest_pressure = pressure_readings[0][0]

        # Calculate 3-hour change
        change_3hr = current_pressure - oldest_pressure
        forecast["change_3hr"] = round(change_3hr, 1)

        # Determine trend and prediction
        if change_3hr > 2:
            forecast["trend"] = "rising_fast"
            forecast["trend_symbol"] = "↑↑"
            forecast["prediction"] = "Fair weather ahead"
            forecast["confidence"] = "high"
        elif change_3hr > 0.5:
            forecast["trend"] = "rising"
            forecast["trend_symbol"] = "↑"
            forecast["prediction"] = "Weather improving"
            forecast["confidence"] = "medium"
        elif change_3hr < -2:
            forecast["trend"] = "falling_fast"
            forecast["trend_symbol"] = "↓↓"
            forecast["prediction"] = "Storm likely"
            forecast["confidence"] = "high"
        elif change_3hr < -0.5:
            forecast["trend"] = "falling"
            forecast["trend_symbol"] = "↓"
            forecast["prediction"] = "Rain possible"
            forecast["confidence"] = "medium"
        else:
            forecast["trend"] = "stable"
            forecast["trend_symbol"] = "→"
            forecast["prediction"] = "No change expected"
            forecast["confidence"] = "medium"

        # Add absolute pressure context
        if current_pressure > 1020:
            forecast["conditions"] = "High pressure"
        elif current_pressure < 1000:
            forecast["conditions"] = "Low pressure"
        else:
            forecast["conditions"] = "Normal pressure"

        return forecast

    def get_required_provider(self) -> Optional[str]:
        return "indoor_sensor"
