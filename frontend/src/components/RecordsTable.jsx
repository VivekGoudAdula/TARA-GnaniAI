import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import PersonDetailModal from './PersonDetailModal'

const API_BASE = 'http://localhost:8000/api'

/**
 * Universal table for Customers and Leads with band filtering, summary counts, and detail inspector.
 */
export default function RecordsTable({ recordType }) {
  const { token } = useAuth()
  const [data, setData] = useState({ items: [], total: 0, high_count: 0, medium_count: 0, low_count: 0 })
  const [bandFilter, setBandFilter] = useState('')
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [loading, setLoading] = useState(false)
  const [scoring, setScoring] = useState(false)

  const loadRecords = async () => {
    setLoading(true)
    try {
      const url = new URL(`${API_BASE}/${recordType}`)
      if (bandFilter) url.searchParams.set('band', bandFilter)

      const res = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${token}` },
      })
      const resJson = await res.json()
      setData(resJson)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const runScoring = async () => {
    setScoring(true)
    try {
      const res = await fetch(`${API_BASE}/scoring/run`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Scoring failed')
      await loadRecords()
    } catch (err) {
      alert(err.message)
    } finally {
      setScoring(false)
    }
  }

  const openDetail = async (recordId) => {
    try {
      const res = await fetch(`${API_BASE}/${recordType}/${recordId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const detail = await res.json()
      setSelectedPerson(detail)
    } catch (err) {
      alert(err.message)
    }
  }

  useEffect(() => {
    if (token) loadRecords()
  }, [token, recordType, bandFilter])

  const title = recordType === 'customers' ? 'Internal Customers' : 'External Leads'
  const bandBadge = (band) => {
    if (band === 'High') return 'bg-green-100 text-green-800 border-green-200'
    if (band === 'Medium') return 'bg-blue-100 text-blue-800 border-blue-200'
    return 'bg-gray-100 text-gray-800 border-gray-200'
  }

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-gray-900">{title}</h1>
            <span className="text-[10px] bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-semibold">
              Trained on synthetic data
            </span>
          </div>
          <p className="text-xs text-gray-500">Audience scoring, eligibility, and outreach fit ranking</p>
        </div>

        <button
          onClick={runScoring}
          disabled={scoring}
          className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
        >
          {scoring ? 'Re-scoring...' : '⚡ Run Scoring'}
        </button>
      </div>

      {/* Summary Counts Bar */}
      <div className="grid grid-cols-4 gap-3 bg-white border border-gray-200 rounded-xl p-3 shadow-sm text-xs">
        <button
          onClick={() => setBandFilter('')}
          className={`p-2 rounded-lg text-left transition-all ${!bandFilter ? 'bg-gray-100 font-bold' : 'hover:bg-gray-50'}`}
        >
          <span className="text-[10px] text-gray-500 block">Total {title}</span>
          <span className="text-base font-bold text-gray-900">{data.total}</span>
        </button>
        <button
          onClick={() => setBandFilter('High')}
          className={`p-2 rounded-lg text-left transition-all ${bandFilter === 'High' ? 'bg-green-100 font-bold' : 'hover:bg-green-50'}`}
        >
          <span className="text-[10px] text-green-700 block">High Fit (≥70)</span>
          <span className="text-base font-bold text-green-900">{data.high_count}</span>
        </button>
        <button
          onClick={() => setBandFilter('Medium')}
          className={`p-2 rounded-lg text-left transition-all ${bandFilter === 'Medium' ? 'bg-blue-100 font-bold' : 'hover:bg-blue-50'}`}
        >
          <span className="text-[10px] text-blue-700 block">Medium Fit (40–69)</span>
          <span className="text-base font-bold text-blue-900">{data.medium_count}</span>
        </button>
        <button
          onClick={() => setBandFilter('Low')}
          className={`p-2 rounded-lg text-left transition-all ${bandFilter === 'Low' ? 'bg-gray-200 font-bold' : 'hover:bg-gray-50'}`}
        >
          <span className="text-[10px] text-gray-500 block">Low Fit (&lt;40)</span>
          <span className="text-base font-bold text-gray-800">{data.low_count}</span>
        </button>
      </div>

      {/* Records Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50 text-gray-500 font-semibold">
            <tr>
              <th className="px-4 py-3 text-left">Applicant</th>
              <th className="px-4 py-3 text-left">Income &amp; Score</th>
              <th className="px-4 py-3 text-left">Top Product Match</th>
              <th className="px-4 py-3 text-left">Fit Band</th>
              <th className="px-4 py-3 text-left">Contact Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-700">
            {data.items.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-400">
                  {loading ? 'Loading records...' : 'No records match active filter.'}
                </td>
              </tr>
            ) : (
              data.items.map((row) => (
                <tr key={row.record_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="font-semibold text-gray-900">{row.full_name}</div>
                    <div className="text-[10px] text-gray-400 font-mono">{row.phone} · {row.city}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div>₹{row.monthly_income_inr?.toLocaleString('en-IN')}/mo</div>
                    <div className="text-[10px] text-gray-400">Score: {row.credit_score}</div>
                  </td>
                  <td className="px-4 py-3">
                    {row.top_match ? (
                      <div>
                        <span className="font-semibold text-gray-800">{row.top_match.product_name}</span>
                        <div className="text-[10px] text-gray-400">
                          {row.top_match.eligible ? '✓ Eligible' : '✕ Ineligible'}
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-400 italic">Not scored</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.top_match ? (
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${bandBadge(row.top_match.band)}`}>
                        {row.top_match.band} ({row.top_match.fit_score})
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-semibold ${row.contactable ? 'text-green-700' : 'text-red-700'}`}>
                      {row.contactable ? 'Contactable' : 'DND / No Consent'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => openDetail(row.record_id)}
                      className="text-brand-600 hover:text-brand-800 font-semibold"
                    >
                      View Fits
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedPerson && (
        <PersonDetailModal person={selectedPerson} onClose={() => setSelectedPerson(null)} />
      )}
    </div>
  )
}

