import httpx
import pytest

from services.traffic_provider import MapplsTrafficProvider


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.is_error = status_code >= 400

    def json(self):
        return self._payload


def provider_with_token(monkeypatch):
    monkeypatch.setattr(
        "services.traffic_provider.os.getenv",
        lambda name: "test-mappls-key" if name == "MAPPLS_ACCESS_TOKEN" else None,
    )
    return MapplsTrafficProvider()


def test_traffic_request_sends_longitude_latitude_and_normalizes_eta(monkeypatch):
    provider = provider_with_token(monkeypatch)
    request = {}

    def fake_get(url, *, params, timeout):
        request.update(url=url, params=params, timeout=timeout)
        return FakeResponse(
            payload={
                "code": "Ok",
                "routes": [{"distance": 1000, "duration": 120}],
            }
        )

    monkeypatch.setattr("services.traffic_provider.httpx.get", fake_get)

    roads = provider.get_traffic()

    assert "/93.9368,24.817;93.955,24.817" in request["url"]
    assert request["params"]["region"] == "ind"
    assert request["params"]["rtype"] == 0
    assert request["timeout"] == 15
    assert len(roads) == 1
    assert roads[0].average_speed_kmh == 30
    assert roads[0].status == "unknown"
    assert roads[0].traffic_delay_seconds is None
    assert roads[0].timestamp
    assert provider.status == "available"


def test_unauthorized_response_is_sanitized_and_reported(monkeypatch):
    provider = provider_with_token(monkeypatch)
    monkeypatch.setattr(
        "services.traffic_provider.httpx.get",
        lambda *args, **kwargs: FakeResponse(status_code=401),
    )

    with pytest.raises(RuntimeError) as error:
        provider.get_traffic()

    assert "401" in str(error.value)
    assert "test-mappls-key" not in str(error.value)
    assert provider.status == "authorization_denied"


def test_network_errors_do_not_include_request_details(monkeypatch):
    provider = provider_with_token(monkeypatch)

    def fail_request(*args, **kwargs):
        request = httpx.Request("GET", "https://route.mappls.com/secret")
        raise httpx.ConnectError("network failure", request=request)

    monkeypatch.setattr("services.traffic_provider.httpx.get", fail_request)

    with pytest.raises(RuntimeError) as error:
        provider.get_traffic()

    assert str(error.value) == "Could not reach the Mappls traffic API."
    assert provider.status == "unavailable"
