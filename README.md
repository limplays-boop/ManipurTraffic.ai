# Manipur Traffic

**A map-first road operations dashboard for exploring traffic conditions and transparent road-risk data across Manipur.**

Manipur Traffic combines a React and TypeScript map interface with a FastAPI service. Search for places, preview routes, inspect provider-reported traffic when configured, and review backend-recorded road-risk observations and patterns.

> **Data integrity:** live traffic depends on a configured provider and valid credentials. Weather is a model estimate, and risk scores are explainable operational baselines—not trained accident predictions. The dashboard does not invent missing measurements or map locations.

## Features

- Map-first, responsive interface with place suggestions, device location, route previews, and a backend risk layer.
- TomTom traffic flow, incidents, and route data when the backend is configured with an eligible API key. If live route data is unavailable, route previews may use OSRM and are identified as estimates, not live-traffic routes.
- Current Open-Meteo weather estimates with provider and timestamps when available.
- Source-attributed risk observations, an explainable baseline score, a risk map, and recurring time/location patterns.
- Separate, small public-report and historical-data views, labelled with their coverage and limitations.
- Explicit loading, empty, and unavailable states; no seeded traffic or observation values.

## Technology

- **Frontend:** React, TypeScript, Vite, Leaflet, and React Leaflet
- **Backend:** FastAPI, Pydantic, and SQLite
- **External data:** TomTom (optional traffic provider), Open-Meteo (weather estimate), OpenStreetMap-based place search and map tiles, and OSRM (route-estimate fallback)

## Run locally on Windows

Open two PowerShell terminals from the repository root.

### 1. Start the API

Create the Python environment and install backend dependencies once:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

For live TomTom traffic, create `backend\.env` and set a valid key with the required product access:

```text
TRAFFIC_PROVIDER=tomtom
TOMTOM_API_KEY=your_tomtom_api_key
```

Without a valid provider configuration, live traffic endpoints report unavailable. Keep credentials in the local, ignored `.env` file; never commit API keys.

Start Uvicorn from the backend directory so the service's local imports resolve:

```powershell
Set-Location backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API health check is at [http://localhost:8000/api/health](http://localhost:8000/api/health), and the interactive API reference is at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Start the frontend

In the second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally [http://localhost:5173](http://localhost:5173)). The frontend uses `http://localhost:8000` by default. To use another API origin, set `VITE_API_BASE_URL` in `frontend\.env`, for example:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## API surface

The API exposes these endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | API and risk-model health |
| `GET /api/traffic/provider` | Traffic provider and availability |
| `GET /api/traffic/roads` | Provider road-segment traffic |
| `GET /api/traffic/location` | Live flow for the requested nearby road segment |
| `POST /api/traffic/route` | Live route data when available |
| `GET /api/traffic/incidents` | Provider incidents for a map viewport |
| `GET /api/weather/current` | Current model-based weather estimate |
| `GET /api/risk/map` | Map aggregation of stored observations |
| `GET /api/risk/observations` | Recorded road-risk observations |
| `POST /api/risk/observations` | Store a source-attributed observation |
| `POST /api/risk/observations/batch` | Store a validated observation batch |
| `GET /api/risk/patterns` | Repeated time/location risk patterns |
| `GET /api/accidents/demo` | Small rule-based public-report example |
| `GET /api/accidents/history` | Published, source-attributed historical totals |

See [backend/README.md](backend/README.md) for endpoint contracts, scoring details, data provenance, and limitations.

## Data and model limitations

- **Traffic:** live values are only available when the selected provider is configured and covers the requested roads. A working frontend connection does not itself mean traffic data is live. OSRM fallback routes are not traffic-adjusted.
- **Weather:** Open-Meteo provides a model estimate, not a roadside station reading. Weather is only included in a risk score where the backend explicitly returns it and identifies its contribution.
- **Live traffic index:** this is a transparent operational index from measured inputs, not a crash probability or trained machine-learning model. It is not calibrated against Manipur crash outcomes or traffic exposure.
- **Observation baseline:** scores are computed from submitted measured factors. Missing factors are not fabricated or treated as zero.
- **Historical accidents:** the imported annual and highway summaries are limited public datasets, not a complete event-level register. Some highway entries have chainage descriptions rather than verified coordinates; they must not be plotted at invented locations or treated as model-training data.
- **Public-report example:** the small, rule-based report scan is illustrative only. It does not establish statewide rates, causal findings, or predictive accuracy.
- **Third-party services:** map tiles and place search use OpenStreetMap community services; route estimates may use the public OSRM service. Availability and usage policies are controlled by those providers. OpenStreetMap attribution is shown on the map.

## Development checks

Frontend:

```powershell
Set-Location frontend
npm run lint
npm run build
```

Backend tests:

```powershell
python -m pip install -r backend\requirements-dev.txt
python -m pytest backend\tests
```
