from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HistoricalAccidentYear(BaseModel):
    state: str
    year: int = Field(ge=1900, le=2200)
    accidents: int = Field(ge=0)
    fatalities: int = Field(ge=0)
    geography_level: Literal["state_annual"]
    source_report: str
    source_table: str
    source_url: str


class HistoricalBlackspotRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: int
    state: str
    district: str
    police_station: str
    highway: str
    location_name: str
    chainage_start_reported: str
    chainage_end_reported: str
    accidents_by_year: dict[int, int]
    accidents_total_reported: int = Field(ge=0)
    accidents_total_from_years: int = Field(ge=0)
    fatalities_by_year: dict[int, int]
    fatalities_total_reported: int = Field(ge=0)
    fatalities_total_from_years: int = Field(ge=0)
    totals_match_annual_values: bool
    coordinates_status: Literal["not_geocoded"]
    source_report: str
    source_table: str
    source_url: str


class HistoricalAccidentHistoryResponse(BaseModel):
    status: Literal["partial"]
    state: Literal["Manipur"]
    annual_state_totals: list[HistoricalAccidentYear]
    reported_nh_high_accident_locations: list[HistoricalBlackspotRecord]
    event_level_records_available: Literal[False]
    training_ready: Literal[False]
    note: str


class PublicAccidentDemoIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demo_id: str
    occurred_at_local: str
    district: str
    location_description: str
    road_reference: str | None
    event_type_reported: str
    vehicles_reported: list[str]
    injury_outcome_reported: str
    fatality_outcome_reported: str
    weather_reported: str | None
    traffic_reported: str | None
    latitude: float | None
    longitude: float | None
    coordinates_status: Literal["not_geocoded"]
    report_nature: str
    source_reference: str
    training_eligible: Literal[False]
    limitations: str


class PublicAccidentDemoPattern(BaseModel):
    name: str
    matched_reports: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    evidence_rule: str


class PublicAccidentDemoAnalysis(BaseModel):
    model_name: str
    method: Literal["rule_based_pattern_scan"]
    sample_size: int = Field(ge=0)
    patterns: list[PublicAccidentDemoPattern]
    risk_score_available: Literal[False]
    note: str


class PublicAccidentDemoResponse(BaseModel):
    status: Literal["demo_only"]
    state: Literal["Manipur"]
    incidents: list[PublicAccidentDemoIncident]
    analysis: PublicAccidentDemoAnalysis
    training_ready: Literal[False]
    note: str
