from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WeatherStatus = Literal["available", "unavailable"]


class WeatherCurrent(BaseModel):
    """Timestamped weather-model conditions for one requested map location."""

    model_config = ConfigDict(allow_inf_nan=False)

    status: WeatherStatus
    provider: Literal["Open-Meteo"] = "Open-Meteo"
    data_basis: Literal["weather_model_estimate"] = "weather_model_estimate"
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str | None = None
    valid_at: datetime | None = None
    fetched_at: datetime
    temperature_c: float | None = None
    relative_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    precipitation_mm: float | None = Field(default=None, ge=0)
    rain_mm: float | None = Field(default=None, ge=0)
    showers_mm: float | None = Field(default=None, ge=0)
    weather_code: int | None = Field(default=None, ge=0)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
    wind_gusts_kmh: float | None = Field(default=None, ge=0)
    message: str | None = None
