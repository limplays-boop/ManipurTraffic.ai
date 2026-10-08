from collections import defaultdict
from datetime import datetime, timedelta, timezone

from models.risk import RiskMapPoint, RiskPattern, RiskPoint
from services.risk_engine import RiskEngine


class RiskAnalytics:
    """Aggregates persisted observations into map and recurrence views."""

    TIMEZONE = timezone(timedelta(hours=5, minutes=30), "Asia/Kolkata")

    def __init__(self, risk_engine: RiskEngine):
        self.risk_engine = risk_engine

    @staticmethod
    def _timestamp(point: RiskPoint) -> datetime:
        timestamp = datetime.fromisoformat(point.timestamp.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp

    def build_map(self, observations: list[RiskPoint]) -> list[RiskMapPoint]:
        grouped: dict[str, list[RiskPoint]] = defaultdict(list)
        for observation in observations:
            grouped[observation.location_id].append(observation)

        locations: list[RiskMapPoint] = []
        for location_id, points in grouped.items():
            latest = max(points, key=self._timestamp)
            scored_points = [
                point for point in points if point.risk_score is not None
            ]
            scores = [
                point.risk_score
                for point in scored_points
                if point.risk_score is not None
            ]
            average_score = (
                round(sum(scores) / len(scores), 2)
                if scores
                else None
            )

            locations.append(
                RiskMapPoint(
                    location_id=location_id,
                    name=latest.name,
                    latitude=latest.latitude,
                    longitude=latest.longitude,
                    risk_score=average_score,
                    risk_level=self.risk_engine.get_risk_level(average_score),
                    observation_count=len(points),
                    scored_observation_count=len(scored_points),
                    high_risk_observation_count=sum(
                        point.risk_score is not None and point.risk_score >= 60
                        for point in scored_points
                    ),
                    source_count=len({point.data_source for point in points}),
                    first_observed_at=min(map(self._timestamp, points)),
                    last_observed_at=max(map(self._timestamp, points)),
                )
            )

        return sorted(
            locations,
            key=lambda point: (
                point.risk_score is None,
                -(point.risk_score or 0),
                point.name.casefold(),
            ),
        )

    def find_recurring_patterns(
        self,
        observations: list[RiskPoint],
        minimum_occurrences: int = 2,
        risk_threshold: float = 60,
    ) -> list[RiskPattern]:
        grouped: dict[tuple[str, int, int], list[RiskPoint]] = defaultdict(list)
        for observation in observations:
            if observation.risk_score is None:
                continue
            local_time = self._timestamp(observation).astimezone(self.TIMEZONE)
            key = (
                observation.location_id,
                local_time.weekday(),
                local_time.hour,
            )
            grouped[key].append(observation)

        patterns: list[RiskPattern] = []
        for (location_id, day_of_week, hour_of_day), points in grouped.items():
            high_risk_points = [
                point
                for point in points
                if point.risk_score is not None
                and point.risk_score >= risk_threshold
            ]
            high_risk_days = {
                self._timestamp(point).astimezone(self.TIMEZONE).date()
                for point in high_risk_points
            }
            if len(high_risk_days) < minimum_occurrences:
                continue

            scores = [
                point.risk_score
                for point in points
                if point.risk_score is not None
            ]
            average_score = round(sum(scores) / len(scores), 2)
            latest = max(points, key=self._timestamp)
            patterns.append(
                RiskPattern(
                    location_id=location_id,
                    name=latest.name,
                    hour_of_day=hour_of_day,
                    day_of_week=day_of_week,
                    observation_count=len(points),
                    high_risk_observation_count=len(high_risk_points),
                    high_risk_days=len(high_risk_days),
                    average_risk_score=average_score,
                    risk_level=self.risk_engine.get_risk_level(average_score),
                )
            )

        return sorted(
            patterns,
            key=lambda pattern: (
                -pattern.high_risk_days,
                -pattern.high_risk_observation_count,
                -pattern.average_risk_score,
                pattern.name.casefold(),
                pattern.day_of_week,
                pattern.hour_of_day,
            ),
        )
