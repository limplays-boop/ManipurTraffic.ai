from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from models.accident_history import HistoricalAccidentHistoryResponse
from models.risk import (
    RiskMapResponse,
    RiskObservationBatchCreate,
    RiskObservationBatchResponse,
    RiskObservationCreate,
    RiskObservationListResponse,
    RiskPatternsResponse,
    RiskPoint,
)
from models.traffic import TrafficRouteRequest
from models.weather import WeatherCurrent
from services.historical_accident_provider import HistoricalAccidentProvider
from services.risk_analytics import RiskAnalytics
from services.risk_engine import RiskEngine, RiskFactors
from services.risk_repository import RiskRepository
from services.tomtom_provider import TomTomIncidentProvider
from services.traffic_provider import create_traffic_provider
from services.weather_provider import OpenMeteoWeatherProvider


app = FastAPI(
    title="Manipur Traffic AI",
    description="Traffic status and explainable road-risk analysis API.",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

traffic_provider = create_traffic_provider()
incident_provider = TomTomIncidentProvider()
weather_provider = OpenMeteoWeatherProvider()
risk_engine = RiskEngine()
risk_analytics = RiskAnalytics(risk_engine)
risk_repository = RiskRepository()
historical_accident_provider = HistoricalAccidentProvider()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_risk_point(observation: RiskObservationCreate) -> RiskPoint:
    return risk_engine.create_risk_point(
        name=observation.name,
        latitude=observation.latitude,
        longitude=observation.longitude,
        factors=RiskFactors(**observation.factors.model_dump()),
        data_source=observation.source,
        timestamp=observation.observed_at,
        location_id=observation.location_id,
    )


@app.get("/")
def root():
    return {
        "message": "Manipur Traffic AI backend is running",
        "risk_analysis": "available",
        "risk_model": risk_engine.MODEL_VERSION,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "risk_observations": risk_repository.count(),
        "risk_model": risk_engine.MODEL_VERSION,
    }


@app.get("/api/traffic/provider")
def get_traffic_provider():
    return {
        "provider": traffic_provider.source_name,
        "status": traffic_provider.status,
    }


@app.get(
    "/api/accidents/history",
    response_model=HistoricalAccidentHistoryResponse,
)
def get_historical_accident_data():
    try:
        return historical_accident_provider.get_history()
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(
            status_code=503,
            detail="Published historical accident data is unavailable.",
        ) from error


@app.get("/api/weather/current", response_model=WeatherCurrent)
def get_current_weather(
    latitude: float = Query(default=24.817, ge=-90, le=90),
    longitude: float = Query(default=93.9368, ge=-180, le=180),
):
    try:
        return weather_provider.get_current(latitude, longitude)
    except RuntimeError:
        return WeatherCurrent(
            status="unavailable",
            latitude=latitude,
            longitude=longitude,
            fetched_at=_now_utc(),
            message="Current weather data is temporarily unavailable.",
        )


@app.get("/api/traffic")
def get_traffic():
    try:
        roads = traffic_provider.get_traffic()
        risk_scores = [
            road.risk_score
            for road in roads
            if road.risk_score is not None
        ]
        average_risk = (
            round(sum(risk_scores) / len(risk_scores))
            if risk_scores
            else None
        )

        if average_risk is None:
            traffic_level = "unknown"
        elif average_risk >= 80:
            traffic_level = "critical"
        elif average_risk >= 60:
            traffic_level = "heavy"
        elif average_risk >= 30:
            traffic_level = "moderate"
        else:
            traffic_level = "clear"

        return {
            "city": "Imphal",
            "status": "available",
            "traffic_level": traffic_level,
            "risk_score": average_risk,
        }
    except RuntimeError as error:
        return {
            "city": "Imphal",
            "status": "unavailable",
            "traffic_level": "unknown",
            "risk_score": None,
            "message": str(error),
        }


@app.get("/api/traffic/roads")
def get_traffic_roads():
    try:
        roads = traffic_provider.get_traffic()
        return {
            "city": "Imphal",
            "data_source": traffic_provider.source_name,
            "status": "available",
            "timestamp": _now_utc(),
            "roads": roads,
        }
    except RuntimeError as error:
        return {
            "city": "Imphal",
            "data_source": traffic_provider.source_name,
            "status": "unavailable",
            "message": str(error),
            "timestamp": _now_utc(),
            "roads": [],
        }


@app.post("/api/traffic/route")
def get_live_traffic_route(request: TrafficRouteRequest):
    start = (request.origin_latitude, request.origin_longitude)
    end = (request.destination_latitude, request.destination_longitude)
    try:
        route = traffic_provider.get_live_route(start, end)
        return {
            "status": "available",
            "data_source": traffic_provider.source_name,
            "timestamp": _now_utc(),
            **route,
        }
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@app.get("/api/traffic/location")
def get_live_traffic_at_location(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
):
    try:
        return traffic_provider.get_traffic_at_location(latitude, longitude)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@app.get("/api/traffic/incidents")
def get_traffic_incidents(
    min_longitude: float = Query(ge=-180, le=180),
    min_latitude: float = Query(ge=-90, le=90),
    max_longitude: float = Query(ge=-180, le=180),
    max_latitude: float = Query(ge=-90, le=90),
):
    bbox = (min_longitude, min_latitude, max_longitude, max_latitude)
    if min_longitude >= max_longitude or min_latitude >= max_latitude:
        raise HTTPException(
            status_code=422,
            detail="Bounding-box minimum coordinates must be below the maximum coordinates.",
        )

    try:
        incidents = incident_provider.get_incidents(bbox)
        return {
            "status": "available" if incidents else "empty",
            "data_source": incident_provider.source_name,
            "timestamp": _now_utc(),
            "incident_count": len(incidents),
            "incidents": incidents,
        }
    except RuntimeError as error:
        return {
            "status": "unavailable",
            "data_source": incident_provider.source_name,
            "timestamp": _now_utc(),
            "incident_count": None,
            "message": str(error),
            "incidents": [],
        }


@app.get("/api/traffic/summary")
def get_traffic_summary():
    try:
        roads = traffic_provider.get_traffic()
        counts = {
            "critical_roads": 0,
            "heavy_roads": 0,
            "moderate_roads": 0,
            "clear_roads": 0,
            "unknown_roads": 0,
        }

        for road in roads:
            if road.status == "critical":
                counts["critical_roads"] += 1
            elif road.status == "heavy":
                counts["heavy_roads"] += 1
            elif road.status == "moderate":
                counts["moderate_roads"] += 1
            elif road.status == "clear":
                counts["clear_roads"] += 1
            else:
                counts["unknown_roads"] += 1

        risk_scores = [
            road.risk_score
            for road in roads
            if road.risk_score is not None
        ]
        average_risk = (
            round(sum(risk_scores) / len(risk_scores), 2)
            if risk_scores
            else None
        )

        return {
            "city": "Imphal",
            "status": "available",
            "timestamp": _now_utc(),
            "total_roads": len(roads),
            **counts,
            "average_risk_score": average_risk,
        }
    except RuntimeError as error:
        return {
            "city": "Imphal",
            "status": "unavailable",
            "timestamp": _now_utc(),
            "total_roads": None,
            "critical_roads": None,
            "heavy_roads": None,
            "moderate_roads": None,
            "clear_roads": None,
            "unknown_roads": None,
            "average_risk_score": None,
            "message": str(error),
        }


@app.post(
    "/api/risk/observations",
    response_model=RiskPoint,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_observation(observation: RiskObservationCreate):
    point = _build_risk_point(observation)
    risk_repository.add_many([point])
    return point


@app.post(
    "/api/risk/observations/batch",
    response_model=RiskObservationBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_observation_batch(batch: RiskObservationBatchCreate):
    points = [_build_risk_point(observation) for observation in batch.observations]
    risk_repository.add_many(points)
    return {"created_count": len(points), "observations": points}


@app.get(
    "/api/risk/observations",
    response_model=RiskObservationListResponse,
)
def list_risk_observations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    total_count = risk_repository.count()
    observations = risk_repository.list(limit=limit, offset=offset)
    return {
        "status": "available" if total_count else "empty",
        "total_count": total_count,
        "observations": observations,
    }


@app.get("/api/risk/map", response_model=RiskMapResponse)
def get_risk_map():
    observations = risk_repository.list_all()
    locations = risk_analytics.build_map(observations)
    return {
        "status": "available" if observations else "empty",
        "city": "Imphal",
        "aggregation": "Mean of scored observations grouped by location_id",
        "model_version": risk_engine.MODEL_VERSION,
        "observation_count": len(observations),
        "locations": locations,
        "generated_at": _now_utc(),
    }


@app.get("/api/risk/patterns", response_model=RiskPatternsResponse)
def get_risk_patterns(
    minimum_occurrences: int = Query(default=2, ge=2, le=1000),
    risk_threshold: float = Query(default=60, ge=60, le=100),
):
    observations = risk_repository.list_all()
    patterns = risk_analytics.find_recurring_patterns(
        observations,
        minimum_occurrences=minimum_occurrences,
        risk_threshold=risk_threshold,
    )
    return {
        "status": "available" if observations else "empty",
        "timezone": "Asia/Kolkata",
        "minimum_occurrences": minimum_occurrences,
        "risk_threshold": risk_threshold,
        "patterns": patterns,
        "generated_at": _now_utc(),
    }
