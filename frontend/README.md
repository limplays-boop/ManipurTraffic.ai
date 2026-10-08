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
- `GET /api/weather/current`
- `GET /api/risk/map`
- `GET /api/risk/observations`
- `GET /api/risk/patterns`

Traffic-provider and traffic-road responses are shown as unavailable until Mappls access is verified; no demo traffic values are used. Weather is labelled as a model estimate, with its provider and valid/fetch times shown when returned. Risk observations, map points, and patterns are rendered only from backend responses. Risk scores are the backend's transparent baseline, not a trained AI prediction.

OpenStreetMap provides map tiles and its attribution remains visible in the map.

Run `npm run build` to type-check and create the production build.
