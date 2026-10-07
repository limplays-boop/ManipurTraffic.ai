import { useEffect, useState } from 'react'
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

type TrafficStatus = 'clear' | 'moderate' | 'heavy' | 'critical'

type TrafficPoint = {
  name: string
  latitude: number
  longitude: number
  status: TrafficStatus
  average_speed: number
  vehicles: number
  risk_score: number
}

type TrafficResponse = {
  city: string
  data_source: string
  roads: TrafficPoint[]
}

function getTrafficColor(status: TrafficStatus) {
  switch (status) {
    case 'clear':
      return '#22c55e'
    case 'moderate':
      return '#facc15'
    case 'heavy':
      return '#f97316'
    case 'critical':
      return '#ef4444'
  }
}

function MapView() {
  const [trafficPoints, setTrafficPoints] = useState<TrafficPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/traffic/roads')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch traffic data')
        }

        return response.json()
      })
      .then((data: TrafficResponse) => {
        setTrafficPoints(data.roads)
        setLoading(false)
      })
      .catch((error) => {
        console.error('Traffic API error:', error)
        setError(true)
        setLoading(false)
      })
  }, [])

  return (
    <MapContainer
      center={[24.817, 93.9368]}
      zoom={14}
      scrollWheelZoom={true}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Central Imphal monitoring point */}
      <Marker position={[24.817, 93.9368]}>
        <Popup>
          <strong>Manipur Traffic AI</strong>
          <br />
          Central Imphal monitoring area
        </Popup>
      </Marker>

      {/* Loading message */}
      {loading && (
        <div className="map-status">
          Loading traffic data...
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="map-status">
          Unable to load traffic data.
        </div>
      )}

      {/* Traffic points from FastAPI */}
      {trafficPoints.map((point) => {
        const color = getTrafficColor(point.status)

        return (
          <CircleMarker
            key={point.name}
            center={[point.latitude, point.longitude]}
            radius={12}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.75,
            }}
          >
            <Popup>
              <strong>{point.name}</strong>
              <br />
              Traffic: {point.status.toUpperCase()}
              <br />
              Average speed: {point.average_speed} km/h
              <br />
              Vehicles detected: {point.vehicles}
              <br />
              Risk score: {point.risk_score}/100
            </Popup>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}

export default MapView