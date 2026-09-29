import { Shield, RefreshCw, Radio, Layers, MapPin, Cpu } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Header({ lastUpdated, loading, activeTab, onTabChange, onRefresh }) {
  return (
    <header className="border-b border-gray-800 bg-gray-900/90 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 shadow-lg shadow-blue-900/20">
            <Shield size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-base tracking-tight text-white">AECHI</h1>
              <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded-full font-mono font-semibold">
                v1.2-PROD
              </span>
            </div>
            <p className="text-[11px] text-gray-400">
              Adaptive Edge-Cloud Hierarchical Intelligence for Urban Hazard Triage
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center bg-gray-950 p-1 rounded-xl border border-gray-800 text-xs">
          <button
            onClick={() => onTabChange('command_center')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors font-medium ${
              activeTab === 'command_center'
                ? 'bg-blue-600 text-white shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Layers size={14} />
            Command Center
          </button>
          <button
            onClick={() => onTabChange('incidents')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors font-medium ${
              activeTab === 'incidents'
                ? 'bg-blue-600 text-white shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <MapPin size={14} />
            Geo Incidents
          </button>
          <button
            onClick={() => onTabChange('fleet_config')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors font-medium ${
              activeTab === 'fleet_config'
                ? 'bg-blue-600 text-white shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Cpu size={14} />
            Edge Fleet
          </button>
        </div>

        {/* Live sync indicators */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/40 border border-emerald-900/60 px-2.5 py-1 rounded-full">
            <Radio size={13} className="animate-pulse" />
            <span className="font-semibold text-[11px]">STREAM ACTIVE</span>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-1 text-gray-400 hover:text-white px-2 py-1 rounded hover:bg-gray-800 transition-colors disabled:opacity-50"
            title="Refresh now"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span className="hidden sm:inline">
              {lastUpdated ? formatDistanceToNow(lastUpdated, { addSuffix: true }) : 'Syncing'}
            </span>
          </button>
        </div>
      </div>
    </header>
  )
}
