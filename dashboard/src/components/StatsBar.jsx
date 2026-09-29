import { AlertTriangle, Activity, TrendingUp, Cpu } from 'lucide-react'

const CARDS = [
  {
    key: 'HIGH',
    label: 'HIGH Severity',
    icon: AlertTriangle,
    color: 'text-red-400',
    bg: 'bg-red-900/20 border-red-800/40',
  },
  {
    key: 'MEDIUM',
    label: 'MEDIUM Severity',
    icon: TrendingUp,
    color: 'text-yellow-400',
    bg: 'bg-yellow-900/20 border-yellow-800/40',
  },
  {
    key: 'LOW',
    label: 'LOW Severity',
    icon: Activity,
    color: 'text-green-400',
    bg: 'bg-green-900/20 border-green-800/40',
  },
  {
    key: 'total',
    label: 'Total Events (1h)',
    icon: Cpu,
    color: 'text-blue-400',
    bg: 'bg-blue-900/20 border-blue-800/40',
  },
]

export default function StatsBar({ stats }) {
  if (!stats) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {CARDS.map(c => (
          <div key={c.key} className={`rounded-xl border p-4 ${c.bg} animate-pulse`}>
            <div className="h-8 bg-gray-700 rounded w-16 mb-2" />
            <div className="h-4 bg-gray-700 rounded w-24" />
          </div>
        ))}
      </div>
    )
  }

  const getValue = (key) => {
    if (key === 'total') return stats.total ?? 0
    return stats.by_severity?.[key] ?? 0
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {CARDS.map(({ key, label, icon: Icon, color, bg }) => (
        <div key={key} className={`rounded-xl border p-4 ${bg}`}>
          <div className="flex items-center justify-between mb-2">
            <Icon className={color} size={20} />
            <span className="text-xs text-gray-500 uppercase tracking-wider">1h</span>
          </div>
          <div className={`text-3xl font-bold ${color}`}>{getValue(key)}</div>
          <div className="text-sm text-gray-400 mt-1">{label}</div>
        </div>
      ))}
    </div>
  )
}
