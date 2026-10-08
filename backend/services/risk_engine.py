from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from models.risk import RiskPoint


@dataclass(frozen=True)
class RiskFactors:
    accident_count: float | None = None
    accident_window_days: float | None = None
    traffic_volume: float | None = None
    traffic_delay_seconds: float | None = None
    weather_factor: float | None = None
    road_factor: float | None = None
    time_factor: float | None = None


class RiskEngine:
    """Explainable baseline score built only from supplied observations."""

    MODEL_VERSION = "transparent-baseline-v1"

    def calculate_factor_scores(self, factors: RiskFactors) -> dict[str, float]:
        scores: dict[str, float] = {}

        if factors.accident_count is not None and factors.accident_window_days:
            accidents_per_30_days = (
                factors.accident_count * 30 / factors.accident_window_days
            )
            scores["accident_history"] = round(
                min(accidents_per_30_days * 5, 100), 2
            )

        if factors.traffic_volume is not None:
            scores["traffic_volume"] = round(
                min(factors.traffic_volume / 10, 100), 2
            )

        if factors.traffic_delay_seconds is not None:
            scores["traffic_delay"] = round(
                min(factors.traffic_delay_seconds / 3, 100), 2
            )

        if factors.weather_factor is not None:
            scores["weather"] = round(factors.weather_factor, 2)

        if factors.road_factor is not None:
            scores["road_characteristics"] = round(factors.road_factor, 2)

        if factors.time_factor is not None:
            scores["time_conditions"] = round(factors.time_factor, 2)

        return scores

    def calculate_score(self, factors: RiskFactors) -> float | None:
        scores = list(self.calculate_factor_scores(factors).values())
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)

    def get_risk_level(self, score: float | None) -> str:
        if score is None:
            return "unknown"
        if score >= 80:
            return "critical"
        if score >= 60:
            return "high"
        if score >= 30:
            return "moderate"
        return "low"

    def create_risk_point(
        self,
        name: str,
        latitude: float,
        longitude: float,
        factors: RiskFactors,
        data_source: str,
        timestamp: datetime | str,
        *,
        location_id: str | None = None,
        observation_id: str | None = None,
    ) -> RiskPoint:
        factor_scores = self.calculate_factor_scores(factors)
        score = (
            round(sum(factor_scores.values()) / len(factor_scores), 2)
            if factor_scores
            else None
        )

        return RiskPoint(
            observation_id=observation_id or str(uuid4()),
            location_id=location_id or name,
            name=name,
            latitude=latitude,
            longitude=longitude,
            risk_score=score,
            risk_level=self.get_risk_level(score),
            accident_count=(
                int(factors.accident_count)
                if factors.accident_count is not None
                else None
            ),
            accident_window_days=(
                int(factors.accident_window_days)
                if factors.accident_window_days is not None
                else None
            ),
            traffic_volume=(
                int(factors.traffic_volume)
                if factors.traffic_volume is not None
                else None
            ),
            traffic_delay_seconds=(
                int(factors.traffic_delay_seconds)
                if factors.traffic_delay_seconds is not None
                else None
            ),
            weather_factor=factors.weather_factor,
            road_factor=factors.road_factor,
            time_factor=factors.time_factor,
            factor_scores=factor_scores,
            factors_used=list(factor_scores),
            data_source=data_source,
            timestamp=(
                timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else timestamp
            ),
            model_version=self.MODEL_VERSION,
        )
