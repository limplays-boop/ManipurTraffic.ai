from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RiskLevel = Literal["unknown", "low", "moderate", "high", "critical"]
RiskDataStatus = Literal["available", "empty"]


class RiskFactorInput(BaseModel):
    """Observed inputs; nullable values mean that the factor was not measured."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    accident_count: int | None = Field(default=None, ge=0)
    accident_window_days: int | None = Field(default=None, ge=1, le=3650)
    traffic_volume: int | None = Field(default=None, ge=0)
    traffic_delay_seconds: int | None = Field(default=None, ge=0)
    weather_factor: float | None = Field(default=None, ge=0, le=100)
    road_factor: float | None = Field(default=None, ge=0, le=100)
    time_factor: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_accident_window(self):
        if self.accident_count is not None and self.accident_window_days is None:
            raise ValueError("accident_window_days is required when accident_count is provided")
        if self.accident_count is None and self.accident_window_days is not None:
            raise ValueError("accident_window_days requires accident_count")
        return self


class RiskObservationCreate(BaseModel):
    """A source-attributed observation submitted for risk analysis."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    location_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime
    source: str = Field(min_length=1, max_length=200)
    factors: RiskFactorInput

    @field_validator("location_id", "name", "source")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_timezone_and_normalize(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def require_measured_factor(self):
        if not any(
            value is not None
            for name, value in self.factors.model_dump().items()
            if name != "accident_window_days"
        ):
            raise ValueError("At least one measured risk factor is required")
        return self


class RiskObservationBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[RiskObservationCreate] = Field(min_length=1, max_length=1000)


class RiskPoint(BaseModel):
    """One scored observation with both raw inputs and normalized contributions."""

    observation_id: str
    location_id: str
    name: str
    latitude: float
    longitude: float
    risk_score: float | None
    risk_level: RiskLevel
    accident_count: int | None
    accident_window_days: int | None
    traffic_volume: int | None
    traffic_delay_seconds: int | None
    weather_factor: float | None
    road_factor: float | None
    time_factor: float | None
    factor_scores: dict[str, float]
    factors_used: list[str]
    data_source: str
    timestamp: str
    model_version: str


class RiskMapPoint(BaseModel):
    location_id: str
    name: str
    latitude: float
    longitude: float
    risk_score: float | None
    risk_level: RiskLevel
    observation_count: int
    scored_observation_count: int
    high_risk_observation_count: int
    source_count: int
    first_observed_at: datetime
    last_observed_at: datetime


class RiskMapResponse(BaseModel):
    status: RiskDataStatus
    city: str
    aggregation: str
    model_version: str
    observation_count: int
    locations: list[RiskMapPoint]
    generated_at: datetime


class RiskPattern(BaseModel):
    location_id: str
    name: str
    hour_of_day: int
    day_of_week: int
    observation_count: int
    high_risk_observation_count: int
    high_risk_days: int
    average_risk_score: float
    risk_level: RiskLevel


class RiskPatternsResponse(BaseModel):
    status: RiskDataStatus
    timezone: str
    minimum_occurrences: int
    risk_threshold: float
    patterns: list[RiskPattern]
    generated_at: datetime


class RiskObservationListResponse(BaseModel):
    status: RiskDataStatus
    total_count: int
    observations: list[RiskPoint]


class RiskObservationBatchResponse(BaseModel):
    created_count: int
    observations: list[RiskPoint]
