import httpx
import pytest

from services.tomtom_provider import TomTomIncidentProvider, TomTomTrafficProvider


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.is_error = status_code >= 400

    def json(self):
        return self._payload


def test_route_request_uses_tomtom_live_traffic_and_normalizes_summary(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomTrafficProvider()
    request = {}

    def fake_post(url, *, headers, json, timeout):
        request.update(url=url, headers=headers, json=json, timeout=timeout)
        return FakeResponse(
            payload={
                "routes": [
                    {
                        "summary": {
                            "lengthInMeters": 1200,
                            "travelDurationInSeconds": 180,
                            "trafficDelayDurationInSeconds": 25,
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("services.tomtom_provider.httpx.post", fake_post)

    roads = provider.get_traffic()

    assert request["url"] == provider.ROUTE_URL
    assert request["headers"]["TomTom-Api-Key"] == "test-tomtom-key"
    assert request["headers"]["TomTom-Api-Version"] == "3"
    assert request["json"]["traffic"] == "live"
    assert request["json"]["routePlanningLocations"]["origin"]["coordinates"] == [
        93.9368,
        24.817,
    ]
    assert roads[0].average_speed_kmh == 24
    assert roads[0].traffic_delay_seconds == 25
    assert roads[0].status == "unknown"
    assert roads[0].risk_score is None
    assert roads[0].data_source == "TomTom"
    assert provider.status == "available"


def test_user_route_returns_live_traffic_summary_and_geojson(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomTrafficProvider()

    def fake_post(url, *, headers, json, timeout):
        return FakeResponse(
            payload={
                "routes": [
                    {
                        "summary": {
                            "lengthInMeters": 2400,
                            "travelDurationInSeconds": 360,
                            "trafficDelayDurationInSeconds": 42,
                        },
                        "legs": [
                            {
                                "path": {
                                    "coordinates": [[93.9, 24.8], [93.91, 24.81]],
                                }
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("services.tomtom_provider.httpx.post", fake_post)

    route = provider.get_live_route((24.8, 93.9), (24.81, 93.91))

    assert route["distance_meters"] == 2400
    assert route["travel_duration_seconds"] == 360
    assert route["traffic_delay_seconds"] == 42
    assert route["geometry"] == {
        "type": "LineString",
        "coordinates": [[93.9, 24.8], [93.91, 24.81]],
    }


def test_route_unauthorized_error_does_not_expose_api_key(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomTrafficProvider()
    monkeypatch.setattr(
        "services.tomtom_provider.httpx.post",
        lambda *args, **kwargs: FakeResponse(status_code=401),
    )

    with pytest.raises(RuntimeError) as error:
        provider.get_traffic()

    assert "test-tomtom-key" not in str(error.value)
    assert "401" in str(error.value)
    assert provider.status == "authorization_denied"


def test_incidents_request_uses_bbox_and_normalizes_geojson(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomIncidentProvider()
    request = {}

    def fake_get(url, *, params, headers, timeout):
        request.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse(
            payload={
                "incidents": [
                    {
                        "geometry": {
                            "type": "Point",
                            "coordinates": [93.94, 24.82],
                        },
                        "properties": {
                            "id": "incident-1",
                            "iconCategory": "accident",
                            "magnitudeOfDelay": "minor",
                            "delayInSeconds": 45,
                            "timeValidity": "present",
                            "events": [{"description": "Accident"}],
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr("services.tomtom_provider.httpx.get", fake_get)

    incidents = provider.get_incidents((93.8, 24.7, 94.0, 24.9))

    assert request["params"]["apiVersion"] == 2
    assert request["params"]["bbox"] == "93.8,24.7,94.0,24.9"
    assert request["params"]["timeValidity"] == "present"
    assert request["headers"]["TomTom-Api-Key"] == "test-tomtom-key"
    assert incidents[0]["incident_id"] == "incident-1"
    assert incidents[0]["category"] == "accident"
    assert incidents[0]["geometry"]["coordinates"] == [93.94, 24.82]
    assert incidents[0]["data_source"] == "TomTom"
    assert provider.status == "available"


def test_incidents_handle_no_current_results(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomIncidentProvider()
    monkeypatch.setattr(
        "services.tomtom_provider.httpx.get",
        lambda *args, **kwargs: FakeResponse(status_code=204),
    )

    assert provider.get_incidents((93.8, 24.7, 94.0, 24.9)) == []
    assert provider.status == "available"


def test_route_network_error_is_sanitized(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-tomtom-key")
    provider = TomTomTrafficProvider()

    def fail_request(*args, **kwargs):
        request = httpx.Request("POST", provider.ROUTE_URL)
        raise httpx.ConnectError("failed", request=request)

    monkeypatch.setattr("services.tomtom_provider.httpx.post", fail_request)

    with pytest.raises(RuntimeError) as error:
        provider.get_traffic()

    assert str(error.value) == "Could not reach the TomTom routing API."
    assert provider.status == "unavailable"
