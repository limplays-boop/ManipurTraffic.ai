from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Manipur Traffic AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


traffic_points = [
    {
        "name": "Keishampat",
        "latitude": 24.8128,
        "longitude": 93.9365,
        "status": "critical",
        "average_speed": 9,
        "vehicles": 126,
        "risk_score": 91,
    },
    {
        "name": "Thangal Bazar",
        "latitude": 24.8177,
        "longitude": 93.9362,
        "status": "heavy",
        "average_speed": 15,
        "vehicles": 98,
        "risk_score": 78,
    },
    {
        "name": "Nagamapal",
        "latitude": 24.8215,
        "longitude": 93.945,
        "status": "moderate",
        "average_speed": 23,
        "vehicles": 67,
        "risk_score": 61,
    },
    {
        "name": "Paona Bazar",
        "latitude": 24.8157,
        "longitude": 93.9475,
        "status": "clear",
        "average_speed": 34,
        "vehicles": 41,
        "risk_score": 28,
    },
]


@app.get("/")
def root():
    return {
        "message": "Manipur Traffic AI backend is running"
    }


@app.get("/api/traffic")
def get_traffic():
    return {
        "city": "Imphal",
        "traffic_level": "moderate",
        "risk_score": 72,
    }


@app.get("/api/traffic/roads")
def get_traffic_roads():
    return {
        "city": "Imphal",
        "data_source": "demo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "roads": traffic_points,
    }

@app.get("/api/traffic/summary")
def get_traffic_summary():
    critical = 0
    heavy = 0
    moderate = 0
    clear = 0

    total_risk = 0

    for road in traffic_points:
        status = road["status"]

        if status == "critical":
            critical += 1
        elif status == "heavy":
            heavy += 1
        elif status == "moderate":
            moderate += 1
        elif status == "clear":
            clear += 1

        total_risk += road["risk_score"]

    total_roads = len(traffic_points)

    average_risk = round(total_risk / total_roads) if total_roads else 0

    return {
            "city": "Imphal",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_roads": total_roads,
            "critical_roads": critical,
            "heavy_roads": heavy,
            "moderate_roads": moderate,
            "clear_roads": clear,
             "average_risk_score": average_risk,
    }