from datetime import datetime, timezone

from models.traffic_risk import TrafficRiskAssessment, TrafficRiskFactor
from models.weather import WeatherCurrent


class TrafficRiskEngine:
    """Scores current road conditions from measured live traffic and weather."""

    MODEL_NAME = "Manipur Live Traffic Risk Index"
    MODEL_VERSION = "live-traffic-risk-v1"
    METHOD_SUMMARY = (
        "Traffic pressure averages speed reduction (70%) and extra travel-time "
        "ratio (30%) when both are measured. The current WMO weather-code severity "
        "band can add up to 35 points; it never lowers the traffic score. A reported "
        "road closure is critical. Risk bands: low <30, moderate 30–59, high 60–79, "
        "critical ≥80."
    )
    LIMITATION = (
        "This is a live operational conditions index, not an accident probability. "
        "Its transparent bands have not been calibrated against Manipur crash "
        "outcomes or traffic exposure data."
    )
    WEATHER_RISK = {
        0: (0, "clear"),
        1: (5, "mainly clear"),
        2: (10, "partly cloudy"),
        3: (15, "overcast"),
        45: (55, "fog"),
        48: (65, "depositing rime fog"),
        51: (25, "light drizzle"),
        53: (35, "drizzle"),
        55: (45, "heavy drizzle"),
        56: (50, "freezing drizzle"),
        57: (60, "dense freezing drizzle"),
        61: (45, "light rain"),
        63: (60, "rain"),
        65: (75, "heavy rain"),
        66: (65, "freezing rain"),
        67: (80, "heavy freezing rain"),
        71: (65, "light snow"),
        73: (80, "snow"),
        75: (95, "heavy snow"),
        77: (75, "snow grains"),
        80: (50, "light rain showers"),
        81: (65, "rain showers"),
        82: (80, "heavy rain showers"),
        85: (80, "light snow showers"),
        86: (95, "heavy snow showers"),
        95: (90, "thunderstorm"),
        96: (95, "thunderstorm with hail"),
        97: (100, "heavy thunderstorm"),
        99: (100, "severe thunderstorm with hail"),
    }

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    @staticmethod
    def _risk_level(score: float | None) -> str:
        if score is None:
            return "unknown"
        if score >= 80:
            return "critical"
        if score >= 60:
            return "high"
        if score >= 30:
            return "moderate"
        return "low"

    def assess(
        self,
        traffic: dict,
        weather: WeatherCurrent | None,
    ) -> TrafficRiskAssessment:
        factors: list[TrafficRiskFactor] = []
        traffic_parts: list[tuple[float, float]] = []
        current_speed = self._number(traffic.get("current_speed_kmh"))
        free_flow_speed = self._number(traffic.get("free_flow_speed_kmh"))
        if current_speed is not None and free_flow_speed is not None and free_flow_speed > 0:
            speed_reduction = max(
                0.0,
                min(100.0, (1 - current_speed / free_flow_speed) * 100),
            )
            traffic_parts.append((speed_reduction, 0.7))
            factors.append(
                TrafficRiskFactor(
                    name="Speed reduction",
                    score=round(speed_reduction, 1),
                    observed_value=(
                        f"{current_speed:.0f} km/h current vs "
                        f"{free_flow_speed:.0f} km/h free-flow"
                    ),
                    data_source="TomTom Traffic Flow Segment Data",
                )
            )

        current_time = self._number(traffic.get("current_travel_time_seconds"))
        free_flow_time = self._number(traffic.get("free_flow_travel_time_seconds"))
        if current_time is not None and free_flow_time is not None and free_flow_time > 0:
            delay_ratio = max(0.0, (current_time - free_flow_time) / free_flow_time)
            delay_score = min(100.0, delay_ratio / 0.5 * 100)
            traffic_parts.append((delay_score, 0.3))
            factors.append(
                TrafficRiskFactor(
                    name="Extra travel time",
                    score=round(delay_score, 1),
                    observed_value=f"{delay_ratio * 100:.1f}% above free-flow time",
                    data_source="TomTom Traffic Flow Segment Data",
                )
            )

        traffic_score = None
        if traffic_parts:
            total_weight = sum(weight for _, weight in traffic_parts)
            traffic_score = sum(score * weight for score, weight in traffic_parts) / total_weight

        closed = traffic.get("road_closure") is True
        if closed:
            factors.append(
                TrafficRiskFactor(
                    name="Road closure",
                    score=100,
                    observed_value="TomTom reports the road segment closed",
                    data_source="TomTom Traffic Flow Segment Data",
                )
            )

        weather_score: float | None = None
        weather_description: str | None = None
        if weather is not None and weather.status == "available" and weather.weather_code is not None:
            weather_entry = self.WEATHER_RISK.get(weather.weather_code)
            if weather_entry is not None:
                weather_score, weather_description = weather_entry
                factors.append(
                    TrafficRiskFactor(
                        name="Weather conditions",
                        score=weather_score,
                        observed_value=(
                            f"{weather_description} (Open-Meteo weather code "
                            f"{weather.weather_code})"
                        ),
                        data_source="Open-Meteo weather-model estimate",
                    )
                )

        if closed:
            score = 100.0
        elif traffic_score is None:
            score = None
        elif weather_score is None:
            score = traffic_score
        else:
            score = min(100.0, traffic_score + weather_score * 0.35)

        if score is not None:
            score = round(score, 1)
        if score is None:
            status = "unavailable"
        elif weather_score is None or not factors:
            status = "partial"
        else:
            status = "available"

        return TrafficRiskAssessment(
            status=status,
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            risk_score=score,
            risk_level=self._risk_level(score),
            factors=factors,
            assessed_at=datetime.now(timezone.utc),
            method_summary=self.METHOD_SUMMARY,
            limitation=self.LIMITATION,
        )
