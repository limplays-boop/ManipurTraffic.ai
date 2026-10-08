import httpx
from fastapi.testclient import TestClient

import main
from services.weather_provider import OpenMeteoWeatherProvider


def test_current_weather_endpoint_uses_provider_data(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "timezone": "Asia/Kolkata",
                "utc_offset_seconds": 19800,
                "current": {
                    "time": "2026-10-07T14:00",
                    "temperature_2m": 28.4,
                    "relative_humidity_2m": 72,
                    "precipitation": 0.2,
                    "rain": 0.2,
                    "showers": 0,
                    "weather_code": 61,
                    "wind_speed_10m": 8.3,
                    "wind_gusts_10m": 11.5,
                },
            }

    monkeypatch.setattr(
        "services.weather_provider.httpx.get",
        lambda *args, **kwargs: FakeResponse(),
    )
    client = TestClient(main.app)

    response = client.get("/api/weather/current")

    assert response.status_code == 200
    weather = response.json()
    assert weather["status"] == "available"
    assert weather["provider"] == "Open-Meteo"
    assert weather["data_basis"] == "weather_model_estimate"
    assert weather["temperature_c"] == 28.4
    assert weather["weather_code"] == 61
    assert weather["valid_at"].startswith("2026-10-07T14:00:00+05:30")
    assert weather["fetched_at"]


def test_weather_provider_requests_named_fields_and_units(monkeypatch):
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "timezone": "Asia/Kolkata",
                "utc_offset_seconds": 19800,
                "current": {"time": "2026-10-07T14:00"},
            }

    def fake_get(url, *, params, timeout):
        seen.update(url=url, params=params, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("services.weather_provider.httpx.get", fake_get)

    result = OpenMeteoWeatherProvider().get_current(24.817, 93.9368)

    assert result.status == "available"
    assert "temperature_2m" in seen["params"]["current"]
    assert seen["params"]["temperature_unit"] == "celsius"
    assert seen["params"]["wind_speed_unit"] == "kmh"
    assert seen["params"]["precipitation_unit"] == "mm"
    assert seen["timeout"] == 10


def test_weather_endpoint_returns_unavailable_without_upstream_error_details(monkeypatch):
    def fail_get(*args, **kwargs):
        request = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
        raise httpx.ConnectError("network failure", request=request)

    monkeypatch.setattr("services.weather_provider.httpx.get", fail_get)
    client = TestClient(main.app)

    response = client.get("/api/weather/current?latitude=24.817&longitude=93.9368")

    assert response.status_code == 200
    weather = response.json()
    assert weather["status"] == "unavailable"
    assert weather["temperature_c"] is None
    assert "network failure" not in response.text
