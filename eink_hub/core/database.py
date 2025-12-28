"""SQLite database module for sensor data storage."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from eink_hub.core.logging import get_logger

logger = get_logger(__name__)


class SensorDatabase:
    """SQLite database for storing sensor readings from ESP32 devices."""

    def __init__(self, db_path: str = "sensors.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create sensor_readings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    temperature_c REAL NOT NULL,
                    humidity REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
                ON sensor_readings(sensor_id, timestamp DESC)
            """)

            # Migration: Add BME280 columns if they don't exist
            # SQLite doesn't have IF NOT EXISTS for ALTER TABLE, so we check first
            cursor.execute("PRAGMA table_info(sensor_readings)")
            existing_columns = {row["name"] for row in cursor.fetchall()}

            new_columns = [
                ("pressure_hpa", "REAL"),       # Barometric pressure from BME280
                ("dew_point_c", "REAL"),        # Calculated dew point
                ("uptime_s", "INTEGER"),        # ESP32 uptime in seconds
                ("boot_count", "INTEGER"),      # ESP32 boot counter
            ]

            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE sensor_readings ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Added column {col_name} to sensor_readings table")

            conn.commit()
            logger.info(f"Sensor database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def insert_reading(
        self,
        sensor_id: str,
        temperature_c: float,
        humidity: float,
        timestamp: Optional[datetime] = None,
        pressure_hpa: Optional[float] = None,
        dew_point_c: Optional[float] = None,
        uptime_s: Optional[int] = None,
        boot_count: Optional[int] = None,
    ) -> int:
        """Insert a new sensor reading with optional BME280 fields."""
        if timestamp is None:
            timestamp = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sensor_readings
                    (sensor_id, temperature_c, humidity, timestamp,
                     pressure_hpa, dew_point_c, uptime_s, boot_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sensor_id, temperature_c, humidity, timestamp,
                 pressure_hpa, dew_point_c, uptime_s, boot_count)
            )
            conn.commit()
            reading_id = cursor.lastrowid

            # Log with pressure if available (BME280 sensor)
            if pressure_hpa is not None:
                logger.debug(
                    f"Inserted reading {reading_id} from {sensor_id}: "
                    f"{temperature_c}°C, {humidity}%, {pressure_hpa}hPa"
                )
            else:
                logger.debug(
                    f"Inserted reading {reading_id} from {sensor_id}: "
                    f"{temperature_c}°C, {humidity}%"
                )
            return reading_id

    def get_latest_reading(self, sensor_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent reading, optionally filtered by sensor_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if sensor_id:
                cursor.execute(
                    """
                    SELECT * FROM sensor_readings
                    WHERE sensor_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (sensor_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM sensor_readings
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_readings(
        self,
        sensor_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get readings from the last N hours."""
        since = datetime.now() - timedelta(hours=hours)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if sensor_id:
                cursor.execute(
                    """
                    SELECT * FROM sensor_readings
                    WHERE sensor_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (sensor_id, since, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM sensor_readings
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (since, limit)
                )

            return [dict(row) for row in cursor.fetchall()]

    def get_stats(
        self,
        sensor_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get min/max/avg statistics for the last N hours."""
        since = datetime.now() - timedelta(hours=hours)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if sensor_id:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as reading_count,
                        MIN(temperature_c) as temp_min,
                        MAX(temperature_c) as temp_max,
                        AVG(temperature_c) as temp_avg,
                        MIN(humidity) as humidity_min,
                        MAX(humidity) as humidity_max,
                        AVG(humidity) as humidity_avg,
                        MIN(pressure_hpa) as pressure_min,
                        MAX(pressure_hpa) as pressure_max,
                        AVG(pressure_hpa) as pressure_avg,
                        MIN(dew_point_c) as dew_min,
                        MAX(dew_point_c) as dew_max,
                        AVG(dew_point_c) as dew_avg
                    FROM sensor_readings
                    WHERE sensor_id = ? AND timestamp >= ?
                    """,
                    (sensor_id, since)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as reading_count,
                        MIN(temperature_c) as temp_min,
                        MAX(temperature_c) as temp_max,
                        AVG(temperature_c) as temp_avg,
                        MIN(humidity) as humidity_min,
                        MAX(humidity) as humidity_max,
                        AVG(humidity) as humidity_avg,
                        MIN(pressure_hpa) as pressure_min,
                        MAX(pressure_hpa) as pressure_max,
                        AVG(pressure_hpa) as pressure_avg,
                        MIN(dew_point_c) as dew_min,
                        MAX(dew_point_c) as dew_max,
                        AVG(dew_point_c) as dew_avg
                    FROM sensor_readings
                    WHERE timestamp >= ?
                    """,
                    (since,)
                )

            row = cursor.fetchone()
            if row and row["reading_count"] > 0:
                result = {
                    "reading_count": row["reading_count"],
                    "temperature": {
                        "min": round(row["temp_min"], 1),
                        "max": round(row["temp_max"], 1),
                        "avg": round(row["temp_avg"], 1)
                    },
                    "humidity": {
                        "min": round(row["humidity_min"], 1),
                        "max": round(row["humidity_max"], 1),
                        "avg": round(row["humidity_avg"], 1)
                    }
                }

                # Add pressure stats if available (BME280 sensors)
                if row["pressure_min"] is not None:
                    result["pressure"] = {
                        "min": round(row["pressure_min"], 1),
                        "max": round(row["pressure_max"], 1),
                        "avg": round(row["pressure_avg"], 1)
                    }

                # Add dew point stats if available
                if row["dew_min"] is not None:
                    result["dew_point"] = {
                        "min": round(row["dew_min"], 1),
                        "max": round(row["dew_max"], 1),
                        "avg": round(row["dew_avg"], 1)
                    }

                return result

            return {
                "reading_count": 0,
                "temperature": {"min": None, "max": None, "avg": None},
                "humidity": {"min": None, "max": None, "avg": None}
            }

    def get_all_sensors(self) -> List[str]:
        """Get list of all unique sensor IDs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT sensor_id FROM sensor_readings ORDER BY sensor_id"
            )
            return [row["sensor_id"] for row in cursor.fetchall()]

    def cleanup_old_readings(self, days: int = 30) -> int:
        """Delete readings older than N days. Returns count of deleted rows."""
        cutoff = datetime.now() - timedelta(days=days)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sensor_readings WHERE timestamp < ?",
                (cutoff,)
            )
            conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old sensor readings")
            return deleted


# Global instance
_db_instance: Optional[SensorDatabase] = None


def get_sensor_db(db_path: str = "sensors.db") -> SensorDatabase:
    """Get or create the global sensor database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SensorDatabase(db_path)
    return _db_instance
