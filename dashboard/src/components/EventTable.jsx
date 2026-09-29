import { formatDistanceToNow } from 'date-fns'

const SEVERITY_BADGE = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
}

const TIER_BADGE = {
  nano: 'bg-blue-500/20 text-blue-400',
  small: 'bg-indigo-500/20 text-indigo-400',
  medium: 'bg-purple-500/20 text-purple-400',
}

const FILTER_OPTIONS = [null, 'HIGH', 'MEDIUM', 'LOW']
const FILTER_LABELS = { null: 'All', HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW' }

export default function EventTable({ events, severityFilter, onFilterChange }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800">
      {/* Table header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="font-semibold text-sm text-gray-300">
          Recent Detections
        </h2>
        {/* Severity filter pills */}
        <div className="flex gap-2">
          {FILTER_OPTIONS.map(opt => (
            <button
              key={String(opt)}
              onClick={() => onFilterChange(opt)}
              className={`text-xs px-3 py-1 rounded-full transition-colors ${
                severityFilter === opt
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {FILTER_LABELS[String(opt)] || 'All'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-gray-800">
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Device</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Model Tier</th>
              <th className="px-4 py-3">Inference</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50">
            {events.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-600">
                  No events to display
                </td>
              </tr>
            ) : (
              events.map((ev, i) => (
                <EventRow key={ev.event_id || i} event={ev} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function EventRow({ event }) {
  const ts = event.timestamp ? new Date(Number(event.timestamp)) : null
  const sev = event.severity || 'LOW'
  const tier = event.model_tier || 'nano'
  const conf = typeof event.confidence === 'number' ? event.confidence : parseFloat(event.confidence) || 0

  return (
    <tr className="hover:bg-gray-800/40 transition-colors">
      <td className="px-4 py-2.5 text-gray-400 text-xs whitespace-nowrap">
        {ts ? formatDistanceToNow(ts, { addSuffix: true }) : '—'}
      </td>
      <td className="px-4 py-2.5 font-mono text-xs text-gray-300">
        {event.device_id || '—'}
      </td>
      <td className="px-4 py-2.5 font-medium capitalize">
        {event.class_label || '—'}
      </td>
      <td className="px-4 py-2.5">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_BADGE[sev] || SEVERITY_BADGE.LOW}`}>
          {sev}
        </span>
      </td>
      <td className="px-4 py-2.5 text-gray-300">
        <div className="flex items-center gap-2">
          <div className="w-16 bg-gray-800 rounded-full h-1.5">
            <div
              className="h-1.5 rounded-full bg-blue-500"
              style={{ width: `${(conf * 100).toFixed(0)}%` }}
            />
          </div>
          <span className="text-xs">{(conf * 100).toFixed(1)}%</span>
        </div>
      </td>
      <td className="px-4 py-2.5">
        <span className={`text-xs px-2 py-0.5 rounded font-mono ${TIER_BADGE[tier] || TIER_BADGE.nano}`}>
          {tier}
        </span>
      </td>
      <td className="px-4 py-2.5 text-gray-400 text-xs">
        {event.inference_ms != null ? `${event.inference_ms}ms` : '—'}
      </td>
    </tr>
  )
}
