import React, { useState } from 'react'

/**
 * Launch Confirmation Modal enforcing explicit confirmation of recipient counts
 * and prominent TEST MODE declarations.
 */
export default function CampaignLaunchModal({ campaign, onClose, onLaunchSuccess, authFetch }) {
  const [typedCount, setTypedCount] = useState('')
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState(null)

  const expectedCount = campaign.recipient_count || 0
  const isMatch = parseInt(typedCount) === expectedCount

  const handleLaunch = async () => {
    if (!isMatch) return
    try {
      setLaunching(true)
      setError(null)
      const res = await authFetch(`/api/campaigns/${campaign.id}/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirm_count: expectedCount,
          mode: 'test',
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail?.message || err.detail || 'Launch failed')
      }
      const data = await res.json()
      alert(`Campaign launched in TEST MODE! Dispatched ${data.total_dispatched} communications (${data.queued_tasks} queued, ${data.blocked_by_gate} blocked by gate).`)
      onLaunchSuccess()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div className="flex justify-between items-center border-b pb-3">
          <div className="flex items-center gap-2">
            <span className="text-amber-600 text-lg">⚠️</span>
            <h3 className="text-sm font-bold text-gray-900">Confirm Campaign Test Launch</h3>
          </div>
          <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-700">✕</button>
        </div>

        <div className="bg-amber-50 p-3 rounded-xl border border-amber-200 text-xs text-amber-900 space-y-1">
          <p className="font-bold">TEST MODE RESTRICTION:</p>
          <p className="text-[11px]">
            This deployment creates web-tester interaction links for verified test profiles. No telephone calls will be placed.
          </p>
        </div>

        <div className="bg-gray-50 p-3 rounded-lg text-xs space-y-1 font-mono text-gray-700">
          <p>Product: <strong className="text-gray-900">{campaign.product_name}</strong></p>
          <p>Config Version: <strong className="text-gray-900">v{campaign.current_voice_config_version || 1}</strong></p>
          <p>Snapshot Recipients: <strong className="text-gray-900 font-bold">{expectedCount}</strong></p>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-gray-700">
            Type exact recipient count (<span className="text-brand-600 font-mono font-bold">{expectedCount}</span>) to confirm:
          </label>
          <input
            type="number"
            value={typedCount}
            onChange={(e) => setTypedCount(e.target.value)}
            placeholder={expectedCount.toString()}
            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500 font-mono"
          />
        </div>

        {error && <div className="p-2.5 bg-rose-50 text-rose-700 text-xs rounded-lg">{error}</div>}

        <div className="flex justify-end gap-2 pt-2 border-t">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 text-xs">
            Cancel
          </button>
          <button
            onClick={handleLaunch}
            disabled={!isMatch || launching}
            className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shadow-xs disabled:opacity-40 transition"
          >
            {launching ? 'Launching...' : 'Confirm Test Launch 🚀'}
          </button>
        </div>
      </div>
    </div>
  )
}

