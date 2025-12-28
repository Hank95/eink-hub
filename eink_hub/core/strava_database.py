"""SQLite database module for Strava activity storage."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from eink_hub.core.logging import get_logger

logger = get_logger(__name__)


class StravaDatabase:
    """SQLite database for storing Strava activities."""

    def __init__(self, db_path: str = "strava.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create activities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strava_activities (
                    id INTEGER PRIMARY KEY,
                    strava_id INTEGER UNIQUE NOT NULL,
                    name TEXT,
                    type TEXT NOT NULL,
                    distance_meters REAL NOT NULL,
                    moving_time_seconds INTEGER NOT NULL,
                    elapsed_time_seconds INTEGER,
                    total_elevation_gain REAL,
                    start_date TEXT NOT NULL,
                    start_date_local TEXT,
                    timezone TEXT,
                    average_speed REAL,
                    max_speed REAL,
                    average_heartrate REAL,
                    max_heartrate REAL,
                    calories REAL,
                    raw_data TEXT,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_strava_type_date
                ON strava_activities(type, start_date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_strava_date
                ON strava_activities(start_date DESC)
            """)

            conn.commit()
            logger.info(f"Strava database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def upsert_activity(self, activity: Dict[str, Any]) -> bool:
        """
        Insert or update an activity.

        Returns True if a new activity was inserted, False if updated.
        """
        import json

        strava_id = activity.get("id")
        if not strava_id:
            logger.warning("Activity missing id, skipping")
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if activity exists
            cursor.execute(
                "SELECT id FROM strava_activities WHERE strava_id = ?",
                (strava_id,)
            )
            exists = cursor.fetchone() is not None

            cursor.execute(
                """
                INSERT INTO strava_activities (
                    strava_id, name, type, distance_meters, moving_time_seconds,
                    elapsed_time_seconds, total_elevation_gain, start_date,
                    start_date_local, timezone, average_speed, max_speed,
                    average_heartrate, max_heartrate, calories, raw_data, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strava_id) DO UPDATE SET
                    name = excluded.name,
                    type = excluded.type,
                    distance_meters = excluded.distance_meters,
                    moving_time_seconds = excluded.moving_time_seconds,
                    elapsed_time_seconds = excluded.elapsed_time_seconds,
                    total_elevation_gain = excluded.total_elevation_gain,
                    start_date = excluded.start_date,
                    start_date_local = excluded.start_date_local,
                    timezone = excluded.timezone,
                    average_speed = excluded.average_speed,
                    max_speed = excluded.max_speed,
                    average_heartrate = excluded.average_heartrate,
                    max_heartrate = excluded.max_heartrate,
                    calories = excluded.calories,
                    raw_data = excluded.raw_data,
                    fetched_at = excluded.fetched_at
                """,
                (
                    strava_id,
                    activity.get("name"),
                    activity.get("type", "Unknown"),
                    activity.get("distance", 0),
                    activity.get("moving_time", 0),
                    activity.get("elapsed_time"),
                    activity.get("total_elevation_gain"),
                    activity.get("start_date"),
                    activity.get("start_date_local"),
                    activity.get("timezone"),
                    activity.get("average_speed"),
                    activity.get("max_speed"),
                    activity.get("average_heartrate"),
                    activity.get("max_heartrate"),
                    activity.get("calories"),
                    json.dumps(activity),
                    datetime.now()
                )
            )
            conn.commit()

            if not exists:
                logger.debug(f"Inserted new activity: {activity.get('name')} ({strava_id})")
            return not exists

    def upsert_activities(self, activities: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Insert or update multiple activities.

        Returns dict with counts of inserted and updated activities.
        """
        inserted = 0
        updated = 0

        for activity in activities:
            is_new = self.upsert_activity(activity)
            if is_new:
                inserted += 1
            else:
                updated += 1

        if inserted > 0:
            logger.info(f"Saved {inserted} new activities, {updated} updated")

        return {"inserted": inserted, "updated": updated}

    def get_activities(
        self,
        activity_type: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get activities with optional filters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM strava_activities WHERE 1=1"
            params: List[Any] = []

            if activity_type:
                query += " AND type = ?"
                params.append(activity_type)

            if days:
                since = (datetime.now() - timedelta(days=days)).isoformat()
                query += " AND start_date >= ?"
                params.append(since)

            query += " ORDER BY start_date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_runs(self, days: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get run activities."""
        return self.get_activities(activity_type="Run", days=days, limit=limit)

    def get_weekly_summary(
        self,
        activity_type: str = "Run",
        weeks_back: int = 0
    ) -> Dict[str, Any]:
        """
        Get summary for a specific week.

        Args:
            activity_type: Type of activity to summarize
            weeks_back: 0 = current week, 1 = last week, etc.

        Returns:
            Dict with week_total_miles, weekly_miles [Mon-Sun], activity_count
        """
        now = datetime.now()

        # Find start of target week (Monday)
        days_since_monday = now.weekday()
        start_of_this_week = now - timedelta(days=days_since_monday)
        start_of_week = start_of_this_week - timedelta(weeks=weeks_back)
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT start_date, distance_meters
                FROM strava_activities
                WHERE type = ? AND start_date >= ? AND start_date < ?
                ORDER BY start_date
                """,
                (activity_type, start_of_week.isoformat(), end_of_week.isoformat())
            )

            weekly_miles = [0.0] * 7
            for row in cursor.fetchall():
                start_date = datetime.fromisoformat(
                    row["start_date"].replace("Z", "+00:00")
                )
                day_index = start_date.weekday()
                miles = row["distance_meters"] / 1609.34
                weekly_miles[day_index] += miles

            return {
                "week_start": start_of_week.strftime("%Y-%m-%d"),
                "week_total_miles": round(sum(weekly_miles), 1),
                "weekly_miles": [round(m, 1) for m in weekly_miles],
                "activity_count": sum(1 for m in weekly_miles if m > 0)
            }

    def get_monthly_totals(
        self,
        activity_type: str = "Run",
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """Get monthly mileage totals."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    strftime('%Y-%m', start_date) as month,
                    SUM(distance_meters) / 1609.34 as total_miles,
                    COUNT(*) as activity_count,
                    SUM(moving_time_seconds) as total_time_seconds
                FROM strava_activities
                WHERE type = ?
                GROUP BY strftime('%Y-%m', start_date)
                ORDER BY month DESC
                LIMIT ?
                """,
                (activity_type, months)
            )
            return [
                {
                    "month": row["month"],
                    "total_miles": round(row["total_miles"], 1),
                    "activity_count": row["activity_count"],
                    "total_time_seconds": row["total_time_seconds"]
                }
                for row in cursor.fetchall()
            ]

    def get_all_time_stats(self, activity_type: str = "Run") -> Dict[str, Any]:
        """Get all-time statistics for an activity type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_activities,
                    SUM(distance_meters) / 1609.34 as total_miles,
                    SUM(moving_time_seconds) as total_time_seconds,
                    AVG(distance_meters) / 1609.34 as avg_miles,
                    MAX(distance_meters) / 1609.34 as longest_miles,
                    MIN(start_date) as first_activity,
                    MAX(start_date) as last_activity
                FROM strava_activities
                WHERE type = ?
                """,
                (activity_type,)
            )
            row = cursor.fetchone()

            if row and row["total_activities"] > 0:
                return {
                    "total_activities": row["total_activities"],
                    "total_miles": round(row["total_miles"], 1),
                    "total_time_seconds": row["total_time_seconds"],
                    "avg_miles": round(row["avg_miles"], 1),
                    "longest_miles": round(row["longest_miles"], 1),
                    "first_activity": row["first_activity"],
                    "last_activity": row["last_activity"]
                }
            return {
                "total_activities": 0,
                "total_miles": 0,
                "total_time_seconds": 0,
                "avg_miles": 0,
                "longest_miles": 0,
                "first_activity": None,
                "last_activity": None
            }

    def get_activity_count(self) -> int:
        """Get total number of stored activities."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM strava_activities")
            return cursor.fetchone()["count"]


# Global instance
_db_instance: Optional[StravaDatabase] = None


def get_strava_db(db_path: str = "strava.db") -> StravaDatabase:
    """Get or create the global Strava database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = StravaDatabase(db_path)
    return _db_instance
