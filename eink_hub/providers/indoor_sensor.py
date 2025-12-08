"""Indoor sensor provider for ESP32 DHT11 data."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from ..core.database import get_sensor_db
from ..core.exceptions import ProviderError
from ..core.logging import get_logger
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.indoor_sensor")


@ProviderRegistry.register("indoor_sensor")
class IndoorSensorProvider(BaseProvider):
    """
    Indoor sensor data provider using SQLite database.

    Reads temperature and humidity data from ESP32 DHT11 sensors
    stored in the local SQLite database.

    Options:
    - sensor_id: Optional specific sensor to query (default: latest from any)
    - database: SQLite database path (default: sensors.db)
    - stats_hours: Hours of history for min/max/avg stats (default: 24)
    """

    name = "indoor_sensor"

    def _validate_config(self) -> None:
        """Validate indoor sensor provider config."""
        # No required credentials - data comes from local SQLite
        pass

    async def fetch(self) -> ProviderData:
        """Fetch latest sensor readings from database."""
        try:
            db_path = self.options.get("database", "sensors.db")
            sensor_id = self.options.get("sensor_id")
            stats_hours = self.options.get("stats_hours", 24)
            history_hours = self.options.get("history_hours", 6)

            db = get_sensor_db(db_path)

            # Get latest reading
            latest = db.get_latest_reading(sensor_id)

            if latest is None:
                logger.warning("No sensor readings found in database")
                return ProviderData(
                    provider_name=self.name,
                    fetched_at=dt.datetime.now(),
                    data={
                        "available": False,
                        "error": "No sensor data available"
                    },
                    ttl_seconds=60,
                )

            # Get statistics for the time period
            stats = db.get_stats(sensor_id, hours=stats_hours)

            # Get list of all sensors
            sensors = db.get_all_sensors()

            # Get historical readings for graphs
            history = db.get_readings(sensor_id, hours=history_hours, limit=500)

            # Convert temperature to Fahrenheit
            temp_c = latest["temperature_c"]
            temp_f = (temp_c * 9 / 5) + 32

            # Parse timestamp
            timestamp = latest["timestamp"]
            if isinstance(timestamp, str):
                timestamp = dt.datetime.fromisoformat(timestamp)

            # Calculate age of reading
            age_seconds = (dt.datetime.now() - timestamp).total_seconds()
            age_minutes = int(age_seconds / 60)

            # Determine if reading is stale (older than 5 minutes)
            is_stale = age_seconds > 300

            # Process history for graphing (reverse to chronological order)
            history_data = []
            for reading in reversed(history):
                r_temp_c = reading["temperature_c"]
                history_data.append({
                    "temperature_c": r_temp_c,
                    "temperature_f": round((r_temp_c * 9 / 5) + 32, 1),
                    "humidity": reading["humidity"],
                    "timestamp": reading["timestamp"],
                })

            data = {
                "available": True,
                "sensor_id": latest["sensor_id"],
                "temperature_c": round(temp_c, 1),
                "temperature_f": round(temp_f, 1),
                "humidity": round(latest["humidity"], 1),
                "timestamp": timestamp.isoformat(),
                "age_minutes": age_minutes,
                "is_stale": is_stale,
                "stats": {
                    "hours": stats_hours,
                    "reading_count": stats["reading_count"],
                    "temperature": {
                        "min_c": stats["temperature"]["min"],
                        "max_c": stats["temperature"]["max"],
                        "avg_c": stats["temperature"]["avg"],
                        "min_f": round((stats["temperature"]["min"] * 9 / 5) + 32, 1) if stats["temperature"]["min"] else None,
                        "max_f": round((stats["temperature"]["max"] * 9 / 5) + 32, 1) if stats["temperature"]["max"] else None,
                        "avg_f": round((stats["temperature"]["avg"] * 9 / 5) + 32, 1) if stats["temperature"]["avg"] else None,
                    },
                    "humidity": stats["humidity"]
                },
                "history": history_data,
                "sensors": sensors,
            }

            logger.info(
                f"Fetched indoor sensor: {data['temperature_f']}°F, {data['humidity']}% "
                f"from {data['sensor_id']} ({age_minutes}m ago, {len(history_data)} history points)"
            )

            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data=data,
                ttl_seconds=60,  # Short TTL since sensor updates frequently
            )

        except Exception as e:
            logger.error(f"Indoor sensor fetch failed: {e}")
            raise ProviderError(self.name, str(e))

    def get_default_refresh_interval(self) -> int:
        """Default refresh every 2 minutes."""
        return 2
