import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Governance & Compliance View: policy transparency declarations and immutable audit log.
 */
export default function GovernanceView() {
  const { authFetch } = useAuth()
  const [logs, setLogs] = useState([])
  const [complianceInfo, setComplianceInfo] = useState(null)
  const [callingWindowMode, setCallingWindowMode] = useState('strict')
  const [decisionFilter, setDecisionFilter] = useState('')
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      setLoading(true)
      let url = '/api/governance/audit-log?limit=50'
      if (decisionFilter) url += `&decision=${decisionFilter}`
      const [logRes, compRes, modeRes] = await Promise.all([
        authFetch(url),
        authFetch('/api/governance/compliance-info'),
        authFetch('/api/governance/calling-window-mode'),
      ])
      if (logRes.ok) setLogs((await logRes.json()).items || [])
      if (compRes.ok) setComplianceInfo(await compRes.json())
      if (modeRes.ok) setCallingWindowMode((await modeRes.json()).calling_window_mode || 'strict')
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const toggleWindowMode = async () => {
    const nextMode = callingWindowMode === 'strict' ? 'demo_override' : 'strict'
    try {
      const res = await authFetch('/api/governance/calling-window-mode', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ calling_window_mode: nextMode }),
      })
      if (res.ok) {
        const data = await res.json()
        setCallingWindowMode(data.calling_window_mode)
      }
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    loadData()
  }, [decisionFilter])

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900 tracking-tight">Governance & Compliance Gate</h1>
        <p className="text-xs text-gray-500 mt-0.5">Machine compliance rules, transparent limitations, and immutable dispatch audit trails.</p>
      </div>

      {/* Demo Window Override Amber Banner */}
      {callingWindowMode === 'demo_override' && (
        <div className="bg-amber-100 border border-amber-300 p-3.5 rounded-xl text-xs text-amber-900 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <span className="font-semibold">Demo window override ON: calling-hours check bypassed for test calls.</span>
          </div>
          <button
            onClick={toggleWindowMode}
            className="text-[11px] font-bold text-amber-900 bg-amber-200 hover:bg-amber-300 px-3 py-1 rounded-lg border border-amber-300"
          >
            Revert to Strict Hours
          </button>
        </div>
      )}

      {callingWindowMode === 'strict' && (
        <div className="flex justify-end">
          <button
            onClick={toggleWindowMode}
            className="text-xs text-gray-500 hover:text-gray-800 underline"
          >
            Enable Demo Calling Hours Override (for test calls outside 09:00-21:00)
          </button>
        </div>
      )}

      {/* Compliance Policy Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-emerald-600 font-bold">🛡️ Active Enforced Controls</span>
          </div>
          <ul className="space-y-2 text-xs">
            {(complianceInfo?.active_controls || []).map((c) => (
              <li key={c.id} className="p-2 bg-gray-50 rounded-lg border border-gray-100">
                <span className="font-bold text-gray-800">{c.name}:</span> <span className="text-gray-600">{c.description}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-amber-50/60 p-5 rounded-xl border border-amber-200 shadow-xs space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-amber-800 font-bold">⚠️ Transparency & Policy Limitations</span>
          </div>
          <p className="text-[11px] text-amber-900">
            To ensure complete honesty and audit accuracy, the following external registries are NOT integrated:
          </p>
          <ul className="space-y-2 text-xs">
            {(complianceInfo?.unsupported_controls || []).map((u, i) => (
              <li key={i} className="p-2 bg-white/80 rounded-lg border border-amber-200">
                <span className="font-bold text-amber-950">{u.name}:</span> <span className="text-amber-800">{u.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Immutable Dispatch Audit Trail</h3>
          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="text-xs border border-gray-300 rounded-lg px-2.5 py-1 bg-white"
          >
            <option value="">All Decisions</option>
            <option value="ALLOWED">Allowed</option>
            <option value="BLOCKED">Blocked</option>
          </select>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-gray-400">Loading audit trail...</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-xs text-gray-400">No audit records found.</div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Decision</th>
                <th className="py-2.5 px-4">Reason Code</th>
                <th className="py-2.5 px-4">Record ID</th>
                <th className="py-2.5 px-4">Channel</th>
                <th className="py-2.5 px-4">Config Ver</th>
                <th className="py-2.5 px-4">Campaign</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((l, idx) => (
                <tr key={idx} className="hover:bg-gray-50/50">
                  <td className="py-2.5 px-4 font-mono text-[11px] text-gray-500">{new Date(l.timestamp).toLocaleString()}</td>
                  <td className="py-2.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${l.decision === 'ALLOWED' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                      {l.decision}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 font-mono text-[11px] text-rose-700">{l.reason_code || '—'}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-600">{l.record_id}</td>
                  <td className="py-2.5 px-4 uppercase text-[10px] text-gray-500">{l.channel}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-500">v{l.config_version}</td>
                  <td className="py-2.5 px-4 text-gray-400 font-mono text-[11px] truncate max-w-xs">{l.campaign_id || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

