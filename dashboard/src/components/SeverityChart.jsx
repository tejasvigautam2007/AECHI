import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend
} from 'recharts'
import { useMemo } from 'react'

const SEVERITY_COLORS = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#22c55e',
}

export default function SeverityChart({ events }) {
  // Build class label breakdown grouped by severity
  const chartData = useMemo(() => {
    const counts = {}
    for (const ev of events) {
      const label = ev.class_label || 'unknown'
      if (!counts[label]) counts[label] = { name: label, HIGH: 0, MEDIUM: 0, LOW: 0 }
      counts[label][ev.severity || 'LOW'] += 1
    }
    return Object.values(counts)
      .sort((a, b) => (b.HIGH + b.MEDIUM) - (a.HIGH + a.MEDIUM))
      .slice(0, 8)  // Top 8 classes
  }, [events])

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <h2 className="font-semibold text-sm mb-4 text-gray-300">
        Detection Breakdown by Class &amp; Severity
      </h2>
      {chartData.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-600 text-sm">
          No detection data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="name"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickLine={false}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="HIGH" fill={SEVERITY_COLORS.HIGH} stackId="a" name="HIGH" />
            <Bar dataKey="MEDIUM" fill={SEVERITY_COLORS.MEDIUM} stackId="a" name="MEDIUM" />
            <Bar dataKey="LOW" fill={SEVERITY_COLORS.LOW} stackId="a" name="LOW" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
