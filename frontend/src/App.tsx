import { useCallback, useEffect, useState, type FormEvent } from 'react'
import './App.css'
import MapView from './MapView'
import { apiGet, ApiError } from './api'
import {
  ensureDeviceLocationPermission,
  getCurrentDeviceLocation,
  getDrivingRoute,
  getLiveTrafficAtLocation,
  searchPlaces,
  suggestPlaces,
  type LocationTraffic,
  type MapPlace,
  type RoutePreview,
} from './mapServices'

type RemoteData<T> = {
  status: 'loading' | 'available' | 'empty' | 'unavailable' | 'error'
  data?: T
  message?: string
}

type TrafficRoads = {
  city?: string
  data_source?: string
  status?: string
  timestamp?: string
  roads?: TrafficRoad[]
  message?: string
}

type TrafficRoad = {
  name?: string
  average_speed_kmh?: number | null
  traffic_delay_seconds?: number | null
  status?: string
}

type TrafficProvider = {
  provider?: string
  status?: string
}

type CurrentWeather = {
  status?: string
  provider?: string
  data_basis?: string
  valid_at?: string | null
  fetched_at?: string | null
  timezone?: string | null
  temperature_c?: number | null
  relative_humidity_pct?: number | null
  precipitation_mm?: number | null
  wind_speed_kmh?: number | null
  message?: string | null
}

type DashboardData = {
  health: RemoteData<unknown>
  provider: RemoteData<TrafficProvider>
  roads: RemoteData<TrafficRoads>
  weather: RemoteData<CurrentWeather>
  riskMap: RemoteData<unknown>
  observations: RemoteData<unknown>
  patterns: RemoteData<unknown>
}

type ToolMode = 'search' | 'directions'
type PlaceSearchState = 'idle' | 'loading' | 'results' | 'empty' | 'error'
type SuggestionState = 'idle' | 'loading' | 'results' | 'empty' | 'error'
type RouteField = 'start' | 'end'

function PlaceSuggestions({
  id,
  places,
  state,
  errorMessage,
  onSelect,
}: {
  id: string
  places: MapPlace[]
  state: SuggestionState
  errorMessage: string
  onSelect: (place: MapPlace) => void
}) {
  if (state === 'idle') return null

  return (
    <div className="suggestion-popover" id={id}>
      {state === 'loading' ? (
        <p className="suggestion-status" role="status">Looking for places…</p>
      ) : null}
      {state === 'empty' ? (
        <p className="suggestion-status">No nearby matches. Keep typing or use Search.</p>
      ) : null}
      {state === 'error' ? (
        <p className="suggestion-status suggestion-error" role="status">
          Suggestions unavailable. Use Search to try again.
          {errorMessage ? ` ${errorMessage}` : ''}
        </p>
      ) : null}
      {state === 'results' ? (
        <div className="suggestion-list" role="listbox" aria-label="Place suggestions">
          {places.map((place, index) => (
            <button
              className="suggestion-option"
              id={`${id}-option-${index}`}
              key={`${place.latitude}-${place.longitude}-${index}`}
              type="button"
              role="option"
              aria-selected="false"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => onSelect(place)}
            >
              <span className="suggestion-pin" aria-hidden="true">⌖</span>
              <span className="suggestion-copy">
                <strong>{place.name}</strong>
                <small>{place.displayName}</small>
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

const emptyDashboard: DashboardData = {
  health: { status: 'loading' },
  provider: { status: 'loading' },
  roads: { status: 'loading' },
  weather: { status: 'loading' },
  riskMap: { status: 'loading' },
  observations: { status: 'loading' },
  patterns: { status: 'loading' },
}

async function readEndpoint<T>(path: string): Promise<RemoteData<T>> {
  try {
    const data = await apiGet<T>(path)
    if (
      data &&
      typeof data === 'object' &&
      'status' in data &&
      data.status === 'unavailable'
    ) {
      const payload = data as T & { message?: string }
      return {
        status: 'unavailable',
        data,
        message: payload.message ?? 'The backend reports this data source as unavailable.',
      }
    }
    if (isEmptyPayload(data)) return { status: 'empty', data }
    return { status: 'available', data }
  } catch (error) {
    const message =
      error instanceof Error ? error.message : 'Unexpected API response.'
    return {
      status: error instanceof ApiError && error.status === 404 ? 'unavailable' : 'error',
      message,
    }
  }
}

function isEmptyPayload(value: unknown): boolean {
  if (Array.isArray(value)) return value.length === 0
  if (!value || typeof value !== 'object') return false

  const record = value as Record<string, unknown>
  const collectionKeys = [
    'roads',
    'observations',
    'patterns',
    'risk_map',
    'risk_points',
    'points',
    'locations',
    'risk_areas',
    'features',
  ]
  return collectionKeys.some((key) => {
    const collection = record[key]
    return Array.isArray(collection) && collection.length === 0
  }) ||
    (record.data !== value && isEmptyPayload(record.data))
}

function displayValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (value === null || value === undefined) return '—'
  return JSON.stringify(value)
}

function humanize(key: string): string {
  return key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatWeatherTime(value: string | null | undefined): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Kolkata',
  })
}

function DataState({ state }: { state: RemoteData<unknown> }) {
  if (state.status === 'loading') {
    return <p className="state-message">Loading from the backend…</p>
  }
  if (state.status === 'empty') {
    return <p className="state-message">The backend returned an empty response.</p>
  }
  if (state.status === 'unavailable') {
    return <p className="state-message">Endpoint unavailable: {state.message}</p>
  }
  if (state.status === 'error') {
    return <p className="state-message state-error">Unable to load: {state.message}</p>
  }
  return null
}

function getRecords(value: unknown, keys: string[]): Record<string, unknown>[] | null {
  if (Array.isArray(value)) {
    return value.filter(
      (row): row is Record<string, unknown> =>
        Boolean(row) && typeof row === 'object' && !Array.isArray(row),
    )
  }
  if (!value || typeof value !== 'object') return null

  const record = value as Record<string, unknown>
  for (const key of keys) {
    if (Array.isArray(record[key])) {
      return (record[key] as unknown[]).filter(
        (row): row is Record<string, unknown> =>
          Boolean(row) && typeof row === 'object' && !Array.isArray(row),
      )
    }
  }

  const nested = record.data
  if (nested && typeof nested === 'object' && !Array.isArray(nested)) {
    return getRecords(nested, keys)
  }
  return [record]
}

function RecordTable({
  state,
  keys,
  emptyMessage,
}: {
  state: RemoteData<unknown>
  keys: string[]
  emptyMessage: string
}) {
  if (state.status !== 'available') {
    if (state.status === 'empty') return <p className="state-message">{emptyMessage}</p>
    return <DataState state={state} />
  }

  const records = getRecords(state.data, keys)
  if (!records || records.length === 0) {
    return <p className="state-message">{emptyMessage}</p>
  }

  const columns = [...new Set(records.flatMap((record) => Object.keys(record)))]
  if (columns.length === 0) {
    return <p className="state-message">{emptyMessage}</p>
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">{humanize(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={String(record.id ?? record.observed_at ?? index)}>
              {columns.map((column) => (
                <td key={column}>{displayValue(record[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function App() {
  const [dashboard, setDashboard] = useState<DashboardData>(emptyDashboard)
  const [refreshing, setRefreshing] = useState(false)
  const [checkedAt, setCheckedAt] = useState<string | null>(null)
  const [toolMode, setToolMode] = useState<ToolMode>('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchState, setSearchState] = useState<PlaceSearchState>('idle')
  const [searchMessage, setSearchMessage] = useState('')
  const [searchResults, setSearchResults] = useState<MapPlace[]>([])
  const [searchFocused, setSearchFocused] = useState(false)
  const [searchSuggestions, setSearchSuggestions] = useState<MapPlace[]>([])
  const [searchSuggestionState, setSearchSuggestionState] = useState<SuggestionState>('idle')
  const [searchSuggestionMessage, setSearchSuggestionMessage] = useState('')
  const [locationTraffic, setLocationTraffic] = useState<RemoteData<LocationTraffic>>({ status: 'empty' })
  const [searchLocationLoading, setSearchLocationLoading] = useState(false)
  const [directionsLocationLoading, setDirectionsLocationLoading] = useState(false)
  const [selectedPlace, setSelectedPlace] = useState<MapPlace | null>(null)
  const [routeStart, setRouteStart] = useState<MapPlace | null>(null)
  const [routeEnd, setRouteEnd] = useState<MapPlace | null>(null)
  const [startQuery, setStartQuery] = useState('')
  const [endQuery, setEndQuery] = useState('')
  const [routeSearchField, setRouteSearchField] = useState<RouteField | null>(null)
  const [routeSearchState, setRouteSearchState] = useState<PlaceSearchState>('idle')
  const [routeCandidates, setRouteCandidates] = useState<MapPlace[]>([])
  const [focusedRouteField, setFocusedRouteField] = useState<RouteField | null>(null)
  const [routeSuggestions, setRouteSuggestions] = useState<MapPlace[]>([])
  const [routeSuggestionState, setRouteSuggestionState] = useState<SuggestionState>('idle')
  const [routeSuggestionMessage, setRouteSuggestionMessage] = useState('')
  const [routeMessage, setRouteMessage] = useState('')
  const [routePreview, setRoutePreview] = useState<RoutePreview | null>(null)
  const [routeError, setRouteError] = useState('')
  const [routeLoading, setRouteLoading] = useState(false)
  const [showRisk, setShowRisk] = useState(false)

  const fetchDashboard = useCallback(async (): Promise<DashboardData> => {
    const [health, provider, weather, riskMap, observations, patterns] =
      await Promise.all([
        readEndpoint<unknown>('/api/health'),
        readEndpoint<TrafficProvider>('/api/traffic/provider'),
        readEndpoint<CurrentWeather>('/api/weather/current?latitude=24.817&longitude=93.9368'),
        readEndpoint<unknown>('/api/risk/map'),
        readEndpoint<unknown>('/api/risk/observations'),
        readEndpoint<unknown>('/api/risk/patterns'),
      ])

    // Live TomTom traffic is requested only after the browser grants location access.
    return {
      health,
      provider,
      roads: { status: 'empty' },
      weather,
      riskMap,
      observations,
      patterns,
    }
  }, [])

  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      setDashboard(await fetchDashboard())
      setCheckedAt(new Date().toISOString())
    } finally {
      setRefreshing(false)
    }
  }, [fetchDashboard])

  useEffect(() => {
    let cancelled = false
    void fetchDashboard().then((data) => {
      if (!cancelled) {
        setDashboard(data)
        setCheckedAt(new Date().toISOString())
      }
    })
    return () => {
      cancelled = true
    }
  }, [fetchDashboard])

  useEffect(() => {
    const query = searchQuery.trim()
    if (toolMode !== 'search' || !searchFocused || query.length < 2) return

    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void suggestPlaces(query, controller.signal)
        .then((places) => {
          if (controller.signal.aborted) return
          setSearchSuggestions(places)
          setSearchSuggestionState(places.length ? 'results' : 'empty')
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setSearchSuggestionMessage(
            error instanceof Error ? error.message : 'Place suggestions failed.',
          )
          setSearchSuggestionState('error')
        })
    }, 350)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [searchFocused, searchQuery, toolMode])

  useEffect(() => {
    const query = focusedRouteField === 'start' ? startQuery.trim() : endQuery.trim()
    if (toolMode !== 'directions' || !focusedRouteField || query.length < 2) return

    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void suggestPlaces(query, controller.signal)
        .then((places) => {
          if (controller.signal.aborted) return
          setRouteSuggestions(places)
          setRouteSuggestionState(places.length ? 'results' : 'empty')
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setRouteSuggestionMessage(
            error instanceof Error ? error.message : 'Place suggestions failed.',
          )
          setRouteSuggestionState('error')
        })
    }, 350)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [endQuery, focusedRouteField, startQuery, toolMode])

  const runPlaceSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSearchFocused(false)
    setSearchState('loading')
    setSearchMessage('')
    setSearchResults([])
    setLocationTraffic({ status: 'empty' })
    try {
      const places = await searchPlaces(searchQuery)
      setSearchResults(places)
      setSearchState(places.length ? 'results' : 'empty')
    } catch (error) {
      setSearchMessage(error instanceof Error ? error.message : 'Place search failed.')
      setSearchState('error')
    }
  }

  const selectPlace = (place: MapPlace) => {
    setSearchFocused(false)
    setSearchSuggestions([])
    setSearchSuggestionState('idle')
    setSelectedPlace(place)
    setSearchQuery(place.name)
    setSearchResults([])
    setSearchState('idle')
    setLocationTraffic({ status: 'empty' })
    setRoutePreview(null)
  }

  const loadCurrentLocationForSearch = async () => {
    setSearchLocationLoading(true)
    setSearchState('idle')
    setSearchResults([])
    setSelectedPlace(null)
    setRoutePreview(null)
    setLocationTraffic({ status: 'loading' })
    try {
      const place = await getCurrentDeviceLocation()
      setSelectedPlace(place)
      setSearchQuery(place.name)
      setRoutePreview(null)
      try {
        const traffic = await getLiveTrafficAtLocation(place)
        setLocationTraffic({ status: 'available', data: traffic })
      } catch (error) {
        setLocationTraffic({
          status: 'error',
          message: error instanceof Error ? error.message : 'Live traffic at this location is unavailable.',
        })
      }
    } catch (error) {
      setLocationTraffic({
        status: 'error',
        message: error instanceof Error ? error.message : 'Could not find your current location.',
      })
    } finally {
      setSearchLocationLoading(false)
    }
  }

  const setRouteFieldValue = (field: RouteField, place: MapPlace) => {
    setLocationTraffic({ status: 'empty' })
    setFocusedRouteField(null)
    setRouteSuggestions([])
    setRouteSuggestionState('idle')
    if (field === 'start') {
      setRouteStart(place)
      setStartQuery(place.name)
    } else {
      setRouteEnd(place)
      setEndQuery(place.name)
    }
    setRouteCandidates([])
    setRouteSearchState('idle')
    setRouteSearchField(null)
    setRoutePreview(null)
    setRouteError('')
  }

  const findRoutePlace = async (field: RouteField) => {
    const query = field === 'start' ? startQuery : endQuery
    setRouteSearchField(field)
    setRouteSearchState('loading')
    setRouteMessage('')
    setRouteCandidates([])
    try {
      const places = await searchPlaces(query)
      setRouteCandidates(places)
      setRouteSearchState(places.length ? 'results' : 'empty')
    } catch (error) {
      setRouteMessage(error instanceof Error ? error.message : 'Place search failed.')
      setRouteSearchState('error')
    }
  }

  const previewRoute = async () => {
    if (!routeStart || !routeEnd) {
      setRouteError('Find and select both a starting point and a destination.')
      return
    }
    setRouteLoading(true)
    setRouteError('')
    setRoutePreview(null)
    try {
      // Check the browser's saved choice. The browser asks only when undecided.
      await ensureDeviceLocationPermission()
      const route = await getDrivingRoute(routeStart, routeEnd)
      setRoutePreview(route)
      setSelectedPlace(null)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not calculate a route.'
      setRouteError(`Allow browser location access before requesting live traffic. ${message}`)
    } finally {
      setRouteLoading(false)
    }
  }

  const clearRoute = () => {
    setRouteStart(null)
    setRouteEnd(null)
    setStartQuery('')
    setEndQuery('')
    setRouteCandidates([])
    setRouteSearchState('idle')
    setRouteSearchField(null)
    setRoutePreview(null)
    setRouteError('')
    setLocationTraffic({ status: 'empty' })
  }

  const setCurrentLocationAsStart = async () => {
    setDirectionsLocationLoading(true)
    setRouteError('')
    try {
      const place = await getCurrentDeviceLocation()
      setSelectedPlace(place)
      setRouteFieldValue('start', place)
      setToolMode('directions')
    } catch (error) {
      setRouteError(error instanceof Error ? error.message : 'Could not find your current location.')
    } finally {
      setDirectionsLocationLoading(false)
    }
  }

  const handleLocated = (place: MapPlace) => {
    setSelectedPlace(place)
    setLocationTraffic({ status: 'empty' })
    setRouteFieldValue('start', place)
    setToolMode('directions')
  }

  const trafficSegment = locationTraffic.data?.geometry?.coordinates
    ?.map(([longitude, latitude]) => [latitude, longitude] as [number, number]) ?? null

  const pointTrafficDelay = locationTraffic.data?.traffic_delay_seconds
  const pointTrafficDelayLabel = pointTrafficDelay == null
    ? '—'
    : pointTrafficDelay > 0 && pointTrafficDelay < 60
      ? '<1 min'
      : `${Math.max(0, Math.round(pointTrafficDelay / 60))} min`
  const pointTrafficConfidence = locationTraffic.data?.confidence
  const pointTrafficFetchedAt = locationTraffic.data?.fetched_at

  const providerData = dashboard.provider.data
  const weatherData = dashboard.weather.data
  const trafficAvailable = locationTraffic.status === 'available' && Boolean(locationTraffic.data)
  const providerStatus =
    locationTraffic.status === 'available'
      ? 'available'
      : locationTraffic.status === 'error'
        ? 'unavailable'
        : dashboard.provider.status === 'available'
          ? providerData?.status ?? 'status unavailable'
          : dashboard.provider.status
  const providerLabel =
    providerStatus === 'not_configured'
      ? 'Not configured'
      : providerStatus === 'authorization_pending'
        ? 'Waiting for location permission'
        : providerStatus === 'available'
          ? 'Available'
          : providerStatus === 'loading'
            ? 'Checking'
            : 'Unavailable'
  const providerName = locationTraffic.data?.data_source ?? providerData?.provider ?? 'Traffic provider'

  const healthUnavailable =
    dashboard.health.status === 'error' || dashboard.health.status === 'unavailable'
  const healthLabel = healthUnavailable
    ? 'Service unavailable'
    : dashboard.health.status === 'available'
      ? 'Backend connected'
      : dashboard.health.status === 'loading'
        ? 'Connecting to backend'
        : 'Health service returned no status'

  const weatherMetrics: [string, number | null | undefined, string][] = [
    ['Humidity', weatherData?.relative_humidity_pct, '%'],
    ['Precipitation', weatherData?.precipitation_mm, 'mm'],
    ['Wind', weatherData?.wind_speed_kmh, 'km/h'],
  ]

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main" aria-label="Manipur Traffic Risk home">
          <span className="brand-mark" aria-hidden="true">TR</span>
          <span className="brand-copy">
            <strong>MANIPUR TRAFFIC</strong>
            <span>ROAD RISK MONITORING</span>
          </span>
        </a>
        <div className="header-tools">
          <div className={`header-status ${dashboard.health.status}`} aria-live="polite">
            {!healthUnavailable ? <span className="status-light" aria-hidden="true" /> : null}
            <span>{healthLabel}</span>
          </div>
          <button className="header-refresh" type="button" onClick={() => void refresh()} disabled={refreshing}>
            <span aria-hidden="true">{refreshing ? '…' : '↻'}</span>
            <span className="refresh-label">{refreshing ? 'Checking' : 'Refresh'}</span>
          </button>
        </div>
      </header>

      <main id="main" className="map-dashboard">
        <section className="map-workspace" aria-label="Map and navigation tools">
          <aside className="map-sidebar">
            <div className="sidebar-heading">
              <div>
                <span className="eyebrow">MANIPUR · TR-04</span>
                <h1>Explore the map</h1>
              </div>
              <span className="checked-time" title="Last backend check">
                {checkedAt
                  ? new Date(checkedAt).toLocaleTimeString('en-IN', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'Asia/Kolkata',
                  })
                  : '—'}
              </span>
            </div>

            <div className="tool-tabs" role="tablist" aria-label="Map tools">
              <button
                id="search-tab"
                className={toolMode === 'search' ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={toolMode === 'search'}
                aria-controls="map-tool-panel"
                onClick={() => setToolMode('search')}
              >
                <span className="tab-icon" aria-hidden="true">⌕</span>
                Search
              </button>
              <button
                id="directions-tab"
                className={toolMode === 'directions' ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={toolMode === 'directions'}
                aria-controls="map-tool-panel"
                onClick={() => setToolMode('directions')}
              >
                <span className="tab-icon directions-icon" aria-hidden="true">↗</span>
                Directions
              </button>
            </div>

            <div className="tool-panel" id="map-tool-panel" role="tabpanel" aria-labelledby={`${toolMode}-tab`}>
              {toolMode === 'search' ? (
                <>
                  <div className="autocomplete-anchor search-autocomplete-anchor">
                    <form className="place-search-form" onSubmit={(event) => void runPlaceSearch(event)}>
                      <label className="visually-hidden" htmlFor="place-search">Search places in Manipur</label>
                      <span className="search-input-icon" aria-hidden="true">⌕</span>
                      <input
                        id="place-search"
                        type="search"
                        value={searchQuery}
                        onFocus={() => {
                          setSearchFocused(true)
                          setSearchSuggestions([])
                          setSearchSuggestionState(searchQuery.trim().length >= 2 ? 'loading' : 'idle')
                        }}
                        onBlur={() => {
                          setSearchFocused(false)
                          setSearchSuggestionState('idle')
                        }}
                        onChange={(event) => {
                          setSearchQuery(event.target.value)
                          setSearchSuggestions([])
                          setSearchSuggestionState(event.target.value.trim().length >= 2 ? 'loading' : 'idle')
                          setSearchSuggestionMessage('')
                          setSearchResults([])
                          setSearchState('idle')
                          setSearchMessage('')
                          setLocationTraffic({ status: 'empty' })
                        }}
                        onKeyDown={(event) => {
                          if (event.key === 'Escape') {
                            setSearchSuggestions([])
                            setSearchSuggestionState('idle')
                          }
                          if (
                            event.key === 'Enter' &&
                            searchSuggestionState === 'results' &&
                            searchSuggestions[0]
                          ) {
                            event.preventDefault()
                            selectPlace(searchSuggestions[0])
                          }
                          if (event.key === 'ArrowDown' && searchSuggestionState === 'results') {
                            event.preventDefault()
                            document.querySelector<HTMLButtonElement>('#search-place-suggestions button')?.focus()
                          }
                        }}
                        placeholder="Search places in Manipur"
                        autoComplete="off"
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded={searchFocused && searchSuggestionState !== 'idle'}
                        aria-controls="search-place-suggestions"
                      />
                      <button type="submit" disabled={searchState === 'loading'} aria-label="Search places">
                        {searchState === 'loading' ? '…' : 'Search'}
                      </button>
                    </form>
                    <PlaceSuggestions
                      id="search-place-suggestions"
                      places={searchSuggestions}
                      state={searchFocused ? searchSuggestionState : 'idle'}
                      errorMessage={searchSuggestionMessage}
                      onSelect={selectPlace}
                    />
                  </div>
                  <button
                    className="current-location-button"
                    type="button"
                    onClick={() => void loadCurrentLocationForSearch()}
                    disabled={searchLocationLoading}
                  >
                    <span aria-hidden="true">◎</span>
                    {searchLocationLoading ? 'Getting location and traffic…' : 'Use current location'}
                  </button>
                  <p className="service-note">
                    Suggestions use Photon with OpenStreetMap data, focused on Manipur. The browser asks once for location access; your choice is remembered for this site.
                  </p>
                  {searchState === 'loading' ? (
                    <p className="tool-message" role="status">Searching OpenStreetMap…</p>
                  ) : null}
                  {searchState === 'empty' ? (
                    <p className="tool-message">No matching place found. Try a town or landmark with “Imphal” or “Manipur,” such as “Keishampat Junction, Imphal.”</p>
                  ) : null}
                  {searchState === 'error' ? (
                    <p className="tool-message tool-error" role="alert">{searchMessage}</p>
                  ) : null}
                  {searchResults.length > 0 ? (
                    <div className="place-results" aria-label="Place search results">
                      {searchResults.map((place, index) => (
                        <article className="place-result" key={`${place.latitude}-${place.longitude}-${index}`}>
                          <button className="place-result-main" type="button" onClick={() => selectPlace(place)}>
                            <span className="place-pin" aria-hidden="true">●</span>
                            <span>
                              <strong>{place.name}</strong>
                              <small>{place.displayName}</small>
                            </span>
                          </button>
                          <div className="place-result-actions">
                            <button type="button" onClick={() => {
                              setRouteFieldValue('start', place)
                              setToolMode('directions')
                            }}>Route from</button>
                            <button type="button" onClick={() => {
                              setRouteFieldValue('end', place)
                              setToolMode('directions')
                            }}>Route to</button>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : null}
                  {selectedPlace && searchState === 'idle' ? (
                    <div className="selected-place">
                      <span className="place-pin" aria-hidden="true">●</span>
                      <span><strong>{selectedPlace.name}</strong><small>{selectedPlace.displayName}</small></span>
                      <button type="button" onClick={() => {
                        setRouteFieldValue('end', selectedPlace)
                        setToolMode('directions')
                      }}>Directions</button>
                    </div>
                  ) : null}
                  {locationTraffic.status === 'loading' ? (
                    <p className="tool-message" role="status">Loading live traffic for the nearest road…</p>
                  ) : null}
                  {locationTraffic.status === 'error' ? (
                    <p className="tool-message tool-error" role="alert">{locationTraffic.message}</p>
                  ) : null}
                  {locationTraffic.status === 'available' && locationTraffic.data ? (
                    <section className="location-traffic-card" aria-label="Live traffic near current location">
                      <div className="location-traffic-heading">
                        <span><strong>Live traffic near you</strong><small>Nearest road segment · {locationTraffic.data.data_source}</small></span>
                        <span className={`traffic-condition${locationTraffic.data.road_closure ? ' is-closed' : ''}`}>
                          {locationTraffic.data.road_closure ? 'Closed' : 'Live'}
                        </span>
                      </div>
                      <div className="location-traffic-metrics">
                        <span><small>Current speed</small><strong>{locationTraffic.data.current_speed_kmh.toFixed(0)} <em>km/h</em></strong></span>
                        <span><small>Free-flow speed</small><strong>{locationTraffic.data.free_flow_speed_kmh.toFixed(0)} <em>km/h</em></strong></span>
                        <span><small>Extra delay</small><strong>{pointTrafficDelayLabel}</strong></span>
                        <span><small>Confidence</small><strong>{pointTrafficConfidence == null ? '—' : `${Math.round(pointTrafficConfidence * 100)}%`}</strong></span>
                      </div>
                      <p className="location-traffic-updated">
                        {pointTrafficFetchedAt ? `Updated ${formatWeatherTime(pointTrafficFetchedAt)}` : 'Update time unavailable'}
                      </p>
                    </section>
                  ) : null}
                </>
              ) : (
                <>
                  <div className="directions-fields">
                    <div className="route-waypoints" aria-hidden="true">
                      <span className="waypoint-dot start-dot" />
                      <span className="waypoint-line" />
                      <span className="waypoint-dot end-dot" />
                    </div>
                    <div className="autocomplete-anchor route-autocomplete-anchor">
                      <label className="route-field">
                        <span className="visually-hidden">Starting point</span>
                        <input
                          value={startQuery}
                          onFocus={() => {
                            setFocusedRouteField('start')
                            setRouteSuggestions([])
                            setRouteSuggestionState(startQuery.trim().length >= 2 ? 'loading' : 'idle')
                          }}
                          onBlur={() => {
                            setFocusedRouteField(null)
                            setRouteSuggestionState('idle')
                          }}
                          onChange={(event) => {
                            setStartQuery(event.target.value)
                            setRouteSuggestions([])
                            setRouteSuggestionState(event.target.value.trim().length >= 2 ? 'loading' : 'idle')
                            setRouteSuggestionMessage('')
                            setRouteStart(null)
                            setRouteCandidates([])
                            setRouteSearchState('idle')
                            setRoutePreview(null)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Escape') {
                              setRouteSuggestions([])
                              setRouteSuggestionState('idle')
                            }
                            if (
                              event.key === 'Enter' &&
                              focusedRouteField === 'start' &&
                              routeSuggestionState === 'results' &&
                              routeSuggestions[0]
                            ) {
                              event.preventDefault()
                              setRouteFieldValue('start', routeSuggestions[0])
                            }
                            if (event.key === 'ArrowDown' && routeSuggestionState === 'results') {
                              event.preventDefault()
                              document.querySelector<HTMLButtonElement>('#start-place-suggestions button')?.focus()
                            }
                          }}
                          placeholder="Choose starting point"
                          autoComplete="off"
                          role="combobox"
                          aria-autocomplete="list"
                          aria-expanded={focusedRouteField === 'start' && routeSuggestionState !== 'idle'}
                          aria-controls="start-place-suggestions"
                        />
                        <button type="button" onClick={() => void findRoutePlace('start')} disabled={routeSearchState === 'loading'}>Find</button>
                      </label>
                      <PlaceSuggestions
                        id="start-place-suggestions"
                        places={focusedRouteField === 'start' ? routeSuggestions : []}
                        state={focusedRouteField === 'start' ? routeSuggestionState : 'idle'}
                        errorMessage={routeSuggestionMessage}
                        onSelect={(place) => setRouteFieldValue('start', place)}
                      />
                    </div>
                    <div className="autocomplete-anchor route-autocomplete-anchor">
                      <label className="route-field">
                        <span className="visually-hidden">Destination</span>
                        <input
                          value={endQuery}
                          onFocus={() => {
                            setFocusedRouteField('end')
                            setRouteSuggestions([])
                            setRouteSuggestionState(endQuery.trim().length >= 2 ? 'loading' : 'idle')
                          }}
                          onBlur={() => {
                            setFocusedRouteField(null)
                            setRouteSuggestionState('idle')
                          }}
                          onChange={(event) => {
                            setEndQuery(event.target.value)
                            setRouteSuggestions([])
                            setRouteSuggestionState(event.target.value.trim().length >= 2 ? 'loading' : 'idle')
                            setRouteSuggestionMessage('')
                            setRouteEnd(null)
                            setRouteCandidates([])
                            setRouteSearchState('idle')
                            setRoutePreview(null)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Escape') {
                              setRouteSuggestions([])
                              setRouteSuggestionState('idle')
                            }
                            if (
                              event.key === 'Enter' &&
                              focusedRouteField === 'end' &&
                              routeSuggestionState === 'results' &&
                              routeSuggestions[0]
                            ) {
                              event.preventDefault()
                              setRouteFieldValue('end', routeSuggestions[0])
                            }
                            if (event.key === 'ArrowDown' && routeSuggestionState === 'results') {
                              event.preventDefault()
                              document.querySelector<HTMLButtonElement>('#end-place-suggestions button')?.focus()
                            }
                          }}
                          placeholder="Choose destination"
                          autoComplete="off"
                          role="combobox"
                          aria-autocomplete="list"
                          aria-expanded={focusedRouteField === 'end' && routeSuggestionState !== 'idle'}
                          aria-controls="end-place-suggestions"
                        />
                        <button type="button" onClick={() => void findRoutePlace('end')} disabled={routeSearchState === 'loading'}>Find</button>
                      </label>
                      <PlaceSuggestions
                        id="end-place-suggestions"
                        places={focusedRouteField === 'end' ? routeSuggestions : []}
                        state={focusedRouteField === 'end' ? routeSuggestionState : 'idle'}
                        errorMessage={routeSuggestionMessage}
                        onSelect={(place) => setRouteFieldValue('end', place)}
                      />
                    </div>
                  </div>
                  <button
                    className="current-location-button directions-location-button"
                    type="button"
                    onClick={() => void setCurrentLocationAsStart()}
                    disabled={directionsLocationLoading}
                  >
                    <span aria-hidden="true">◎</span>
                    {directionsLocationLoading ? 'Getting current location…' : 'Use current location as starting point'}
                  </button>
                  {routeSearchState === 'loading' ? (
                    <p className="tool-message" role="status">Finding places…</p>
                  ) : null}
                  {routeSearchState === 'empty' ? (
                    <p className="tool-message">No matching place found. Try adding “Imphal” or “Manipur” to the place name.</p>
                  ) : null}
                  {routeSearchState === 'error' ? (
                    <p className="tool-message tool-error" role="alert">{routeMessage}</p>
                  ) : null}
                  {routeSearchField && routeCandidates.length > 0 ? (
                    <div className="place-results route-candidates" aria-label="Choose a route location">
                      {routeCandidates.map((place, index) => (
                        <button
                          className="candidate-button"
                          key={`${place.latitude}-${place.longitude}-${index}`}
                          type="button"
                          onClick={() => setRouteFieldValue(routeSearchField, place)}
                        >
                          <strong>{place.name}</strong>
                          <small>{place.displayName}</small>
                        </button>
                      ))}
                    </div>
                  ) : null}
                  <div className="route-actions">
                    <button className="route-submit" type="button" onClick={() => void previewRoute()} disabled={routeLoading}>
                      {routeLoading ? 'Finding route…' : 'Preview driving route'}
                    </button>
                    <button className="route-clear" type="button" onClick={clearRoute}>Clear</button>
                  </div>
                  {routeError ? <p className="tool-message tool-error" role="alert">{routeError}</p> : null}
                  {routePreview ? (
                    <div className="route-summary" aria-live="polite">
                      <strong>{routePreview.distanceKm.toFixed(1)} km</strong>
                      <span>about {Math.max(1, Math.round(routePreview.durationMinutes))} min</span>
                      <small>
                        {routePreview.trafficAdjusted
                          ? `${routePreview.source} live traffic${routePreview.trafficDelayMinutes === null ? '' : ` · ${Math.round(routePreview.trafficDelayMinutes)} min delay`}`
                          : `${routePreview.source} estimate · not live traffic-adjusted`}
                      </small>
                      {routePreview.fallbackMessage ? (
                        <small className="route-fallback-note">
                          Live route unavailable: {routePreview.fallbackMessage}
                        </small>
                      ) : null}
                    </div>
                  ) : null}
                  <p className="service-note">
                    Your browser asks once for location access before the first live route
                    request. Select both points, then preview; unavailable live routes use an OSRM estimate.
                  </p>
                </>
              )}
            </div>

            <section className="sidebar-data" aria-label="Traffic and weather status">
              <div className="traffic-source-row">
                <span className="source-symbol" aria-hidden="true">↗</span>
                <span className="source-copy">
                  <strong>Traffic</strong>
                  <small>{providerName} · {providerLabel}</small>
                </span>
                <span
                  className={`status-indicator ${trafficAvailable ? 'available' : 'unavailable'}`}
                  aria-label={trafficAvailable ? 'Live traffic available' : 'Traffic unavailable'}
                />
              </div>
              {trafficAvailable && locationTraffic.data ? (
                <p className="source-explanation">
                  Nearest road at selected location
                  {` · ${locationTraffic.data.current_speed_kmh.toFixed(0)} km/h`}
                  {locationTraffic.data.traffic_delay_seconds == null
                    ? ''
                    : ` · ${Math.round(locationTraffic.data.traffic_delay_seconds / 60)} min delay`}
                </p>
              ) : (
                <p className="source-explanation source-error">
                  {providerStatus === 'not_configured'
                    ? 'Configure a TomTom key on the backend to enable live traffic.'
                    : locationTraffic.status === 'error'
                      ? locationTraffic.message
                      : locationTraffic.status === 'loading'
                        ? 'Checking live traffic for your location…'
                        : 'Use current location to request live traffic. The browser will ask for permission first.'}
                </p>
              )}
              <div className="weather-sidecard">
                <div className="weather-side-heading">
                  <span className="weather-symbol" aria-hidden="true">◌</span>
                  <span><strong>Imphal weather</strong><small>Model estimate</small></span>
                  {weatherData?.temperature_c != null ? (
                    <strong className="weather-temperature">{weatherData.temperature_c}°</strong>
                  ) : null}
                </div>
                {dashboard.weather.status === 'available' && weatherData ? (
                  <>
                    <div className="weather-quick-metrics">
                      {weatherMetrics
                        .filter(([, value]) => value !== null && value !== undefined)
                        .map(([label, value, unit]) => (
                          <span key={label}><small>{label}</small><strong>{value}{unit}</strong></span>
                        ))}
                    </div>
                    <p className="weather-update">
                      {weatherData.provider ?? 'Open-Meteo'} estimate
                      {weatherData.valid_at
                        ? ` · valid ${formatWeatherTime(weatherData.valid_at)}`
                        : ''}
                      {weatherData.fetched_at
                        ? ` · fetched ${formatWeatherTime(weatherData.fetched_at)}`
                        : ''}
                    </p>
                  </>
                ) : dashboard.weather.status === 'loading' ? (
                  <p className="weather-update">Loading estimate…</p>
                ) : dashboard.weather.status === 'error' || dashboard.weather.status === 'unavailable' ? (
                  <p className="weather-update source-error">{weatherData?.message ?? dashboard.weather.message}</p>
                ) : (
                  <p className="weather-update">No current conditions returned.</p>
                )}
              </div>
              <p className="service-note sidebar-service-note">
                Place search uses OpenStreetMap. Live traffic uses TomTom when enabled; route previews may fall back to an OSRM estimate.
              </p>
            </section>
          </aside>

          <section className="map-area" aria-label="Imphal road map">
            <div className="map-location-bar">
              <span className="map-location-symbol" aria-hidden="true">⌖</span>
              <span>
                <strong>{routePreview ? 'Route preview' : routeStart ? routeStart.name : selectedPlace?.name ?? 'Imphal'}</strong>
                <small>
                  {routePreview
                    ? `${routeStart?.name ?? 'Start'} → ${routeEnd?.name ?? 'Destination'}`
                    : routeStart
                      ? 'Starting point selected'
                      : selectedPlace?.displayName ?? 'Manipur, India'}
                </small>
              </span>
              <span className="map-layer-note">
                {showRisk ? 'Recorded risk layer' : 'OpenStreetMap'}
              </span>
            </div>
            <MapView
              state={dashboard.riskMap}
              selectedPlace={selectedPlace}
              routeStart={routeStart}
              routeEnd={routeEnd}
              route={routePreview}
              trafficSegment={trafficSegment}
              showRisk={showRisk}
              onToggleRisk={() => setShowRisk((visible) => !visible)}
              onLocated={handleLocated}
            />
          </section>
        </section>

        <section className="records-section" aria-label="Road risk records">
          <div className="records-heading">
            <div>
              <span className="eyebrow">TR-04 DATA</span>
              <h2>Recorded road risk</h2>
            </div>
            <p>Risk is an explainable backend baseline, not a trained AI prediction.</p>
          </div>
          <div className="records-grid">
            <section className="record-panel" aria-labelledby="observations-title">
              <div className="record-title">
                <h3 id="observations-title">Observations</h3>
                <span>Backend records</span>
              </div>
              <RecordTable
                state={dashboard.observations}
                keys={['observations', 'items', 'data']}
                emptyMessage="No risk observations have been recorded."
              />
            </section>
            <section className="record-panel" aria-labelledby="patterns-title">
              <div className="record-title">
                <h3 id="patterns-title">Recurring patterns</h3>
                <span>Backend analysis</span>
              </div>
              <RecordTable
                state={dashboard.patterns}
                keys={['patterns', 'items', 'data']}
                emptyMessage="No recurring risk patterns have been returned."
              />
            </section>
          </div>
        </section>
      </main>
      <footer className="page-footer">
        <span>TR-04 · Manipur road risk monitoring</span>
        <span>Search and route services are public OpenStreetMap community services.</span>
      </footer>
    </div>
  )
}

export default App
