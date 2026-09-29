import { Shield, Wifi, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Header({ lastUpdated, loading }) {
  return (
    <header className="bg-gray-900 border-b border-gray-800 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-400" size={28} />
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              AECHI
            </h1>
            <p className="text-xs text-gray-400">
              Adaptive Edge-Cloud Hierarchical Intelligence — Urban Hazard Triage
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Live indicator */}
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400 animate-pulse'
              }`}
            />
            <span className="text-xs text-gray-400">
              {loading ? 'Updating...' : 'LIVE'}
            </span>
          </div>

          {lastUpdated && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock size={12} />
              <span>
                Updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
