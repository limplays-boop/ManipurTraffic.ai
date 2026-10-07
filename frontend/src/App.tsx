import { useEffect, useState } from 'react'
import './App.css'
import MapView from './MapView'

type TrafficData = {
  city: string
  traffic_level: string
  risk_score: number
}

type TrafficSummary = {
  total_roads: number
  critical_roads: number
  heavy_roads: number
  moderate_roads: number
  clear_roads: number
  average_risk_score: number
  timestamp: string
}

function formatTimestamp(timestamp: string | undefined): string {
  if (!timestamp) {
    return 'Waiting for update...'
  }

  const date = new Date(timestamp)

  if (Number.isNaN(date.getTime())) {
    return 'Waiting for update...'
  }

  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function App() {
  const [traffic, setTraffic] = useState<TrafficData | null>(null)

  const [summary, setSummary] = useState<TrafficSummary | null>(null)

  const [backendError, setBackendError] = useState(false)

  useEffect(() => {
    const fetchTrafficData = async () => {
      try {
        setBackendError(false)

        // Get overall traffic information
        const trafficResponse = await fetch(
          'http://127.0.0.1:8000/api/traffic'
        )

        if (!trafficResponse.ok) {
          throw new Error(
            `Traffic API failed: ${trafficResponse.status}`
          )
        }

        const trafficData: TrafficData = await trafficResponse.json()

        setTraffic(trafficData)

        // Get traffic summary
        const summaryResponse = await fetch(
          'http://127.0.0.1:8000/api/traffic/summary'
        )

        if (!summaryResponse.ok) {
          throw new Error(
            `Traffic summary API failed: ${summaryResponse.status}`
          )
        }

        const summaryData: TrafficSummary =
          await summaryResponse.json()

        setSummary(summaryData)

        console.log('Traffic data:', trafficData)
        console.log('Traffic summary:', summaryData)
        console.log('Timestamp received:', summaryData.timestamp)
      } catch (error) {
        console.error(
          'Failed to fetch traffic data:',
          error
        )

        setBackendError(true)
      }
    }

    // Fetch immediately when dashboard loads
    fetchTrafficData()

    // Refresh every 30 seconds
    const interval = window.setInterval(() => {
      fetchTrafficData()
    }, 30000)

    // Clean up the timer
    return () => {
      window.clearInterval(interval)
    }
  }, [])

  const lastUpdated = formatTimestamp(
    summary?.timestamp
  )

  return (
    <div className="app">

      {/* Header */}
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-icon">🚦</span>
            <span>MANIPUR TRAFFIC AI</span>
          </div>

          <p className="subtitle">
            AI-powered traffic intelligence and management system
          </p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>
      </header>

      {/* Main dashboard */}
      <main className="dashboard">

        {/* Backend connection / data status */}
        <div
          style={{
            padding: '15px',
            marginBottom: '20px',
            borderRadius: '12px',
            background: '#111d31',
            border: '1px solid #283753',
          }}
        >
          {backendError ? (
            <>
              <strong>🔴 Backend Connection Error</strong>

              <p>
                Unable to retrieve traffic data from FastAPI.
              </p>

              <p>
                Make sure the backend is running on:
                <br />
                http://127.0.0.1:8000
              </p>
            </>
          ) : traffic ? (
            <>
              <strong>🟢 Backend Connected</strong>

              <p>
                City: {traffic.city}
              </p>

              <p>
                Traffic: {traffic.traffic_level}
              </p>

              <p>
                Risk Score: {traffic.risk_score}/100
              </p>

              <p>
                Last updated: {lastUpdated}
              </p>
            </>
          ) : (
            <strong>
              🟡 Connecting to traffic backend...
            </strong>
          )}
        </div>

        {/* Summary cards */}
        <section className="stats-grid">

          <div className="stat-card critical">
            <span className="stat-label">
              CRITICAL ROADS
            </span>

            <strong>
              {summary
                ? summary.critical_roads
                : '-'}
            </strong>

            <span className="stat-info">
              Immediate attention
            </span>
          </div>

          <div className="stat-card heavy">
            <span className="stat-label">
              HEAVY TRAFFIC
            </span>

            <strong>
              {summary
                ? summary.heavy_roads
                : '-'}
            </strong>

            <span className="stat-info">
              Congestion detected
            </span>
          </div>

          <div className="stat-card clear">
            <span className="stat-label">
              CLEAR ROADS
            </span>

            <strong>
              {summary
                ? summary.clear_roads
                : '-'}
            </strong>

            <span className="stat-info">
              Normal traffic flow
            </span>
          </div>

          <div className="stat-card ai">
            <span className="stat-label">
              AI RISK SCORE
            </span>

            <strong>
              {summary
                ? summary.average_risk_score
                : '-'}
            </strong>

            <span className="stat-info">
              Average network risk
            </span>
          </div>

        </section>

        {/* Main content */}
        <section className="content-grid">

          {/* Map */}
          <div className="panel map-panel">

            <div className="panel-header">
              <div>
                <h2>Live Traffic Map</h2>
                <p>Imphal, Manipur</p>
              </div>

              <span className="live-badge">
                ● LIVE
              </span>
            </div>

            <div className="map">
              <MapView />
            </div>

            <div className="legend">

              <span>
                <i className="legend-dot clear-dot"></i>
                Clear
              </span>

              <span>
                <i className="legend-dot moderate-dot"></i>
                Moderate
              </span>

              <span>
                <i className="legend-dot heavy-dot"></i>
                Heavy
              </span>

              <span>
                <i className="legend-dot critical-dot"></i>
                Critical
              </span>

            </div>
          </div>

          {/* AI alerts */}
          <div className="panel alerts-panel">

            <div className="panel-header">
              <div>
                <h2>AI Alerts</h2>
                <p>Real-time intelligence</p>
              </div>

              <span className="alert-count">
                4
              </span>
            </div>

            <div className="alert-list">

              <div className="alert-item critical-alert">
                <div className="alert-icon">
                  ⚠️
                </div>

                <div>
                  <h3>
                    Critical congestion
                  </h3>

                  <p>
                    Keishampat junction
                  </p>

                  <small>
                    2 minutes ago
                  </small>
                </div>
              </div>

              <div className="alert-item warning-alert">
                <div className="alert-icon">
                  🚗
                </div>

                <div>
                  <h3>
                    Traffic increasing
                  </h3>

                  <p>
                    Thangal Bazar
                  </p>

                  <small>
                    5 minutes ago
                  </small>
                </div>
              </div>

              <div className="alert-item weather-alert">
                <div className="alert-icon">
                  🌧️
                </div>

                <div>
                  <h3>
                    Weather risk detected
                  </h3>

                  <p>
                    Heavy rainfall possible
                  </p>

                  <small>
                    8 minutes ago
                  </small>
                </div>
              </div>

              <div className="alert-item info-alert">
                <div className="alert-icon">
                  🚑
                </div>

                <div>
                  <h3>
                    Emergency vehicle
                  </h3>

                  <p>
                    Priority route requested
                  </p>

                  <small>
                    11 minutes ago
                  </small>
                </div>
              </div>

            </div>
          </div>

        </section>

        {/* Prediction section */}
        <section className="bottom-grid">

          <div className="panel prediction-panel">

            <div className="panel-header">
              <div>
                <h2>
                  AI Traffic Prediction
                </h2>

                <p>
                  Expected congestion over the next 30 minutes
                </p>
              </div>
            </div>

            <div className="prediction-list">

              <div className="prediction-row">
                <div>
                  <strong>
                    Keishampat
                  </strong>

                  <span>
                    Critical congestion
                  </span>
                </div>

                <div className="prediction-value critical-text">
                  89%
                </div>
              </div>

              <div className="prediction-row">
                <div>
                  <strong>
                    Thangal Bazar
                  </strong>

                  <span>
                    Heavy congestion
                  </span>
                </div>

                <div className="prediction-value heavy-text">
                  74%
                </div>
              </div>

              <div className="prediction-row">
                <div>
                  <strong>
                    Nagamapal
                  </strong>

                  <span>
                    Moderate congestion
                  </span>
                </div>

                <div className="prediction-value moderate-text">
                  61%
                </div>
              </div>

              <div className="prediction-row">
                <div>
                  <strong>
                    Paona Bazar
                  </strong>

                  <span>
                    Stable traffic
                  </span>
                </div>

                <div className="prediction-value clear-text">
                  28%
                </div>
              </div>

            </div>
          </div>

          {/* AI recommendation */}
          <div className="panel recommendation-panel">

            <div className="panel-header">
              <div>
                <h2>
                  🤖 AI Recommendation
                </h2>

                <p>
                  Suggested traffic action
                </p>
              </div>
            </div>

            <div className="recommendation">

              <div className="recommendation-score">
                91
              </div>

              <div>

                <h3>
                  Divert eastbound traffic
                </h3>

                <p>
                  AI predicts severe congestion at
                  Keishampat within the next 20 minutes.
                </p>

                <button>
                  View recommendation
                </button>

              </div>

            </div>
          </div>

        </section>
      </main>
    </div>
  )
}

export default App