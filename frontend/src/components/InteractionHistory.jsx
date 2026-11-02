import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Interaction History page: paged communications table with detailed transcript and audit drawer.
 */
export default function InteractionHistory() {
  const { authFetch } = useAuth()
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedItem, setSelectedItem] = useState(null)
  const [auditEntries, setAuditEntries] = useState([])
  const [loading, setLoading] = useState(true)

  const loadInteractions = async () => {
    try {
      setLoading(true)
      let url = '/api/communication?limit=50'
      if (statusFilter) url += `&status=${statusFilter}`
      const res = await authFetch(url)
      if (res.ok) {
        const data = await res.json()
        setItems(data.items || [])
        setTotal(data.total || 0)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInteractions()
  }, [statusFilter])

  const openDetail = async (item) => {
    setSelectedItem(item)
    try {
      const res = await authFetch(`/api/governance/audit-log?campaign_id=${item.campaign_id || ''}&limit=20`)
      if (res.ok) {
        const data = await res.json()
        setAuditEntries((data.items || []).filter((a) => a.communication_id === item.communication_id))
      }
    } catch (err) {
      console.error(err)
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed': return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">Completed</span>
      case 'blocked': return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700">Blocked</span>
      case 'in_progress': return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">In Progress</span>
      case 'queued': return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700">Queued</span>
      default: return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-600">{status}</span>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Interaction History</h1>
          <p className="text-xs text-gray-500 mt-0.5">Audited records of all communication attempts, conversation transcripts, and gate decisions.</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-xs border border-gray-300 rounded-lg px-3 py-1.5 bg-white"
        >
          <option value="">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="blocked">Blocked</option>
          <option value="queued">Queued</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-xs text-gray-400">Loading interactions...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-xs text-gray-400">No communication records found.</div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-2.5 px-4">Recipient</th>
                <th className="py-2.5 px-4">Product</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Outcome</th>
                <th className="py-2.5 px-4">Interest</th>
                <th className="py-2.5 px-4">Duration</th>
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((it) => {
                const ext = it.extraction || {}
                return (
                  <tr key={it.communication_id} onClick={() => openDetail(it)} className="hover:bg-gray-50/75 cursor-pointer">
                    <td className="py-2.5 px-4 font-semibold text-gray-900">{it.recipient_first_name || 'Customer'}</td>
                    <td className="py-2.5 px-4 text-gray-600">{it.product_name || 'Product'}</td>
                    <td className="py-2.5 px-4">{getStatusBadge(it.status)}</td>
                    <td className="py-2.5 px-4 capitalize font-medium text-gray-700">{ext.outcome || it.outcome || (it.status === 'blocked' ? it.blocked_reason : '—')}</td>
                    <td className="py-2.5 px-4 capitalize text-gray-600">{ext.interest_level || '—'}</td>
                    <td className="py-2.5 px-4 font-mono text-gray-500">{it.duration_s ? `${it.duration_s}s` : '—'}</td>
                    <td className="py-2.5 px-4 text-gray-400 text-[11px]">{new Date(it.created_at).toLocaleDateString()}</td>
                    <td className="py-2.5 px-4 text-right"><button className="text-brand-600 font-semibold hover:underline">Inspect</button></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/40 flex justify-end z-50">
          <div className="bg-white w-full max-w-xl h-full shadow-2xl p-6 overflow-y-auto space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-900">Interaction Details</h3>
                <span className="text-[10px] font-mono text-gray-400">{selectedItem.communication_id}</span>
              </div>
              <button onClick={() => setSelectedItem(null)} className="text-xs text-gray-400 hover:text-gray-700">✕ Close</button>
            </div>

            <div className="grid grid-cols-2 gap-3 bg-gray-50 p-3 rounded-lg text-xs">
              <div><span className="text-gray-400 block text-[10px]">Status:</span> {getStatusBadge(selectedItem.status)}</div>
              <div><span className="text-gray-400 block text-[10px]">Config Version:</span> <span className="font-mono">v{selectedItem.config_version || 1}</span></div>
              {selectedItem.blocked_reason && <div className="col-span-2 text-rose-700 font-semibold">Blocked Reason: {selectedItem.blocked_reason}</div>}
            </div>

            {/* Transcript */}
            {selectedItem.transcript?.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-gray-800">Transcript Turns</h4>
                <div className="space-y-1.5 max-h-56 overflow-y-auto text-xs bg-gray-50 p-3 rounded-lg border">
                  {selectedItem.transcript.map((t, idx) => (
                    <div key={idx} className="p-2 bg-white rounded border border-gray-100">
                      <div className="flex justify-between text-[10px] text-gray-400 font-mono">
                        <span className="font-bold uppercase text-gray-600">{t.speaker}</span>
                        {t.latency_ms ? <span>Latency: {Math.round(t.latency_ms)}ms</span> : null}
                      </div>
                      <p className="mt-0.5 text-gray-800">{t.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Extraction */}
            {selectedItem.extraction && Object.keys(selectedItem.extraction).length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-gray-800 mb-1">Session Extraction</h4>
                <div className="bg-gray-900 text-gray-100 p-3 rounded-lg font-mono text-[11px] overflow-x-auto">
                  <pre>{JSON.stringify(selectedItem.extraction, null, 2)}</pre>
                </div>
              </div>
            )}

            {/* Audit Trail */}
            <div>
              <h4 className="text-xs font-bold text-gray-800 mb-1">Audit Trail Records</h4>
              <div className="space-y-1 text-xs">
                {auditEntries.map((a, i) => (
                  <div key={i} className="p-2 bg-gray-50 rounded border flex justify-between items-center">
                    <div>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${a.decision === 'ALLOWED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>{a.decision}</span>
                      {a.reason_code && <span className="ml-2 font-mono text-[11px] text-rose-700">{a.reason_code}</span>}
                    </div>
                    <span className="text-[10px] text-gray-400 font-mono">{new Date(a.timestamp).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

