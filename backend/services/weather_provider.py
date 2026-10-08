from datetime import datetime, timedelta, timezone

import httpx

from models.weather import WeatherCurrent


class OpenMeteoWeatherProvider:
    """Fetch current model-based weather conditions without an API key."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    CURRENT_FIELDS = (
        "temperature_2m,relative_humidity_2m,precipitation,rain,showers,"
        "weather_code,wind_speed_10m,wind_gusts_10m"
    )

    def get_current(self, latitude: float, longitude: float) -> WeatherCurrent:
        try:
            response = httpx.get(
                self.BASE_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": self.CURRENT_FIELDS,
                    "timezone": "auto",
                    "temperature_unit": "celsius",
                    "wind_speed_unit": "kmh",
                    "precipitation_unit": "mm",
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            current = payload["current"]
            timezone_name = payload.get("timezone", "UTC")
            model_time = datetime.fromisoformat(current["time"])

            if model_time.tzinfo is None:
                offset_seconds = int(payload.get("utc_offset_seconds", 0))
                model_time = model_time.replace(
                    tzinfo=timezone(timedelta(seconds=offset_seconds))
                )

            return WeatherCurrent(
                status="available",
                latitude=latitude,
                longitude=longitude,
                timezone=timezone_name,
                valid_at=model_time,
                fetched_at=datetime.now(timezone.utc),
                temperature_c=current.get("temperature_2m"),
                relative_humidity_pct=current.get("relative_humidity_2m"),
                precipitation_mm=current.get("precipitation"),
                rain_mm=current.get("rain"),
                showers_mm=current.get("showers"),
                weather_code=current.get("weather_code"),
                wind_speed_kmh=current.get("wind_speed_10m"),
                wind_gusts_kmh=current.get("wind_gusts_10m"),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                "Current weather data could not be retrieved from Open-Meteo."
            ) from error
