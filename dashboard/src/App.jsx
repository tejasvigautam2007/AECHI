import { useState, useEffect, useCallback } from 'react'
import StatsBar from './components/StatsBar'
import AlertFeed from './components/AlertFeed'
import EventTable from './components/EventTable'
import SeverityChart from './components/SeverityChart'
import HazardMap from './components/HazardMap'
import IncidentsView from './components/IncidentsView'
import FleetConfigView from './components/FleetConfigView'
import Header from './components/Header'
import { fetchEvents, fetchAlerts, fetchStats, fetchIncidents, fetchMapEvents } from './api'

const POLL_INTERVAL_MS = 5000

export default function App() {
  const [activeTab, setActiveTab] = useState('command_center')
  const [events, setEvents] = useState([])
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [mapEvents, setMapEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [severityFilter, setSeverityFilter] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [eventsData, alertsData, statsData, incidentsData, mapData] = await Promise.all([
        fetchEvents(50, severityFilter),
        fetchAlerts(20),
        fetchStats(),
        fetchIncidents(),
        fetchMapEvents(),
      ])

      setEvents(eventsData.events || [])
      setAlerts(alertsData.alerts || [])
      setStats(statsData)
      setIncidents(incidentsData.incidents || [])
      setMapEvents(mapData.map_events || eventsData.events || [])
      setLastUpdated(new Date())
    } catch (err) {
      console.error('Dashboard refresh error:', err)
    } finally {
      setLoading(false)
    }
  }, [severityFilter])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [refresh])

  return (
    <div className="min-h-screen bg-gray-950 text-white selection:bg-blue-500 selection:text-white">
      <Header
        lastUpdated={lastUpdated}
        loading={loading}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onRefresh={refresh}
      />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {activeTab === 'command_center' && (
          <>
            {/* Stats Bar */}
            <StatsBar stats={stats} />

            {/* Interactive GIS Hazard Map */}
            <HazardMap events={mapEvents} incidents={incidents} />

            {/* Charts & Real-Time Alert Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <SeverityChart events={events} />
              </div>
              <div>
                <AlertFeed alerts={alerts} />
              </div>
            </div>

            {/* Full Event Telemetry Table */}
            <EventTable
              events={events}
              severityFilter={severityFilter}
              onFilterChange={setSeverityFilter}
            />
          </>
        )}

        {activeTab === 'incidents' && (
          <IncidentsView incidents={incidents} />
        )}

        {activeTab === 'fleet_config' && (
          <FleetConfigView />
        )}
      </main>
    </div>
  )
}
