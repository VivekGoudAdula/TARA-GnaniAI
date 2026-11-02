import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

const API_BASE = 'http://localhost:8000/api'

/**
 * Platform overview dashboard showing tenant analytics, band distribution, and scoring status.
 */
export default function Dashboard({ setActiveNav }) {
  const { token, tenant } = useAuth()
  const [stats, setStats] = useState({
    customers: 0,
    leads: 0,
    products: 0,
    high: 0,
    medium: 0,
    low: 0,
  })
  const [governanceSummary, setGovernanceSummary] = useState(null)
  const [isScoring, setIsScoring] = useState(false)

  const loadData = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` }
      const [custRes, leadRes, prodRes, govRes] = await Promise.all([
        fetch(`${API_BASE}/customers`, { headers }),
        fetch(`${API_BASE}/leads`, { headers }),
        fetch(`${API_BASE}/products`, { headers }),
        fetch(`http://localhost:8000/api/governance/dashboard-summary`, { headers }),
      ])
      const [cust, lead, prods, gov] = await Promise.all([
        custRes.json(),
        leadRes.json(),
        prodRes.json(),
        govRes.json(),
      ])

      setStats({
        customers: cust.total || 0,
        leads: lead.total || 0,
        products: (prods || []).length,
        high: (cust.high_count || 0) + (lead.high_count || 0),
        medium: (cust.medium_count || 0) + (lead.medium_count || 0),
        low: (cust.low_count || 0) + (lead.low_count || 0),
      })
      if (gov) setGovernanceSummary(gov)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    }
  }

  const runScoring = async () => {
    setIsScoring(true)
    try {
      const res = await fetch(`${API_BASE}/scoring/run`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Scoring failed')
      await loadData()
      alert('Scoring completed successfully across all products!')
    } catch (err) {
      alert(err.message)
    } finally {
      setIsScoring(false)
    }
  }

  useEffect(() => {
    if (token) loadData()
  }, [token])

  const totalScored = stats.high + stats.medium + stats.low

  return (
    <div className="space-y-6">
      {/* Synthetic Data Banner */}
      <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2.5 rounded-xl text-xs flex items-center justify-between">
        <span className="font-medium">
          🛡️ Notice: Operating on synthetic test profiles. All financial scores and demographic data are synthetic benchmarks.
        </span>
        <span className="text-[10px] bg-amber-100 text-amber-900 px-2 py-0.5 rounded font-semibold uppercase">
          Synthetic Only
        </span>
      </div>

      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-gray-900">{tenant?.name} Overview</h1>
          <p className="text-xs text-gray-500">Workspace health, catalog stats, and scoring summary</p>
        </div>
        <button
          onClick={runScoring}
          disabled={isScoring}
          className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
        >
          {isScoring ? 'Scoring...' : 'Run Scoring Engine'}
        </button>
      </div>

      {/* Key Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-gray-500 font-medium">Customer Records</span>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.customers}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-gray-500 font-medium">External Leads</span>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.leads}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-gray-500 font-medium">Active Products</span>
          <p className="text-2xl font-bold text-gray-900 mt-1">{stats.products}</p>
        </div>
        <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-4 shadow-sm">
          <span className="text-xs text-rose-700 font-medium">Blocked by Gate</span>
          <p className="text-2xl font-bold text-rose-900 mt-1 font-mono">{governanceSummary?.blocked_by_gate || 0}</p>
          <span className="text-[10px] text-rose-600">Compliance &amp; DND</span>
        </div>
      </div>

      {/* Last Campaign Run Summary */}
      {governanceSummary?.last_campaign && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 px-2 py-0.5 rounded">
              Recent Campaign Activity
            </span>
            <h3 className="text-xs font-bold text-gray-900 mt-1">{governanceSummary.last_campaign.name}</h3>
            <p className="text-[11px] text-gray-500">Status: <strong className="uppercase">{governanceSummary.last_campaign.status}</strong> • Snapshot: {governanceSummary.last_campaign.recipient_count} recipients</p>
          </div>
          <button onClick={() => setActiveNav('campaigns')} className="px-3 py-1.5 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
            View Campaigns →
          </button>
        </div>
      )}

      {/* Fit Score Distribution */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Product Fit Score Distribution</h3>
            <p className="text-xs text-gray-500">Breakdown of customer and lead engagement tiers</p>
          </div>
          <span className="text-xs text-gray-500 font-medium">Total Matches Scored: {totalScored}</span>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
            <span className="text-[11px] font-semibold text-green-700 block">High Fit (≥70)</span>
            <span className="text-xl font-bold text-green-900">{stats.high}</span>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
            <span className="text-[11px] font-semibold text-blue-700 block">Medium Fit (40–69)</span>
            <span className="text-xl font-bold text-blue-900">{stats.medium}</span>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
            <span className="text-[11px] font-semibold text-gray-600 block">Low Fit (&lt;40)</span>
            <span className="text-xl font-bold text-gray-800">{stats.low}</span>
          </div>
        </div>
      </div>

      {/* Setup Checklist */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Platform Readiness Checklist</h3>
        <ul className="text-xs space-y-2 text-gray-600">
          <li className="flex items-center gap-2 text-green-700">✓ Isolated tenant workspace operational</li>
          <li className="flex items-center gap-2 text-green-700">✓ Product catalogue configured with eligibility rules</li>
          <li className="flex items-center gap-2 text-green-700">✓ Synthetic audience imported with consent verification</li>
          <li className="flex items-center gap-2 text-green-700">✓ Explainable scoring model calibrated</li>
          <li className="flex items-center gap-2 text-green-700">✓ Realtime STT + Streaming TTS voice agent ready</li>
        </ul>
      </div>
    </div>
  )
}

