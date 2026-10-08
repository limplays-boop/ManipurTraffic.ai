import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

from models.traffic import TrafficPoint


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class TrafficProvider:
    """
    Base interface for traffic data providers.
    """

    source_name = "Unknown"

    def get_traffic(self) -> list[TrafficPoint]:
        raise NotImplementedError

    def get_live_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> dict:
        raise RuntimeError("Live route geometry is unavailable from this provider.")

    def get_traffic_at_location(self, latitude: float, longitude: float) -> dict:
        raise RuntimeError("Point-level live traffic is unavailable from this provider.")


class MapplsTrafficProvider(TrafficProvider):
    """

    source_name = "Mappls"
    Mappls traffic data provider.

    This provider retrieves route ETA data from Mappls when the configured
    static API key has access to the Routing API.
    """

    BASE_URL = "https://route.mappls.com/route/direction"
    ROAD_SEGMENTS = [
        {
            "name": "Keishampat to Thangal Bazar",
            # Coordinates are stored as (latitude, longitude).
            "start": (24.8170, 93.9368),
            "end": (24.8170, 93.9550),
        },
    ]

    def __init__(self):
        self.access_token = os.getenv("MAPPLS_ACCESS_TOKEN")
        self._status = (
            "authorization_pending" if self.access_token else "not_configured"
        )

    @property
    def status(self) -> str:
        return self._status

    def _request_route_eta(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> dict:
        start_lat, start_lon = start
        end_lat, end_lon = end

        url = (
            f"{self.BASE_URL}/route_eta/driving/"
            f"{start_lon},{start_lat};"
            f"{end_lon},{end_lat}"
        )

        try:
            response = httpx.get(
                url,
                params={
                    "region": "ind",
                    "rtype": 0,
                    "access_token": self.access_token,
                },
                timeout=15,
            )
        except httpx.RequestError:
            self._status = "unavailable"
            raise RuntimeError("Could not reach the Mappls traffic API.") from None

        if response.status_code == 401:
            self._status = "authorization_denied"
            raise RuntimeError(
                "Mappls returned HTTP 401: this key is not authorized for the requested API."
            )
        if response.status_code == 403:
            self._status = "forbidden"
            raise RuntimeError(
                "Mappls returned HTTP 403: check the key's IP/domain whitelist and quota."
            )
        if response.is_error:
            self._status = "unavailable"
            raise RuntimeError(
                f"Mappls traffic request failed with HTTP {response.status_code}."
            )

        try:
            return response.json()
        except ValueError:
            self._status = "unavailable"
            raise RuntimeError("Mappls returned an invalid traffic response.") from None

    def _normalize_route(
        self,
        name: str,
        start: tuple[float, float],
        route_data: dict,
    ) -> TrafficPoint:
        routes = route_data.get("routes")
        if (route_data.get("code") or "").lower() != "ok" or not routes:
            self._status = "unavailable"
            raise RuntimeError("Mappls did not return a route for this road segment.")

        try:
            distance_meters = float(routes[0]["distance"])
            duration_seconds = float(routes[0]["duration"])
        except (KeyError, TypeError, ValueError):
            self._status = "unavailable"
            raise RuntimeError("Mappls route response is missing distance or duration.") from None

        average_speed_kmh = (
            round(distance_meters / duration_seconds * 3.6, 1)
            if distance_meters >= 0 and duration_seconds > 0
            else None
        )

        return TrafficPoint(
            name=name,
            latitude=start[0],
            longitude=start[1],
            status="unknown",
            average_speed_kmh=average_speed_kmh,
            traffic_delay_seconds=None,
            risk_score=None,
            data_source="Mappls",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_traffic(self) -> list[TrafficPoint]:
        """
        Retrieve traffic information from Mappls.

        Requests current route ETAs from Mappls for configured road segments.
        """

        if not self.access_token:
            raise RuntimeError("MAPPLS_ACCESS_TOKEN is not configured.")

        roads = [
            self._normalize_route(
                segment["name"],
                segment["start"],
                self._request_route_eta(segment["start"], segment["end"]),
            )
            for segment in self.ROAD_SEGMENTS
        ]
        self._status = "available"
        return roads


def create_traffic_provider() -> TrafficProvider:
    """Create the configured provider; TomTom is the default live source."""
    provider_name = os.getenv("TRAFFIC_PROVIDER", "tomtom").strip().lower()

    if provider_name == "mappls":
        return MapplsTrafficProvider()
    if provider_name == "tomtom":
        from services.tomtom_provider import TomTomTrafficProvider

        return TomTomTrafficProvider()

    raise RuntimeError("TRAFFIC_PROVIDER must be 'tomtom' or 'mappls'.")
