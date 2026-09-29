import axios from 'axios'

// Set your API Gateway endpoint here (or use VITE env var)
const API_BASE = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
})

export async function fetchEvents(limit = 50, severity = null) {
  const params = { limit }
  if (severity) params.severity = severity
  const res = await api.get('/dashboard/events', { params })
  return res.data
}

export async function fetchAlerts(limit = 20) {
  const res = await api.get('/dashboard/alerts', { params: { limit } })
  return res.data
}

export async function fetchStats() {
  const res = await api.get('/dashboard/stats')
  return res.data
}
