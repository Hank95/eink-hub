"""Strava activity provider."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from ..core.exceptions import ConfigurationError, ProviderError
from ..core.logging import get_logger
from ..core.strava_database import get_strava_db
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.strava")

TOKEN_CACHE_PATH = Path("strava_token.json")


@ProviderRegistry.register("strava")
class StravaProvider(BaseProvider):
    """
    Strava activity provider.

    Fetches:
    - Weekly mileage breakdown (Mon-Sun)
    - Recent runs with distance/pace
    - Week total

    Required credentials:
    - client_id
    - client_secret
    - refresh_token
    """

    name = "strava"

    def _validate_config(self) -> None:
        """Validate Strava credentials are present."""
        required = ["client_id", "client_secret", "refresh_token"]
        missing = [k for k in required if not self.credentials.get(k)]
        if missing:
            raise ConfigurationError(f"Strava missing credentials: {missing}")

    async def fetch(self) -> ProviderData:
        """Fetch activities and compute weekly summary."""
        try:
            token = self._get_access_token()
            activities = self._fetch_activities(token)

            # Save activities to database for historical tracking
            db = get_strava_db()
            result = db.upsert_activities(activities)
            if result["inserted"] > 0:
                logger.info(f"Saved {result['inserted']} new activities to database")

            summary = self._compute_week_summary(activities)

            logger.info(
                f"Fetched Strava data: {summary.get('week_total_miles', 0):.1f} mi this week"
            )

            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data=summary,
                ttl_seconds=900,  # 15 minutes
            )
        except Exception as e:
            logger.error(f"Strava fetch failed: {e}")
            raise ProviderError(self.name, str(e))

    def get_default_refresh_interval(self) -> int:
        return 15

    def _refresh_access_token(self) -> Dict[str, Any]:
        """Refresh the OAuth access token."""
        resp = requests.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": self.credentials["refresh_token"],
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Cache access token + expiry
        TOKEN_CACHE_PATH.write_text(
            json.dumps(
                {
                    "access_token": data["access_token"],
                    "expires_at": data["expires_at"],
                }
            )
        )

        logger.debug("Refreshed Strava access token")
        return data

    def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        import time

        # Try cached token
        if TOKEN_CACHE_PATH.exists():
            try:
                cache = json.loads(TOKEN_CACHE_PATH.read_text())
                access_token = cache.get("access_token")
                expires_at = cache.get("expires_at", 0)
                if access_token and time.time() < expires_at - 60:
                    return access_token
            except Exception:
                pass

        # Refresh token
        data = self._refresh_access_token()
        return data["access_token"]

    def _fetch_activities(self, token: str, per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent activities from Strava API."""
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"per_page": per_page},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _compute_week_summary(
        self, activities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a summary for the current week.

        Returns:
            Dict with:
            - week_total_miles: float
            - weekly_miles: [Mon..Sun] list of floats
            - recent_runs: list of dicts with label, miles, pace
        """
        now = dt.datetime.now().astimezone()
        # Monday of this week
        start_of_week = now - dt.timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_miles: List[float] = [0.0] * 7
        recent_runs: List[Dict[str, Any]] = []

        for act in activities:
            if act.get("type") != "Run":
                continue

            start_date_str = act.get("start_date")
            if not start_date_str:
                continue

            start = dt.datetime.fromisoformat(
                start_date_str.replace("Z", "+00:00")
            ).astimezone()

            dist_m = act.get("distance", 0.0) or 0.0
            miles = dist_m / 1609.34

            moving_time = act.get("moving_time", 0) or 0
            if miles > 0 and moving_time > 0:
                pace_sec_per_mile = moving_time / miles
                pace_min = int(pace_sec_per_mile // 60)
                pace_sec = int(round(pace_sec_per_mile % 60))
                pace_str = f"{pace_min}:{pace_sec:02d} /mi"
            else:
                pace_str = ""

            # Count in this week
            if start >= start_of_week:
                day_index = start.weekday()  # Monday = 0
                if 0 <= day_index < 7:
                    weekly_miles[day_index] += miles

            recent_runs.append(
                {
                    "label": act.get("name", "Run"),
                    "miles": round(miles, 1),
                    "pace": pace_str,
                    "start": start.isoformat(timespec="minutes"),
                }
            )

        week_total = round(sum(weekly_miles), 1)
        recent_runs = sorted(recent_runs, key=lambda r: r["start"], reverse=True)[:5]

        return {
            "week_total_miles": week_total,
            "weekly_miles": [round(m, 1) for m in weekly_miles],
            "recent_runs": recent_runs,
        }
