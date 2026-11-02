import React, { useEffect, useState } from 'react'

/**
 * Live Outcomes Tab displaying campaign interaction results,
 * gate block breakdowns, and CSV export.
 */
export default function CampaignOutcomesTab({ campaignId, authFetch }) {
  const [outcomes, setOutcomes] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadOutcomes = async () => {
    try {
      setLoading(true)
      const res = await authFetch(`/api/campaigns/${campaignId}/outcomes`)
      if (res.ok) {
        const data = await res.json()
        setOutcomes(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOutcomes()
  }, [campaignId])

  const handleExportCSV = () => {
    window.open(`http://localhost:8000/api/campaigns/${campaignId}/interactions/export`, '_blank')
  }

  if (loading) return <div className="p-8 text-center text-xs text-gray-400">Loading outcome metrics...</div>
  if (!outcomes) return <div className="p-8 text-center text-xs text-gray-400">No outcomes recorded yet.</div>

  const statusCounts = outcomes.status_counts || {}
  const outcomeCounts = outcomes.outcome_counts || {}
  const blockedReasons = outcomes.blocked_reasons || {}

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Test Calls Dispatched</p>
          <p className="text-xl font-bold text-gray-900 mt-1 font-mono">{outcomes.total_dispatched}</p>
          <span className="text-[10px] text-gray-400">Calls to verified testers</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[10px] text-emerald-600 font-semibold uppercase tracking-wider">Completed Sessions</p>
          <p className="text-xl font-bold text-emerald-700 mt-1 font-mono">{statusCounts.completed || 0}</p>
          <span className="text-[10px] text-gray-400">Avg duration: {outcomes.avg_duration_s}s</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[10px] text-brand-600 font-semibold uppercase tracking-wider">Interested Outcome</p>
          <p className="text-xl font-bold text-brand-700 mt-1 font-mono">{outcomeCounts.interested || 0}</p>
          <span className="text-[10px] text-gray-400">Express customer intent</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[10px] text-rose-600 font-semibold uppercase tracking-wider">Blocked by Gate</p>
          <p className="text-xl font-bold text-rose-700 mt-1 font-mono">{statusCounts.blocked || 0}</p>
          <span className="text-[10px] text-gray-400">Protected by compliance</span>
        </div>
      </div>

      {/* Outcome Distribution & Gate Blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Outcome Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3">
          <h4 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Audience Sentiment & Outcomes</h4>
          <div className="space-y-2 text-xs">
            {Object.entries(outcomeCounts).map(([oc, count]) => (
              <div key={oc} className="flex justify-between items-center p-2 rounded-lg bg-gray-50">
                <span className="capitalize font-semibold text-gray-700">{oc.replace('_', ' ')}</span>
                <span className="font-mono font-bold text-gray-900 bg-white px-2 py-0.5 rounded border border-gray-200">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Gate Blocks Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3">
          <h4 className="text-xs font-bold text-gray-900 uppercase tracking-wider">Compliance Gate Blocking Audit</h4>
          {Object.keys(blockedReasons).length === 0 ? (
            <p className="text-xs text-gray-400 italic">No recipients were blocked by compliance gate.</p>
          ) : (
            <div className="space-y-2 text-xs">
              {Object.entries(blockedReasons).map(([reason, count]) => (
                <div key={reason} className="flex justify-between items-center p-2 rounded-lg bg-rose-50/60 border border-rose-100">
                  <span className="font-mono text-[11px] font-bold text-rose-900">{reason}</span>
                  <span className="font-mono font-bold text-rose-700 bg-white px-2 py-0.5 rounded border border-rose-200">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Export Section */}
      <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold text-gray-900">Export Interaction Data</p>
          <p className="text-[11px] text-gray-500">Download tenant-scoped CSV of all communications, extractions, and durations for audit.</p>
        </div>
        <button
          onClick={handleExportCSV}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs"
        >
          📥 Export CSV
        </button>
      </div>
    </div>
  )
}

