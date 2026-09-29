import { AlertOctagon, Video, Clock, CheckCircle2, ShieldAlert } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function IncidentsView({ incidents = [] }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-red-400" size={20} />
            Active Correlated Incidents
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Incidents formed by spatial-temporal clustering of multiple edge camera detections within 150m.
          </p>
        </div>
        <span className="bg-red-500/20 text-red-400 border border-red-500/30 px-3 py-1 rounded-full text-xs font-semibold">
          {incidents.length} Active Incidents
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {incidents.length === 0 ? (
          <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">
            <CheckCircle2 size={36} className="mx-auto text-emerald-400/60 mb-2" />
            <div className="font-semibold text-gray-300">All Urban Sectors Clear</div>
            <div className="text-xs mt-1">No active multi-node hazard clusters detected in the last 60 minutes.</div>
          </div>
        ) : (
          incidents.map((inc, i) => (
            <div
              key={inc.incident_id || i}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-lg space-y-4 hover:border-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800">
                      {inc.incident_id}
                    </span>
                    <span className="font-bold text-white capitalize text-base">
                      {inc.class_label} Alert
                    </span>
                  </div>
                  <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                    <Clock size={12} />
                    <span>
                      {inc.updated_at ? formatDistanceToNow(new Date(Number(inc.updated_at)), { addSuffix: true }) : 'Just now'}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Urgency</div>
                  <div className="text-2xl font-black text-red-500">{inc.triage_score || 9}/10</div>
                </div>
              </div>

              {/* Geo location & corroborating cameras */}
              <div className="bg-gray-950/70 rounded-lg p-3 border border-gray-800/80 space-y-2 text-xs">
                <div className="flex justify-between items-center text-gray-300">
                  <span className="text-gray-500">Spatial Centroid:</span>
                  <span className="font-mono text-blue-400 font-medium">
                    {Number(inc.lat || 0).toFixed(4)}, {Number(inc.lon || 0).toFixed(4)}
                  </span>
                </div>

                <div className="border-t border-gray-800/60 pt-2">
                  <div className="text-gray-500 mb-1 flex items-center gap-1">
                    <Video size={13} className="text-indigo-400" />
                    <span>Corroborating Edge Nodes ({inc.devices?.length || 1}):</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {(inc.devices || []).map(dev => (
                      <span
                        key={dev}
                        className="bg-gray-800 text-gray-300 font-mono text-[11px] px-2 py-0.5 rounded border border-gray-700"
                      >
                        {dev}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center text-xs pt-1">
                <span className="text-emerald-400 font-medium flex items-center gap-1">
                  <CheckCircle2 size={13} />
                  Triaged &amp; Dispatched via SNS
                </span>
                <span className="text-gray-500">Auto-expires in 24h</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
