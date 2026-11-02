import React, { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'

/**
 * Step 2: Audience preview, filter chips, non-contactable warnings, and snapshot freezing.
 */
export default function WizardStep2Audience({
  campaignId,
  productId,
  audienceType,
  allowOverride,
  setAllowOverride,
  onNext,
  onBack,
}) {
  const { authFetch } = useAuth()
  const [filters, setFilters] = useState({
    bands: ['HIGH', 'MEDIUM'],
    eligibility: 'all',
    language: '',
  })
  const [previewData, setPreviewData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [resultSummary, setResultSummary] = useState(null)

  const fetchPreview = async () => {
    if (!productId || !audienceType) return
    try {
      setLoading(true)
      const res = await authFetch('/api/campaigns/audience/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audience_type: audienceType,
          product_id: productId,
          filters: {
            bands: filters.bands.length > 0 ? filters.bands : undefined,
            eligibility: filters.eligibility,
            language: filters.language || undefined,
          },
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setPreviewData(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPreview()
  }, [filters, productId, audienceType])

  const toggleBand = (band) => {
    setFilters((prev) => ({
      ...prev,
      bands: prev.bands.includes(band) ? prev.bands.filter((b) => b !== band) : [...prev.bands, band],
    }))
  }

  const handleSaveAudience = async () => {
    try {
      setSaving(true)
      const res = await authFetch(`/api/campaigns/${campaignId}/audience`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selection_mode: 'filter',
          filters: {
            bands: filters.bands.length > 0 ? filters.bands : undefined,
            eligibility: filters.eligibility,
            language: filters.language || undefined,
          },
          allow_ineligible_override: allowOverride,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setResultSummary(data)
        setSaveSuccess(true)
      } else {
        alert('Failed to save audience snapshot')
      }
    } catch (err) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  const summary = previewData?.summary || {}

  return (
    <div className="space-y-6">
      {/* Distribution Summary Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
        <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider mb-3">
          Available {audienceType} Distribution
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center text-xs">
          <div className="bg-gray-50 p-2 rounded-lg">
            <span className="text-[10px] text-gray-500 block">Total Scored</span>
            <span className="font-bold text-gray-900 text-sm">{summary.total || 0}</span>
          </div>
          <div className="bg-emerald-50 p-2 rounded-lg border border-emerald-100">
            <span className="text-[10px] text-emerald-600 block">High Fit</span>
            <span className="font-bold text-emerald-700 text-sm">{summary.high || 0}</span>
          </div>
          <div className="bg-amber-50 p-2 rounded-lg border border-amber-100">
            <span className="text-[10px] text-amber-600 block">Medium Fit</span>
            <span className="font-bold text-amber-700 text-sm">{summary.medium || 0}</span>
          </div>
          <div className="bg-rose-50 p-2 rounded-lg border border-rose-100">
            <span className="text-[10px] text-rose-600 block">Low Fit</span>
            <span className="font-bold text-rose-700 text-sm">{summary.low || 0}</span>
          </div>
          <div className="bg-blue-50 p-2 rounded-lg border border-blue-100">
            <span className="text-[10px] text-blue-600 block">Eligible</span>
            <span className="font-bold text-blue-700 text-sm">{summary.eligible || 0}</span>
          </div>
          <div className="bg-purple-50 p-2 rounded-lg border border-purple-100">
            <span className="text-[10px] text-purple-600 block">Contactable</span>
            <span className="font-bold text-purple-700 text-sm">{summary.contactable || 0}</span>
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs space-y-4">
        <h4 className="text-xs font-bold text-gray-900">Targeting Filters</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-[11px] font-semibold text-gray-600 mb-1.5">Fit Score Bands</label>
            <div className="flex gap-1.5">
              {['HIGH', 'MEDIUM', 'LOW'].map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => toggleBand(b)}
                  className={`px-3 py-1 rounded text-xs font-semibold border transition ${
                    filters.bands.includes(b)
                      ? 'bg-brand-600 text-white border-brand-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-gray-600 mb-1.5">Eligibility</label>
            <select
              value={filters.eligibility}
              onChange={(e) => setFilters({ ...filters, eligibility: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
            >
              <option value="all">All records</option>
              <option value="eligible">Eligible Only</option>
              <option value="not_eligible">Ineligible Only</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-gray-600 mb-1.5">Language</label>
            <select
              value={filters.language}
              onChange={(e) => setFilters({ ...filters, language: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg bg-white"
            >
              <option value="">Any Language</option>
              <option value="en-IN">English (en-IN)</option>
              <option value="hi-IN">Hindi (hi-IN)</option>
              <option value="te-IN">Telugu (te-IN)</option>
            </select>
          </div>
        </div>

        {/* Regulatory Warnings and Ineligible Override */}
        <div className="pt-2 border-t border-gray-100 space-y-2">
          <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
            <span><strong>DND Guard:</strong> Non-contactable individuals are strictly excluded.</span>
            <span className="font-semibold text-[11px] bg-amber-200 text-amber-900 px-2 py-0.5 rounded">{summary.not_contactable || 0} excluded</span>
          </div>

          <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer pt-1">
            <input type="checkbox" checked={allowOverride} onChange={(e) => setAllowOverride(e.target.checked)} className="rounded text-brand-600 focus:ring-brand-500" />
            <span>Allow inclusion of ineligible records (marked with eligible=false in snapshot)</span>
          </label>
        </div>
      </div>

      {/* Snapshot Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-gray-50 p-4 rounded-xl border border-gray-200">
        <div>
          <p className="text-xs font-bold text-gray-900">
            Matched Candidates: <span className="text-brand-600 font-mono">{previewData?.matched_count || 0}</span>
          </p>
          {resultSummary && (
            <p className="text-[11px] text-emerald-600 mt-0.5 font-medium">
              ✓ Frozen Snapshot: {resultSummary.recipient_count} recipients (Excluded {resultSummary.excluded_non_contactable} DND, {resultSummary.excluded_ineligible} ineligible)
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleSaveAudience}
          disabled={saving || (previewData?.matched_count || 0) === 0}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
        >
          {saving ? 'Freezing...' : saveSuccess ? '✓ Snapshot Saved' : 'Freeze Audience Snapshot'}
        </button>
      </div>

      {/* Navigation Buttons */}
      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
          ← Back to Details
        </button>
        <button onClick={onNext} disabled={!saveSuccess} className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50">
          Configure Voice Stack →
        </button>
      </div>
    </div>
  )
}
