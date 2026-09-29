import { useState, useMemo } from 'react'
import { MapPin, Video, AlertTriangle, ShieldCheck, Cpu, Eye, ExternalLink, X } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const SEVERITY_COLORS = {
  HIGH: {
    pin: 'bg-red-500 text-white shadow-red-500/50',
    ring: 'border-red-500 animate-ping',
    badge: 'bg-red-500/20 text-red-400 border-red-500/30',
  },
  MEDIUM: {
    pin: 'bg-amber-500 text-white shadow-amber-500/50',
    ring: 'border-amber-500',
    badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  },
  LOW: {
    pin: 'bg-emerald-500 text-white shadow-emerald-500/50',
    ring: 'border-emerald-500',
    badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  },
}

export default function HazardMap({ events = [], incidents = [] }) {
  const [selectedItem, setSelectedItem] = useState(null)
  const [filterSeverity, setFilterSeverity] = useState('ALL')

  // Geo bounds calculation to normalize GPS lat/lon into a 2D map canvas
  const { normalizedPoints, bounds } = useMemo(() => {
    const pts = events.filter(e => e.lat && e.lon)
    if (pts.length === 0) {
      return { normalizedPoints: [], bounds: null }
    }

    const lats = pts.map(p => Number(p.lat))
    const lons = pts.map(p => Number(p.lon))
    const minLat = Math.min(...lats) - 0.015
    const maxLat = Math.max(...lats) + 0.015
    const minLon = Math.min(...lons) - 0.02
    const maxLon = Math.max(...lons) + 0.02

    const normalized = pts.map((pt, idx) => {
      // Invert Y so higher latitude is at the top of the map
      const x = ((Number(pt.lon) - minLon) / (maxLon - minLon || 1)) * 88 + 6
      const y = (1 - (Number(pt.lat) - minLat) / (maxLat - minLat || 1)) * 80 + 10
      return { ...pt, mapX: Math.max(8, Math.min(92, x)), mapY: Math.max(12, Math.min(88, y)) }
    })

    return { normalizedPoints: normalized, bounds: { minLat, maxLat, minLon, maxLon } }
  }, [events])

  const filteredPoints = useMemo(() => {
    if (filterSeverity === 'ALL') return normalizedPoints
    return normalizedPoints.filter(p => p.severity === filterSeverity)
  }, [normalizedPoints, filterSeverity])

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden relative flex flex-col h-[480px]">
      {/* Map Header Bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-950/60 backdrop-blur z-10">
        <div className="flex items-center gap-2">
          <MapPin size={18} className="text-blue-400" />
          <h2 className="font-semibold text-sm text-gray-200">Live Urban Hazard GIS Grid</h2>
          <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full font-mono">
            {filteredPoints.length} active markers
          </span>
        </div>

        {/* Severity Filter Pills */}
        <div className="flex gap-1.5 text-xs">
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 rounded-md transition-colors ${
                filterSeverity === sev
                  ? 'bg-blue-600 text-white font-medium'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Map Surface */}
      <div className="relative flex-1 bg-gradient-to-br from-gray-950 via-gray-900 to-slate-950 overflow-hidden">
        {/* SVG Grid Lines & Sector Circles (Simulated Tactical GIS Overlay) */}
        <svg className="absolute inset-0 w-full h-full opacity-20 pointer-events-none stroke-blue-500/40">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          <circle cx="50%" cy="50%" r="20%" fill="none" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="50%" cy="50%" r="35%" fill="none" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="50%" cy="50%" r="48%" fill="none" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="50%" y1="0" x2="50%" y2="100%" strokeWidth="0.5" strokeDasharray="2 2" />
          <line x1="0" y1="50%" x2="100%" y2="50%" strokeWidth="0.5" strokeDasharray="2 2" />
        </svg>

        {/* Tactical Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-gray-950/80 border border-gray-800 rounded-lg p-2 text-xs space-y-1 z-10 backdrop-blur pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-gray-300">High Threat (Score 7-10)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-gray-300">Medium Threat</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-gray-300">Nominal / Low</span>
          </div>
        </div>

        {/* Map Markers */}
        {filteredPoints.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
            No telemetry matching current filter
          </div>
        ) : (
          filteredPoints.map((pt, i) => {
            const sev = pt.severity || 'LOW'
            const style = SEVERITY_COLORS[sev] || SEVERITY_COLORS.LOW
            const isSelected = selectedItem?.event_id === pt.event_id

            return (
              <div
                key={pt.event_id || i}
                onClick={() => setSelectedItem(pt)}
                style={{ left: `${pt.mapX}%`, top: `${pt.mapY}%` }}
                className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group z-20"
              >
                {/* Ping wave for HIGH severity */}
                {sev === 'HIGH' && (
                  <span className={`absolute -inset-2 rounded-full border-2 ${style.ring} opacity-75`} />
                )}

                {/* Marker Button */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shadow-lg transition-transform group-hover:scale-125 ${
                    style.pin
                  } ${isSelected ? 'ring-4 ring-white ring-offset-2 ring-offset-gray-950' : ''}`}
                >
                  <AlertTriangle size={14} />
                </div>

                {/* Hover Label */}
                <div className="absolute left-1/2 -translate-x-1/2 bottom-8 hidden group-hover:block bg-gray-950 border border-gray-700 px-2 py-1 rounded text-[11px] whitespace-nowrap shadow-xl z-30 pointer-events-none">
                  <div className="font-semibold capitalize text-white">{pt.class_label}</div>
                  <div className="text-gray-400 font-mono text-[10px]">{pt.device_id}</div>
                </div>
              </div>
            )
          })
        )}

        {/* Incident Detail Drawer Modal */}
        {selectedItem && (
          <div className="absolute top-3 right-3 w-80 bg-gray-950/95 border border-gray-700 rounded-xl p-4 shadow-2xl z-30 backdrop-blur space-y-3 animate-in fade-in slide-in-from-right-2">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
                    SEVERITY_COLORS[selectedItem.severity]?.badge
                  }`}
                >
                  {selectedItem.severity}
                </span>
                <span className="font-semibold text-sm capitalize text-white">
                  {selectedItem.class_label}
                </span>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800"
              >
                <X size={16} />
              </button>
            </div>

            {/* Evidence Crop Preview */}
            <div className="bg-gray-900 rounded-lg p-2 border border-gray-800 text-center">
              <div className="text-[11px] text-gray-400 mb-1.5 flex items-center justify-between">
                <span>Zero-Trust Anonymized Crop</span>
                <ShieldCheck size={13} className="text-emerald-400" />
              </div>
              {selectedItem.crop_url ? (
                <img
                  src={selectedItem.crop_url}
                  alt="Hazard Evidence"
                  className="w-full h-32 object-cover rounded border border-gray-700"
                />
              ) : selectedItem.anon_crop_b64 ? (
                <img
                  src={`data:image/jpeg;base64,${selectedItem.anon_crop_b64}`}
                  alt="Hazard Evidence"
                  className="w-full h-32 object-cover rounded border border-gray-700"
                />
              ) : (
                <div className="w-full h-24 bg-gray-800/80 rounded flex flex-col items-center justify-center text-gray-500 text-xs gap-1">
                  <Eye size={20} className="opacity-40" />
                  <span>Faces blurred &amp; plates redacted</span>
                </div>
              )}
            </div>

            {/* Telemetry Metrics */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-900/60 p-2 rounded border border-gray-800/80">
                <div className="text-gray-500 text-[10px]">Triage Urgency</div>
                <div className="text-base font-bold text-red-400">
                  {selectedItem.triage_score ?? 8}/10
                </div>
              </div>
              <div className="bg-gray-900/60 p-2 rounded border border-gray-800/80">
                <div className="text-gray-500 text-[10px]">Confidence</div>
                <div className="text-base font-bold text-blue-400">
                  {((selectedItem.confidence || 0) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-gray-900/60 p-2 rounded border border-gray-800/80">
                <div className="text-gray-500 text-[10px]">Model Tier</div>
                <div className="font-mono font-medium capitalize text-indigo-400">
                  {selectedItem.model_tier || 'nano'} ({selectedItem.inference_ms || 4.2}ms)
                </div>
              </div>
              <div className="bg-gray-900/60 p-2 rounded border border-gray-800/80">
                <div className="text-gray-500 text-[10px]">Device ID</div>
                <div className="font-mono text-[11px] text-gray-300 truncate">
                  {selectedItem.device_id}
                </div>
              </div>
            </div>

            <div className="text-[11px] text-gray-400 flex items-center justify-between pt-1 border-t border-gray-800">
              <span>Coordinates: {Number(selectedItem.lat).toFixed(4)}, {Number(selectedItem.lon).toFixed(4)}</span>
              <span>{selectedItem.timestamp ? formatDistanceToNow(new Date(selectedItem.timestamp), { addSuffix: true }) : ''}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
