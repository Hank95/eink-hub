"""OpenWeatherMap weather provider."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict

import httpx

from ..core.exceptions import ProviderError
from ..core.logging import get_logger
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.weather")

# Weather condition icons (for potential future use)
WEATHER_ICONS = {
    "Clear": "sunny",
    "Clouds": "cloudy",
    "Rain": "rainy",
    "Drizzle": "rainy",
    "Thunderstorm": "stormy",
    "Snow": "snowy",
    "Mist": "foggy",
    "Fog": "foggy",
    "Haze": "hazy",
}


@ProviderRegistry.register("weather")
class WeatherProvider(BaseProvider):
    """
    Weather data provider using OpenWeatherMap API.

    Fetches:
    - Current temperature, conditions
    - Today's high/low
    - Humidity, wind

    Required credentials:
    - api_key: OpenWeatherMap API key

    Options:
    - location: "City,Country" (e.g., "San Francisco,US")
    - units: "imperial" | "metric" (default: imperial)
    """

    name = "weather"
    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def _validate_config(self) -> None:
        """Validate weather provider config."""
        self._require_credential("api_key")
        self._require_option("location")

    async def fetch(self) -> ProviderData:
        """Fetch current weather and forecast."""
        try:
            api_key = self.credentials["api_key"]
            location = self.options["location"]
            units = self.options.get("units", "imperial")

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fetch current weather
                current = await self._fetch_current(client, api_key, location, units)

                # Fetch forecast for high/low
                forecast = await self._fetch_forecast(client, api_key, location, units)

            data = self._build_weather_data(current, forecast, units)

            logger.info(
                f"Fetched weather: {data['current_temp']}° {data['condition']}"
            )

            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data=data,
                ttl_seconds=1800,  # 30 minutes
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Weather API error: {e.response.status_code}")
            raise ProviderError(self.name, f"API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            raise ProviderError(self.name, str(e))

    def get_default_refresh_interval(self) -> int:
        return 30

    async def _fetch_current(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        location: str,
        units: str,
    ) -> Dict[str, Any]:
        """Fetch current weather conditions."""
        resp = await client.get(
            f"{self.BASE_URL}/weather",
            params={
                "q": location,
                "appid": api_key,
                "units": units,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def _fetch_forecast(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        location: str,
        units: str,
    ) -> Dict[str, Any]:
        """Fetch 5-day forecast (3-hour intervals)."""
        resp = await client.get(
            f"{self.BASE_URL}/forecast",
            params={
                "q": location,
                "appid": api_key,
                "units": units,
                "cnt": 40,  # 5 days of 3-hour forecasts
            },
        )
        resp.raise_for_status()
        return resp.json()

    def _build_weather_data(
        self,
        current: Dict[str, Any],
        forecast: Dict[str, Any],
        units: str,
    ) -> Dict[str, Any]:
        """Build standardized weather data from API responses."""
        # Current conditions
        main = current.get("main", {})
        weather = current.get("weather", [{}])[0]
        wind = current.get("wind", {})

        current_temp = round(main.get("temp", 0))
        feels_like = round(main.get("feels_like", 0))
        humidity = main.get("humidity", 0)
        condition = weather.get("main", "Unknown")
        description = weather.get("description", "").title()
        wind_speed = round(wind.get("speed", 0))

        # Temperature unit symbol
        temp_unit = "F" if units == "imperial" else "C"
        wind_unit = "mph" if units == "imperial" else "m/s"

        # Process forecast data
        forecast_list = forecast.get("list", [])

        # Hourly forecast (next 24 hours, 3-hour intervals)
        hourly = []
        for item in forecast_list[:8]:
            item_weather = item.get("weather", [{}])[0]
            hourly.append({
                "time": dt.datetime.fromtimestamp(item.get("dt", 0)).strftime("%I%p").lstrip("0").lower(),
                "temp": round(item.get("main", {}).get("temp", 0)),
                "condition": item_weather.get("main", "Unknown"),
                "icon": WEATHER_ICONS.get(item_weather.get("main", ""), "unknown"),
                "pop": round(item.get("pop", 0) * 100),  # Probability of precipitation
            })

        # Daily forecast (aggregate by day)
        daily_data: Dict[str, Dict] = {}
        for item in forecast_list:
            item_dt = dt.datetime.fromtimestamp(item.get("dt", 0))
            day_key = item_dt.strftime("%Y-%m-%d")
            item_temp = item.get("main", {}).get("temp", 0)
            item_weather = item.get("weather", [{}])[0]
            item_pop = item.get("pop", 0)

            if day_key not in daily_data:
                daily_data[day_key] = {
                    "date": item_dt,
                    "day_name": item_dt.strftime("%a"),
                    "temps": [],
                    "conditions": [],
                    "pops": [],
                }
            daily_data[day_key]["temps"].append(item_temp)
            daily_data[day_key]["conditions"].append(item_weather.get("main", "Unknown"))
            daily_data[day_key]["pops"].append(item_pop)

        # Build daily forecast list
        daily = []
        for day_key in sorted(daily_data.keys())[:5]:
            day = daily_data[day_key]
            # Most common condition for the day
            conditions = day["conditions"]
            most_common = max(set(conditions), key=conditions.count)
            daily.append({
                "day_name": day["day_name"],
                "high": round(max(day["temps"])),
                "low": round(min(day["temps"])),
                "condition": most_common,
                "icon": WEATHER_ICONS.get(most_common, "unknown"),
                "pop": round(max(day["pops"]) * 100),
            })

        # Today's high/low from first day of forecast
        if daily:
            high = daily[0]["high"]
            low = daily[0]["low"]
        else:
            high = current_temp
            low = current_temp

        return {
            "current_temp": current_temp,
            "feels_like": feels_like,
            "high": high,
            "low": low,
            "humidity": humidity,
            "condition": condition,
            "description": description,
            "wind_speed": wind_speed,
            "temp_unit": temp_unit,
            "wind_unit": wind_unit,
            "icon": WEATHER_ICONS.get(condition, "unknown"),
            "location": current.get("name", self.options["location"]),
            "hourly": hourly,
            "daily": daily,
        }
