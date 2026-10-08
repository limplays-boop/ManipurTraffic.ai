import os
from datetime import datetime, timezone

import httpx

from models.traffic import TrafficPoint
from services.traffic_provider import TrafficProvider


class TomTomTrafficProvider(TrafficProvider):
    """Current route duration and delay from TomTom's Orbis Routing API."""

    source_name = "TomTom"
    ROUTE_URL = "https://api.tomtom.com/maps/orbis/routing/routes/calculate"
    FLOW_SEGMENT_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    ROAD_SEGMENTS = [
        {
            "name": "Keishampat to Thangal Bazar",
            # Coordinates are stored as (latitude, longitude).
            "start": (24.8170, 93.9368),
            "end": (24.8170, 93.9550),
        },
    ]

    def __init__(self):
        self.api_key = os.getenv("TOMTOM_API_KEY")
        self._status = "authorization_pending" if self.api_key else "not_configured"

    @property
    def status(self) -> str:
        return self._status

    def _request_route(self, start: tuple[float, float], end: tuple[float, float]) -> dict:
        start_lat, start_lon = start
        end_lat, end_lon = end
        request_body = {
            "routePlanningLocations": {
                "origin": {
                    "type": "Point",
                    "coordinates": [start_lon, start_lat],
                },
                "destination": {
                    "type": "Point",
                    "coordinates": [end_lon, end_lat],
                },
            },
            "traffic": "live",
        }

        try:
            response = httpx.post(
                self.ROUTE_URL,
                headers={
                    "TomTom-Api-Version": "3",
                    "TomTom-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                    "Attributes": "routes",
                },
                json=request_body,
                timeout=15,
            )
        except httpx.RequestError:
            self._status = "unavailable"
            raise RuntimeError("Could not reach the TomTom routing API.") from None

        if response.status_code == 401:
            self._status = "authorization_denied"
            raise RuntimeError("TomTom returned HTTP 401 for the route request.")
        if response.status_code == 403:
            self._status = "forbidden"
            raise RuntimeError("TomTom denied this route request; check API access and restrictions.")
        if response.status_code == 429:
            self._status = "rate_limited"
            raise RuntimeError("TomTom's request limit was reached.")
        if response.is_error:
            self._status = "unavailable"
            raise RuntimeError(
                f"TomTom routing request failed with HTTP {response.status_code}."
            )

        try:
            return response.json()
        except ValueError:
            self._status = "unavailable"
            raise RuntimeError("TomTom returned an invalid route response.") from None

    def _normalize_route(
        self,
        segment: dict,
        route_data: dict,
    ) -> TrafficPoint:
        routes = route_data.get("routes") or []
        if not routes or not isinstance(routes[0].get("summary"), dict):
            self._status = "unavailable"
            raise RuntimeError("TomTom did not return route summary data for this segment.")

        summary = routes[0]["summary"]
        try:
            distance_meters = float(summary["lengthInMeters"])
            duration_seconds = float(summary["travelDurationInSeconds"])
        except (KeyError, TypeError, ValueError):
            self._status = "unavailable"
            raise RuntimeError("TomTom route response is missing distance or duration.") from None

        delay = summary.get("trafficDelayDurationInSeconds")
        average_speed_kmh = (
            round(distance_meters / duration_seconds * 3.6, 1)
            if distance_meters >= 0 and duration_seconds > 0
            else None
        )

        return TrafficPoint(
            name=segment["name"],
            latitude=segment["start"][0],
            longitude=segment["start"][1],
            status="unknown",
            average_speed_kmh=average_speed_kmh,
            traffic_delay_seconds=int(delay) if delay is not None else None,
            risk_score=None,
            data_source=self.source_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_live_route(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> dict:
        """Calculate a user-selected route using TomTom's live traffic model."""
        if not self.api_key:
            raise RuntimeError("TOMTOM_API_KEY is not configured.")

        route_data = self._request_route(start, end)
        routes = route_data.get("routes") or []
        if not routes or not isinstance(routes[0].get("summary"), dict):
            self._status = "unavailable"
            raise RuntimeError("TomTom did not return route summary data.")

        route = routes[0]
        summary = route["summary"]
        try:
            distance_meters = float(summary["lengthInMeters"])
            duration_seconds = float(summary["travelDurationInSeconds"])
        except (KeyError, TypeError, ValueError):
            self._status = "unavailable"
            raise RuntimeError("TomTom route response is missing distance or duration.") from None

        coordinates = []
        for leg in route.get("legs") or []:
            path = leg.get("path") if isinstance(leg, dict) else None
            points = path.get("coordinates") if isinstance(path, dict) else None
            if not isinstance(points, list):
                continue
            for point in points:
                if (
                    isinstance(point, list)
                    and len(point) == 2
                    and all(isinstance(value, (int, float)) for value in point)
                    and (not coordinates or coordinates[-1] != point)
                ):
                    coordinates.append(point)

        if len(coordinates) < 2:
            self._status = "unavailable"
            raise RuntimeError("TomTom route response has no usable route geometry.")

        delay = summary.get("trafficDelayDurationInSeconds")
        self._status = "available"
        return {
            "distance_meters": distance_meters,
            "travel_duration_seconds": duration_seconds,
            "traffic_delay_seconds": int(delay) if delay is not None else None,
            "geometry": {"type": "LineString", "coordinates": coordinates},
        }

    def get_traffic_at_location(self, latitude: float, longitude: float) -> dict:
        """Get live flow data for the road segment nearest a coordinate."""
        if not self.api_key:
            raise RuntimeError("TOMTOM_API_KEY is not configured.")

        try:
            response = httpx.get(
                self.FLOW_SEGMENT_URL,
                params={
                    "key": self.api_key,
                    "point": f"{latitude},{longitude}",
                    "unit": "kmph",
                },
                timeout=15,
            )
        except httpx.RequestError:
            self._status = "unavailable"
            raise RuntimeError("Could not reach the TomTom traffic flow API.") from None

        if response.status_code in (401, 403):
            self._status = "authorization_denied"
            raise RuntimeError(
                f"TomTom denied the traffic flow request with HTTP {response.status_code}; "
                "check Traffic Flow Segment Data access for this key."
            )
        if response.status_code == 429:
            self._status = "rate_limited"
            raise RuntimeError("TomTom's traffic flow request limit was reached.")
        if response.is_error:
            self._status = "unavailable"
            raise RuntimeError(
                f"TomTom traffic flow request failed with HTTP {response.status_code}."
            )

        try:
            payload = response.json()
            flow = payload["flowSegmentData"]
            current_speed = float(flow["currentSpeed"])
            free_flow_speed = float(flow["freeFlowSpeed"])
            current_travel_time = float(flow["currentTravelTime"])
            free_flow_travel_time = float(flow["freeFlowTravelTime"])
            confidence = float(flow["confidence"])
        except (ValueError, TypeError, KeyError):
            self._status = "unavailable"
            raise RuntimeError("TomTom returned incomplete traffic flow data.") from None

        coordinate_container = flow.get("coordinates") or {}
        coordinate_items = coordinate_container.get("coordinate", [])
        if isinstance(coordinate_items, dict):
            coordinate_items = [coordinate_items]
        coordinates = [
            [float(item["longitude"]), float(item["latitude"])]
            for item in coordinate_items
            if isinstance(item, dict)
            and item.get("longitude") is not None
            and item.get("latitude") is not None
        ]

        self._status = "available"
        return {
            "status": "available",
            "data_source": "TomTom Traffic Flow Segment Data",
            "latitude": latitude,
            "longitude": longitude,
            "current_speed_kmh": current_speed,
            "free_flow_speed_kmh": free_flow_speed,
            "current_travel_time_seconds": current_travel_time,
            "free_flow_travel_time_seconds": free_flow_travel_time,
            "traffic_delay_seconds": max(0, current_travel_time - free_flow_travel_time),
            "confidence": confidence,
            "road_closure": bool(flow.get("roadClosure", False)),
            "geometry": (
                {"type": "LineString", "coordinates": coordinates}
                if len(coordinates) >= 2
                else None
            ),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_traffic(self) -> list[TrafficPoint]:
        if not self.api_key:
            raise RuntimeError("TOMTOM_API_KEY is not configured.")

        roads = [
            self._normalize_route(
                segment,
                self._request_route(segment["start"], segment["end"]),
            )
            for segment in self.ROAD_SEGMENTS
        ]
        self._status = "available"
        return roads


class TomTomIncidentProvider:
    """Current TomTom incidents for a caller-supplied map bounding box."""

    source_name = "TomTom"
    INCIDENTS_URL = "https://api.tomtom.com/maps/orbis/traffic/incidents/details"
    ATTRIBUTES = (
        "incidents(type,geometry(type,coordinates),properties("
        "id,iconCategory,magnitudeOfDelay,startTime,endTime,from,to,"
        "lengthInMeters,delayInSeconds,timeValidity,events(description,code,iconCategory)))"
    )

    def __init__(self):
        self.api_key = os.getenv("TOMTOM_API_KEY")
        self._status = "authorization_pending" if self.api_key else "not_configured"

    @property
    def status(self) -> str:
        return self._status

    def get_incidents(
        self,
        bbox: tuple[float, float, float, float],
    ) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("TOMTOM_API_KEY is not configured.")

        try:
            response = httpx.get(
                self.INCIDENTS_URL,
                params={
                    "apiVersion": 2,
                    "bbox": ",".join(str(value) for value in bbox),
                    "timeValidity": "present",
                },
                headers={
                    "TomTom-Api-Key": self.api_key,
                    "Attributes": self.ATTRIBUTES,
                },
                timeout=15,
            )
        except httpx.RequestError:
            self._status = "unavailable"
            raise RuntimeError("Could not reach the TomTom traffic incidents API.") from None

        if response.status_code == 401:
            self._status = "authorization_denied"
            raise RuntimeError("TomTom returned HTTP 401 for the incident request.")
        if response.status_code == 403:
            self._status = "forbidden"
            raise RuntimeError("TomTom denied this incident request; check API access and restrictions.")
        if response.status_code == 429:
            self._status = "rate_limited"
            raise RuntimeError("TomTom's incident request limit was reached.")
        if response.status_code == 204:
            self._status = "available"
            return []
        if response.is_error:
            self._status = "unavailable"
            raise RuntimeError(
                f"TomTom incidents request failed with HTTP {response.status_code}."
            )

        try:
            payload = response.json()
            raw_incidents = payload.get("incidents") or []
        except (ValueError, AttributeError):
            self._status = "unavailable"
            raise RuntimeError("TomTom returned an invalid incidents response.") from None

        self._status = "available"
        return [
            {
                "incident_id": incident.get("properties", {}).get("id"),
                "category": incident.get("properties", {}).get("iconCategory"),
                "severity": incident.get("properties", {}).get("magnitudeOfDelay"),
                "start_time": incident.get("properties", {}).get("startTime"),
                "end_time": incident.get("properties", {}).get("endTime"),
                "road_from": incident.get("properties", {}).get("from"),
                "road_to": incident.get("properties", {}).get("to"),
                "length_meters": incident.get("properties", {}).get("lengthInMeters"),
                "delay_seconds": incident.get("properties", {}).get("delayInSeconds"),
                "time_validity": incident.get("properties", {}).get("timeValidity"),
                "events": incident.get("properties", {}).get("events", []),
                "geometry": incident.get("geometry"),
                "data_source": self.source_name,
            }
            for incident in raw_incidents
            if isinstance(incident, dict)
        ]
