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
        """Fetch 5-day forecast (for today's high/low)."""
        resp = await client.get(
            f"{self.BASE_URL}/forecast",
            params={
                "q": location,
                "appid": api_key,
                "units": units,
                "cnt": 8,  # ~24 hours of 3-hour forecasts
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

        # Calculate today's high/low from forecast
        temps = []
        for item in forecast.get("list", []):
            temps.append(item.get("main", {}).get("temp", 0))

        if temps:
            high = round(max(temps))
            low = round(min(temps))
        else:
            high = current_temp
            low = current_temp

        # Temperature unit symbol
        temp_unit = "F" if units == "imperial" else "C"
        wind_unit = "mph" if units == "imperial" else "m/s"

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
        }
