from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TrafficRiskLevel = Literal["unknown", "low", "moderate", "high", "critical"]


class TrafficRiskFactor(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: str
    score: float = Field(ge=0, le=100)
    observed_value: str
    data_source: str


class TrafficRiskAssessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    status: Literal["available", "partial", "unavailable"]
    model_name: Literal["Manipur Live Traffic Risk Index"]
    model_version: Literal["live-traffic-risk-v1"]
    risk_score: float | None = Field(default=None, ge=0, le=100)
    risk_level: TrafficRiskLevel
    factors: list[TrafficRiskFactor]
    assessed_at: datetime
    method_summary: str
    limitation: str
