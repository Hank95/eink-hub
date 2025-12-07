from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

print("CLIENT_ID:", CLIENT_ID)
print("CLIENT_SECRET present:", bool(CLIENT_SECRET))
print("REFRESH_TOKEN present:", bool(REFRESH_TOKEN))

TOKEN_CACHE_PATH = PROJECT_ROOT / "strava_token.json"


class StravaAuthError(Exception):
    pass


def _refresh_access_token() -> Dict[str, Any]:
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        raise StravaAuthError("Missing STRAVA_CLIENT_ID/SECRET/REFRESH_TOKEN")

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
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
                "expires_at": data["expires_at"],  # epoch seconds
            }
        )
    )

    return data


def _get_access_token() -> str:
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

    # Otherwise refresh
    data = _refresh_access_token()
    return data["access_token"]


def fetch_recent_activities(per_page: int = 50) -> List[Dict[str, Any]]:
    token = _get_access_token()
    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": per_page},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def compute_week_summary(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a summary for the current week:
      - week_total_miles: float
      - weekly_miles: [Mon..Sun] list of floats
      - recent_runs: list of dicts with label, miles, pace
    Only counts "Run" type activities.
    """
    import datetime as dt

    now = dt.datetime.now().astimezone()
    # Monday of this week
    start_of_week = now - dt.timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    weekly_miles = [0.0] * 7
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
                "miles": miles,
                "pace": pace_str,
                "start": start.isoformat(timespec="minutes"),
            }
        )

    week_total = round(sum(weekly_miles), 1)
    recent_runs = sorted(recent_runs, key=lambda r: r["start"], reverse=True)[:5]

    return {
        "week_total_miles": week_total,
        "weekly_miles": weekly_miles,
        "recent_runs": recent_runs,
    }

def get_week_summary() -> Dict[str, Any]:
    try:
        acts = fetch_recent_activities()
        return compute_week_summary(acts)
    except Exception:
        return {}

if __name__ == "__main__":
    # Quick manual test:
    print(json.dumps(get_week_summary(), indent=2))
