import { useState, useEffect, useCallback } from 'react'
import StatsBar from './components/StatsBar'
import AlertFeed from './components/AlertFeed'
import EventTable from './components/EventTable'
import SeverityChart from './components/SeverityChart'
import Header from './components/Header'
import { fetchEvents, fetchAlerts, fetchStats } from './api'

const POLL_INTERVAL_MS = 5000  // Refresh every 5 seconds

export default function App() {
  const [events, setEvents] = useState([])
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [severityFilter, setSeverityFilter] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [eventsData, alertsData, statsData] = await Promise.all([
        fetchEvents(50, severityFilter),
        fetchAlerts(20),
        fetchStats(),
      ])
      setEvents(eventsData.events || [])
      setAlerts(alertsData.alerts || [])
      setStats(statsData)
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
    <div className="min-h-screen bg-gray-950 text-white">
      <Header lastUpdated={lastUpdated} loading={loading} />

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats Bar */}
        <StatsBar stats={stats} />

        {/* Charts + Alert Feed row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <SeverityChart events={events} />
          </div>
          <div>
            <AlertFeed alerts={alerts} />
          </div>
        </div>

        {/* Event Table */}
        <EventTable
          events={events}
          severityFilter={severityFilter}
          onFilterChange={setSeverityFilter}
        />
      </main>
    </div>
  )
}
