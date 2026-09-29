import { Bell, AlertTriangle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const SEVERITY_STYLES = {
  HIGH: 'border-red-500/50 bg-red-900/20 text-red-400',
  MEDIUM: 'border-yellow-500/50 bg-yellow-900/20 text-yellow-400',
  LOW: 'border-green-500/50 bg-green-900/20 text-green-400',
}

export default function AlertFeed({ alerts }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
        <Bell size={16} className="text-red-400" />
        <h2 className="font-semibold text-sm">Alert Feed</h2>
        {alerts.length > 0 && (
          <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
            {alerts.length}
          </span>
        )}
      </div>

      <div className="overflow-y-auto max-h-80 divide-y divide-gray-800">
        {alerts.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500 text-sm">
            <AlertTriangle className="mx-auto mb-2 opacity-30" size={32} />
            No alerts — system nominal
          </div>
        ) : (
          alerts.map((alert, i) => (
            <AlertItem key={alert.event_id || i} alert={alert} />
          ))
        )}
      </div>
    </div>
  )
}

function AlertItem({ alert }) {
  const sev = alert.severity || 'LOW'
  const ts = alert.timestamp ? new Date(Number(alert.timestamp)) : null

  return (
    <div className={`px-4 py-3 border-l-2 ${SEVERITY_STYLES[sev] || SEVERITY_STYLES.LOW}`}>
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm capitalize">
          {alert.class_label || 'Unknown'}
        </span>
        <span className="text-xs opacity-70">
          Score: {alert.triage_score ?? '–'}/10
        </span>
      </div>
      <div className="text-xs mt-1 opacity-60">
        Device: {alert.device_id || 'unknown'}
      </div>
      {ts && (
        <div className="text-xs mt-0.5 opacity-50">
          {formatDistanceToNow(ts, { addSuffix: true })}
        </div>
      )}
    </div>
  )
}
