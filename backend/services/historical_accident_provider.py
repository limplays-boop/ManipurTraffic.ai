import csv
from pathlib import Path

from models.accident_history import (
    HistoricalAccidentHistoryResponse,
    HistoricalAccidentYear,
    HistoricalBlackspotRecord,
    PublicAccidentDemoAnalysis,
    PublicAccidentDemoIncident,
    PublicAccidentDemoPattern,
    PublicAccidentDemoResponse,
)


class HistoricalAccidentProvider:
    """Loads published, source-attributed Manipur accident aggregates."""

    DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "historical"
    ANNUAL_TOTALS_FILE = "morth_manipur_state_accidents_2019_2023.csv"
    BLACKSPOTS_FILE = "morth_manipur_nh_blackspots_2016_2018.csv"
    DEMO_INCIDENTS_FILE = "manipur_public_demo_incidents.csv"

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))

    def get_history(self) -> HistoricalAccidentHistoryResponse:
        annual_rows = self._read_rows(self.DATA_DIR / self.ANNUAL_TOTALS_FILE)
        annual_totals = [
            HistoricalAccidentYear(
                state=row["state"],
                year=int(row["year"]),
                accidents=int(row["accidents"]),
                fatalities=int(row["fatalities"]),
                geography_level=row["geography_level"],
                source_report=row["source_report"],
                source_table=row["source_table"],
                source_url=row["source_url"],
            )
            for row in annual_rows
        ]

        blackspot_rows = self._read_rows(self.DATA_DIR / self.BLACKSPOTS_FILE)
        blackspots = []
        for row in blackspot_rows:
            accidents_by_year = {
                year: int(row[f"accidents_{year}"])
                for year in (2016, 2017, 2018)
            }
            fatalities_by_year = {
                year: int(row[f"fatalities_{year}"])
                for year in (2016, 2017, 2018)
            }
            blackspots.append(
                HistoricalBlackspotRecord(
                    source_record_id=int(row["source_record_id"]),
                    state=row["state"],
                    district=row["district"],
                    police_station=row["police_station"],
                    highway=row["highway"],
                    location_name=row["location_name"],
                    chainage_start_reported=row["chainage_start_reported"],
                    chainage_end_reported=row["chainage_end_reported"],
                    accidents_by_year=accidents_by_year,
                    accidents_total_reported=int(row["accidents_total_reported"]),
                    accidents_total_from_years=int(row["accidents_total_from_years"]),
                    fatalities_by_year=fatalities_by_year,
                    fatalities_total_reported=int(row["fatalities_total_reported"]),
                    fatalities_total_from_years=int(
                        row["fatalities_total_from_years"]
                    ),
                    totals_match_annual_values=(
                        row["total_matches_annual_values"].lower() == "true"
                    ),
                    coordinates_status="not_geocoded",
                    source_report=row["source_report"],
                    source_table=row["source_table"],
                    source_url=row["source_url"],
                )
            )

        return HistoricalAccidentHistoryResponse(
            status="partial",
            state="Manipur",
            annual_state_totals=annual_totals,
            reported_nh_high_accident_locations=blackspots,
            event_level_records_available=False,
            training_ready=False,
            note=(
                "Published historical aggregates are available. Location rows are "
                "not geocoded, and this data does not support a calibrated accident "
                "probability model."
            ),
        )

    def get_demo_incidents(self) -> PublicAccidentDemoResponse:
        rows = self._read_rows(self.DATA_DIR / self.DEMO_INCIDENTS_FILE)
        incidents = [
            PublicAccidentDemoIncident(
                **{
                    **{
                        key: value
                        for key, value in row.items()
                        if key != "source_url"
                    },
                    "vehicles_reported": [
                        value.strip()
                        for value in row["vehicles_reported"].split(";")
                        if value.strip()
                    ],
                    "latitude": float(row["latitude"])
                    if row["latitude"]
                    else None,
                    "longitude": float(row["longitude"])
                    if row["longitude"]
                    else None,
                    "training_eligible": row["training_eligible"].lower()
                    == "true",
                    "source_reference": row["report_nature"],
                }
            )
            for row in rows
        ]
        sample_size = len(incidents)
        demo_patterns = [
            (
                "Two-wheeler involvement",
                lambda incident: any(
                    any(
                        keyword in vehicle.casefold()
                        for keyword in ("motorcycle", "scooter", "activa", "two-wheeler")
                    )
                    for vehicle in incident.vehicles_reported
                ),
                "Vehicle descriptions mention a motorcycle, scooter, Activa, or two-wheeler.",
            ),
            (
                "Turning or crossing conflict described",
                lambda incident: any(
                    keyword in incident.event_type_reported.casefold()
                    for keyword in ("turn", "cross")
                ),
                "The report summary mentions a turn or crossing movement.",
            ),
            (
                "Serious injury described",
                lambda incident: any(
                    keyword in incident.injury_outcome_reported.casefold()
                    for keyword in ("severe", "grievous", "fatal", "died")
                ),
                "The report summary mentions a severe or grievous injury, or a death.",
            ),
        ]
        patterns = [
            PublicAccidentDemoPattern(
                name=name,
                matched_reports=sum(matches(incident) for incident in incidents),
                sample_size=sample_size,
                evidence_rule=evidence_rule,
            )
            for name, matches, evidence_rule in demo_patterns
            if sample_size and any(matches(incident) for incident in incidents)
        ]
        return PublicAccidentDemoResponse(
            status="demo_only",
            state="Manipur",
            incidents=incidents,
            analysis=PublicAccidentDemoAnalysis(
                model_name="TR-04 Public Report Pattern Demo",
                method="rule_based_pattern_scan",
                sample_size=sample_size,
                patterns=patterns,
                risk_score_available=False,
                note=(
                    "These keyword-based patterns describe only this small sourced "
                    "sample. They are not statewide rates, trained predictions, or "
                    "calibrated risk scores."
                ),
            ),
            training_ready=False,
            note=(
                "This demo scans publicly documented incident examples for "
                "reported patterns. It does not train a model or estimate "
                "calibrated accident probabilities."
            ),
        )
