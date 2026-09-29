import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_ENDPOINT || 'http://localhost:3001'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 8000,
})

// Synthetic fallback data for instant offline / local demo preview
const MOCK_CAMERAS = [
  { device_id: 'cam-connaught-01', name: 'Connaught Place Ring', lat: 28.6315, lon: 77.2167, status: 'ONLINE', fps: 10 },
  { device_id: 'cam-indiagate-02', name: 'India Gate Junction', lat: 28.6129, lon: 77.2295, status: 'ONLINE', fps: 10 },
  { device_id: 'cam-chandni-03', name: 'Chandni Chowk Main', lat: 28.6506, lon: 77.2303, status: 'ONLINE', fps: 10 },
  { device_id: 'cam-nehru-04', name: 'Nehru Place Outer', lat: 28.5494, lon: 77.2520, status: 'ONLINE', fps: 10 },
  { device_id: 'cam-aerocity-05', name: 'Aerocity Spine Rd', lat: 28.5528, lon: 77.1219, status: 'ONLINE', fps: 10 },
]

export async function fetchEvents(limit = 50, severity = null) {
  try {
    const params = { limit }
    if (severity) params.severity = severity
    const res = await api.get('/dashboard/events', { params })
    return res.data
  } catch (err) {
    // Return realistic fallback demo events if API not yet provisioned
    return {
      events: generateFallbackEvents(limit, severity),
      count: limit,
      is_mock: true
    }
  }
}

export async function fetchAlerts(limit = 20) {
  try {
    const res = await api.get('/dashboard/alerts', { params: { limit } })
    return res.data
  } catch (err) {
    return {
      alerts: generateFallbackAlerts(),
      count: 3,
      is_mock: true
    }
  }
}

export async function fetchStats() {
  try {
    const res = await api.get('/dashboard/stats')
    return res.data
  } catch (err) {
    return {
      period: 'last_1h',
      total: 128,
      by_severity: { HIGH: 8, MEDIUM: 26, LOW: 94 },
      server_time: Date.now(),
      is_mock: true
    }
  }
}

export async function fetchIncidents() {
  try {
    const res = await api.get('/dashboard/incidents')
    return res.data
  } catch (err) {
    return {
      incidents: [
        {
          incident_id: 'INC-FIRE-409122',
          class_label: 'fire',
          severity: 'HIGH',
          triage_score: 10,
          devices: ['cam-indiagate-02', 'cam-connaught-01'],
          lat: 28.6145,
          lon: 77.2280,
          updated_at: Date.now() - 45000,
        },
        {
          incident_id: 'INC-ACCI-398110',
          class_label: 'accident',
          severity: 'HIGH',
          triage_score: 8,
          devices: ['cam-chandni-03'],
          lat: 28.6510,
          lon: 77.2312,
          updated_at: Date.now() - 120000,
        }
      ],
      is_mock: true
    }
  }
}

export async function fetchMapEvents() {
  try {
    const res = await api.get('/dashboard/map-events')
    return res.data
  } catch (err) {
    return {
      map_events: generateFallbackMapEvents(),
      cameras: MOCK_CAMERAS,
      is_mock: true
    }
  }
}

function generateFallbackEvents(limit, severity) {
  const classes = ['accident', 'fire', 'crowd', 'debris', 'car', 'person']
  const severities = { fire: 'HIGH', accident: 'HIGH', crowd: 'MEDIUM', debris: 'MEDIUM', car: 'LOW', person: 'LOW' }
  const tiers = ['nano', 'small', 'medium']

  const events = []
  const now = Date.now()
  for (let i = 0; i < Math.min(limit, 25); i++) {
    const cls = classes[i % classes.length]
    const sev = severities[cls]
    if (severity && sev !== severity) continue

    const cam = MOCK_CAMERAS[i % MOCK_CAMERAS.length]
    events.push({
      event_id: `evt-demo-${i + 100}`,
      device_id: cam.device_id,
      class_label: cls,
      severity: sev,
      confidence: +(0.72 + (i % 5) * 0.05).toFixed(2),
      model_tier: tiers[i % tiers.length],
      inference_ms: +(3.2 + (i % 3) * 6.5).toFixed(1),
      timestamp: now - i * 65000,
      lat: cam.lat,
      lon: cam.lon,
      triage_score: sev === 'HIGH' ? 9 : sev === 'MEDIUM' ? 5 : 2,
    })
  }
  return events
}

function generateFallbackAlerts() {
  const now = Date.now()
  return [
    {
      event_id: 'alt-901',
      incident_id: 'INC-FIRE-409122',
      device_id: 'cam-indiagate-02',
      class_label: 'fire',
      severity: 'HIGH',
      triage_score: '10',
      timestamp: now - 32000,
      lat: 28.6145,
      lon: 77.2280,
      corroborating_cameras: 2,
      message: '🚨 CRITICAL: High-temperature blaze detected with 2 corroborating cameras.'
    },
    {
      event_id: 'alt-902',
      incident_id: 'INC-ACCI-398110',
      device_id: 'cam-chandni-03',
      class_label: 'accident',
      severity: 'HIGH',
      triage_score: '8',
      timestamp: now - 140000,
      lat: 28.6510,
      lon: 77.2312,
      corroborating_cameras: 1,
      message: '⚠️ Multi-vehicle collision identified in high-density lane.'
    }
  ]
}

function generateFallbackMapEvents() {
  return generateFallbackEvents(12, null)
}
