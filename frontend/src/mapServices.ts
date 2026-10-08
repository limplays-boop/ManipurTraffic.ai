import { apiGet, apiPost } from './api'

export type MapPlace = {
  name: string
  displayName: string
  latitude: number
  longitude: number
}

export type RoutePreview = {
  coordinates: [number, number][]
  distanceKm: number
  durationMinutes: number
  source: string
  trafficAdjusted: boolean
  trafficDelayMinutes: number | null
  fallbackMessage?: string
}

export type LocationTraffic = {
  status: string
  data_source: string
  latitude: number
  longitude: number
  current_speed_kmh: number
  free_flow_speed_kmh: number
  current_travel_time_seconds: number
  free_flow_travel_time_seconds: number
  traffic_delay_seconds: number
  confidence: number
  road_closure: boolean
  geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  } | null
  fetched_at: string
}

type NominatimResult = {
  place_id: number
  display_name: string
  lat: string
  lon: string
  name?: string
}

type PhotonFeatureCollection = {
  features?: {
    geometry?: {
      type?: string
      coordinates?: unknown
    }
    properties?: Record<string, unknown>
  }[]
}

const MANIPUR_SEARCH_BBOX = '92.8,23.6,94.9,25.8'
let lastGeocodeRequestAt = 0

export function getCurrentDeviceLocation(): Promise<MapPlace> {
  const geolocation = typeof navigator === 'undefined' ? undefined : navigator.geolocation
  if (!geolocation) {
    return Promise.reject(new Error('Location is not supported by this browser.'))
  }

  return new Promise((resolve, reject) => {
    geolocation.getCurrentPosition(
      ({ coords }) => resolve({
        name: 'My location',
        displayName: 'Your current device location',
        latitude: coords.latitude,
        longitude: coords.longitude,
      }),
      (error) => {
        const message = error.code === error.PERMISSION_DENIED
          ? 'Allow location access in your browser to use this feature.'
          : error.code === error.POSITION_UNAVAILABLE
            ? 'Your current location could not be determined.'
            : 'Location lookup timed out. Please try again.'
        reject(new Error(message))
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  })
}

export async function ensureDeviceLocationPermission(): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    throw new Error('Location is not supported by this browser.')
  }

  let permissionState: PermissionState | null = null
  if (navigator.permissions?.query) {
    try {
      permissionState = (await navigator.permissions.query({ name: 'geolocation' })).state
    } catch {
      // Fall back to the browser's geolocation request if permission queries are unsupported.
    }
  }

  if (permissionState === 'granted') return
  if (permissionState === 'denied') {
    throw new Error('Location access is blocked for this site. Enable it in your browser settings.')
  }
  await getCurrentDeviceLocation()
}

export function getLiveTrafficAtLocation(place: MapPlace): Promise<LocationTraffic> {
  const query = new URLSearchParams({
    latitude: String(place.latitude),
    longitude: String(place.longitude),
  })
  return apiGet<LocationTraffic>(`/api/traffic/location?${query.toString()}`)
}

async function waitForGeocoderSlot(): Promise<void> {
  const wait = Math.max(0, 1100 - (Date.now() - lastGeocodeRequestAt))
  if (wait > 0) {
    await new Promise((resolve) => window.setTimeout(resolve, wait))
  }
  lastGeocodeRequestAt = Date.now()
}

export async function suggestPlaces(
  query: string,
  signal: AbortSignal,
  limit = 6,
): Promise<MapPlace[]> {
  const cleanQuery = query.trim()
  if (cleanQuery.length < 2) return []

  try {
    return await requestPhotonPlaces(cleanQuery, limit, signal)
  } catch (error) {
    if (signal.aborted) return []
    throw error
  }
}

async function requestPhotonPlaces(
  query: string,
  limit: number,
  signal?: AbortSignal,
): Promise<MapPlace[]> {
  const url = new URL('https://photon.komoot.io/api/')
  url.search = new URLSearchParams({
    q: query,
    limit: String(limit),
    lang: 'en',
    bbox: MANIPUR_SEARCH_BBOX,
    countrycode: 'IN',
    lon: '93.9368',
    lat: '24.8170',
    zoom: '8',
    location_bias_scale: '0.2',
  }).toString()

  let response: Response
  try {
    response = await fetch(url, {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch {
    if (signal?.aborted) return []
    throw new Error('Could not reach the place search service. Check your connection and try again.')
  }

  if (!response.ok) {
    throw new Error(`Place search returned HTTP ${response.status}.`)
  }

  let result: PhotonFeatureCollection
  try {
    result = await response.json() as PhotonFeatureCollection
  } catch {
    throw new Error('Place search returned an invalid response.')
  }

  if (!Array.isArray(result.features)) {
    throw new Error('Place search returned an unexpected response.')
  }

  return result.features.flatMap((feature) => {
    const coordinates = feature.geometry?.coordinates
    const properties = feature.properties
    if (!Array.isArray(coordinates) || !properties) return []

    const longitude = Number(coordinates[0])
    const latitude = Number(coordinates[1])
    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180
    ) return []

    if (typeof properties.state === 'string' && !/\bmanipur\b/i.test(properties.state)) return []

    const name = String(
      properties.name ?? properties.street ?? properties.locality ?? properties.city ?? '',
    ).trim()
    if (!name) return []

    const context = [
      properties.street,
      properties.housenumber,
      properties.suburb,
      properties.neighbourhood,
      properties.district,
      properties.city,
      properties.locality,
      properties.county,
      properties.state,
      properties.country,
      properties.postcode,
    ]
      .filter((part): part is string => typeof part === 'string' && part.trim().length > 0)
      .map((part) => part.trim())
      .filter((part, index, parts) => part !== name && parts.indexOf(part) === index)

    return [{
      name,
      displayName: [name, ...context].join(', '),
      latitude,
      longitude,
    }]
  })
}

export async function searchPlaces(query: string, limit = 5): Promise<MapPlace[]> {
  const cleanQuery = query.trim()
  if (cleanQuery.length < 3) {
    throw new Error('Enter at least 3 characters to search for a place.')
  }

  let photonError: unknown
  try {
    const photonResults = await requestPhotonPlaces(cleanQuery, limit)
    if (photonResults.length > 0) return photonResults
  } catch (error) {
    photonError = error
  }

  const queryWithoutCountry = cleanQuery.replace(/\s*,?\s*India\s*$/i, '')
  const queries = [queryWithoutCountry]
  if (!/\bmanipur\b/i.test(queryWithoutCountry)) {
    queries.push(`${queryWithoutCountry}, Manipur, India`)
  }

  let nominatimError: unknown
  for (const localizedQuery of queries) {
    await waitForGeocoderSlot()
    const url = new URL('https://nominatim.openstreetmap.org/search')
    url.search = new URLSearchParams({
      q: localizedQuery,
      format: 'jsonv2',
      addressdetails: '1',
      countrycodes: 'in',
      viewbox: '92.8,25.8,94.9,23.6',
      bounded: '1',
      limit: String(limit),
    }).toString()

    try {
      const response = await fetch(url, { headers: { Accept: 'application/json' } })
      if (!response.ok) {
        throw new Error(`OpenStreetMap place search returned HTTP ${response.status}.`)
      }

      const results = await response.json() as NominatimResult[]
      if (!Array.isArray(results)) {
        throw new Error('OpenStreetMap place search returned an unexpected response.')
      }

      const places = results.flatMap((result) => {
        const latitude = Number(result.lat)
        const longitude = Number(result.lon)
        if (
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude) ||
          latitude < -90 ||
          latitude > 90 ||
          longitude < -180 ||
          longitude > 180
        ) return []

        return [{
          name: result.name?.trim() || result.display_name.split(',')[0] || 'Unnamed place',
          displayName: result.display_name,
          latitude,
          longitude,
        }]
      })
      if (places.length > 0) return places
    } catch (error) {
      nominatimError = error
    }
  }

  if (nominatimError && photonError) {
    throw new Error('Both place search services are unavailable. Please try again later.')
  }
  if (nominatimError) throw nominatimError
  if (photonError) throw photonError
  return []
}

type OsrmResponse = {
  code: string
  message?: string
  routes?: {
    distance: number
    duration: number
    geometry: {
      coordinates: [number, number][]
    }
  }[]
}

type LiveRouteResponse = {
  status: string
  data_source: string
  distance_meters: number
  travel_duration_seconds: number
  traffic_delay_seconds: number | null
  geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  }
}

export async function getDrivingRoute(
  start: MapPlace,
  end: MapPlace,
): Promise<RoutePreview> {
  let liveTrafficFailure = 'Live traffic routing is unavailable.'
  try {
    const route = await apiPost<LiveRouteResponse>('/api/traffic/route', {
      origin_latitude: start.latitude,
      origin_longitude: start.longitude,
      destination_latitude: end.latitude,
      destination_longitude: end.longitude,
    })
    const points = route.geometry?.coordinates
    if (route.status !== 'available' || !Array.isArray(points) || points.length < 2) {
      throw new Error('The traffic provider returned no usable live route geometry.')
    }
    return {
      coordinates: points.flatMap(([longitude, latitude]) => {
        if (
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude) ||
          latitude < -90 ||
          latitude > 90 ||
          longitude < -180 ||
          longitude > 180
        ) return []
        return [[latitude, longitude] as [number, number]]
      }),
      distanceKm: route.distance_meters / 1000,
      durationMinutes: route.travel_duration_seconds / 60,
      source: route.data_source,
      trafficAdjusted: true,
      trafficDelayMinutes: route.traffic_delay_seconds === null
        ? null
        : route.traffic_delay_seconds / 60,
    }
  } catch (error) {
    liveTrafficFailure = error instanceof Error ? error.message : liveTrafficFailure
  }

  const fallback = await getOsrmDrivingRoute(start, end)
  return { ...fallback, fallbackMessage: liveTrafficFailure }
}

async function getOsrmDrivingRoute(
  start: MapPlace,
  end: MapPlace,
): Promise<RoutePreview> {
  const coordinates =
    `${start.longitude},${start.latitude};${end.longitude},${end.latitude}`
  const url = new URL(`https://router.project-osrm.org/route/v1/driving/${coordinates}`)
  url.search = new URLSearchParams({
    overview: 'full',
    geometries: 'geojson',
    steps: 'false',
  }).toString()

  let response: Response
  try {
    response = await fetch(url, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new Error('Could not reach the public route service. Check your connection and try again.')
  }

  if (!response.ok) {
    throw new Error(`The public route service returned HTTP ${response.status}.`)
  }

  let result: OsrmResponse
  try {
    result = await response.json() as OsrmResponse
  } catch {
    throw new Error('The public route service returned an invalid response.')
  }

  const route = result.routes?.[0]
  if (result.code !== 'Ok' || !route) {
    throw new Error(result.message ?? 'No driving route was found between those places.')
  }

  const points = route.geometry.coordinates
  if (!Array.isArray(points) || points.length < 2) {
    throw new Error('The route service returned no usable route geometry.')
  }

  return {
    coordinates: points.flatMap(([longitude, latitude]) => {
      if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
      ) return []
      return [[latitude, longitude] as [number, number]]
    }),
    distanceKm: route.distance / 1000,
    durationMinutes: route.duration / 60,
    source: 'OSRM',
    trafficAdjusted: false,
    trafficDelayMinutes: null,
  }
}
