from pydantic import BaseModel, Field
from typing import Literal


TrafficStatus = Literal[
    "unknown",
    "clear",
    "moderate",
    "heavy",
    "critical",
]


class TrafficPoint(BaseModel):
    name: str
    latitude: float
    longitude: float

    status: TrafficStatus

    average_speed_kmh: float | None = None
    traffic_delay_seconds: int | None = None

    risk_score: float | None = None

    data_source: str
    timestamp: str


class TrafficRouteRequest(BaseModel):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)
