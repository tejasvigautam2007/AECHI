import { useState } from 'react'
import { Cpu, Shield, Sliders, CheckCircle, Wifi, Camera } from 'lucide-react'

const REGISTERED_FLEET = [
  { device_id: 'cam-connaught-01', name: 'Connaught Place Ring', hw: 'Jetson Nano 4GB', status: 'ONLINE', fps: 10, mtls: true, nano_conf: 0.60, small_conf: 0.75 },
  { device_id: 'cam-indiagate-02', name: 'India Gate Junction', hw: 'Raspberry Pi 5 + Hailo-8L', status: 'ONLINE', fps: 10, mtls: true, nano_conf: 0.60, small_conf: 0.75 },
  { device_id: 'cam-chandni-03', name: 'Chandni Chowk Main', hw: 'Jetson Orin Nano', status: 'ONLINE', fps: 15, mtls: true, nano_conf: 0.65, small_conf: 0.80 },
  { device_id: 'cam-nehru-04', name: 'Nehru Place Outer', hw: 'x86_64 Edge Gateway', status: 'ONLINE', fps: 12, mtls: true, nano_conf: 0.60, small_conf: 0.75 },
  { device_id: 'cam-aerocity-05', name: 'Aerocity Spine Rd', hw: 'Jetson Nano 4GB', status: 'ONLINE', fps: 10, mtls: false, nano_conf: 0.60, small_conf: 0.75 },
]

export default function FleetConfigView() {
  const [nanoThreshold, setNanoThreshold] = useState(0.60)
  const [smallThreshold, setSmallThreshold] = useState(0.75)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const handleSave = () => {
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  return (
    <div className="space-y-6">
      {/* Fleet Overview Header */}
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Cpu className="text-blue-400" size={20} />
          Edge Node Fleet &amp; Pipeline Configuration
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Manage remote edge devices, zero-trust cryptographic credentials, and dynamic cascading inference thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fleet Table (2 cols) */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
            <h3 className="font-semibold text-sm text-gray-200 flex items-center gap-2">
              <Camera size={16} className="text-indigo-400" />
              Registered Edge Camera Nodes ({REGISTERED_FLEET.length})
            </h3>
            <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              5/5 Online
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800 bg-gray-950/50">
                  <th className="px-4 py-2.5">Node ID</th>
                  <th className="px-4 py-2.5">Location</th>
                  <th className="px-4 py-2.5">Hardware Target</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Security (mTLS)</th>
                  <th className="px-4 py-2.5">FPS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {REGISTERED_FLEET.map(cam => (
                  <tr key={cam.device_id} className="hover:bg-gray-800/40 transition-colors">
                    <td className="px-4 py-3 font-mono font-medium text-white">{cam.device_id}</td>
                    <td className="px-4 py-3 text-gray-300">{cam.name}</td>
                    <td className="px-4 py-3 text-gray-400">{cam.hw}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        {cam.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {cam.mtls ? (
                        <span className="bg-blue-900/30 text-blue-400 border border-blue-800 px-2 py-0.5 rounded text-[10px] font-mono">
                          mTLS X.509
                        </span>
                      ) : (
                        <span className="bg-gray-800 text-gray-400 px-2 py-0.5 rounded text-[10px] font-mono">
                          API-Key Only
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-300">{cam.fps}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Dynamic Cascading Thresholds Controller */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-800 pb-3">
            <Sliders className="text-blue-400" size={18} />
            <h3 className="font-semibold text-sm text-white">Cascading Thresholds</h3>
          </div>

          <p className="text-xs text-gray-400 leading-relaxed">
            Configure dynamic confidence escalation boundaries pushed down to the edge fleet.
          </p>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-300 font-medium">YOLOv8 Nano Cutoff (Tier 0 → 1)</span>
                <span className="font-mono text-blue-400 font-bold">{nanoThreshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.40"
                max="0.80"
                step="0.05"
                value={nanoThreshold}
                onChange={e => setNanoThreshold(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="text-[10px] text-gray-500 mt-0.5">Escalates to small model if confidence &lt; {nanoThreshold}</div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-gray-300 font-medium">YOLOv8 Small Cutoff (Tier 1 → 2)</span>
                <span className="font-mono text-indigo-400 font-bold">{smallThreshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.65"
                max="0.90"
                step="0.05"
                value={smallThreshold}
                onChange={e => setSmallThreshold(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="text-[10px] text-gray-500 mt-0.5">Escalates to medium model if confidence &lt; {smallThreshold}</div>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleSave}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              {saveSuccess ? (
                <>
                  <CheckCircle size={14} className="text-white" />
                  Pushed to Fleet
                </>
              ) : (
                'Broadcast Config to Edge Fleet'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
