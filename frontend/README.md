# Manipur Traffic Risk Dashboard

The frontend is a React, TypeScript, and Vite operations dashboard. It requests its data from the FastAPI service and does not seed sample observations or traffic values.

## Run locally

```sh
npm install
npm run dev
```

The API base URL defaults to `http://localhost:8000`, matching the backend's local CORS configuration. Set `VITE_API_BASE_URL` in a local `.env` file to point at another backend, for example:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Backend requests

The dashboard checks `GET /api/health` and requests:

- `GET /api/traffic/provider`
- `GET /api/traffic/roads`
- `GET /api/traffic/location`
- `POST /api/traffic/route`
- `GET /api/weather/current`
- `GET /api/risk/map`
- `GET /api/risk/observations`
- `GET /api/risk/patterns`
- `GET /api/accidents/demo`

Traffic-provider and traffic-road responses are shown as unavailable until Mappls access is verified; no demo traffic values are used. Weather is labelled as a model estimate, with its provider and valid/fetch times shown when returned. Risk observations, map points, and patterns are rendered only from backend responses. Risk scores are the backend's transparent baseline, not a trained AI prediction.

The Demo AI analysis panel scans two anonymized public Manipur Police report summaries with transparent keyword rules and shows how many reports match each pattern. This is a small rule-based demonstration, not a trained model, statewide rate, calibrated risk score, or prediction. The reports have no verified coordinates or matched traffic, weather, or non-crash comparison data, so the UI does not plot them on the risk map.

The selected-location traffic card and live route preview show the live traffic risk index from TomTom flow or route data, with current Open-Meteo weather when available. These are live provider readings, not seeded demo values. The index is a transparent operational score, not a trained machine-learning prediction of crashes; its factors, scoring method, and limits are displayed in the interface. OSRM fallback route estimates do not receive a live traffic risk score.

OpenStreetMap provides map tiles and its attribution remains visible in the map.

Run `npm run build` to type-check and create the production build.
