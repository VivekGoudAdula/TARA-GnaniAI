import React, { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'

/**
 * Step 4: Final validation checklist, sanitized payload inspection, and readiness transition.
 */
export default function WizardStep4Review({ campaignId, onFinish, onBack }) {
  const { authFetch } = useAuth()
  const [validation, setValidation] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [marking, setMarking] = useState(false)
  const [isReady, setIsReady] = useState(false)

  const runAudit = async () => {
    try {
      setLoading(true)
      const [valRes, prevRes] = await Promise.all([
        authFetch(`/api/campaigns/${campaignId}/validate`, { method: 'POST' }),
        authFetch(`/api/campaigns/${campaignId}/preview`, { method: 'POST' }),
      ])
      if (valRes.ok) setValidation(await valRes.json())
      if (prevRes.ok) setPreview(await prevRes.json())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runAudit()
  }, [campaignId])

  const handleMarkReady = async () => {
    try {
      setMarking(true)
      const res = await authFetch(`/api/campaigns/${campaignId}/mark-ready`, { method: 'POST' })
      if (res.ok) {
        setIsReady(true)
        alert('Campaign successfully marked as READY!')
        onFinish()
      } else {
        const err = await res.json()
        alert(err.detail?.message || 'Campaign validation failed')
      }
    } catch (err) {
      alert(err.message)
    } finally {
      setMarking(false)
    }
  }

  if (loading) return <div className="p-8 text-center text-xs text-gray-400">Auditing campaign readiness...</div>

  const isValid = validation?.valid === true

  return (
    <div className="space-y-6">
      {/* Validation Checklist Banner */}
      <div className={`p-4 rounded-xl border ${isValid ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
        <div className="flex items-start gap-3">
          <span className="text-xl">{isValid ? '✅' : '⚠️'}</span>
          <div>
            <h3 className={`text-xs font-bold ${isValid ? 'text-emerald-900' : 'text-rose-900'}`}>
              {isValid ? 'Ready for Deployment Stage' : 'Validation Issues Detected'}
            </h3>
            <p className={`text-[11px] mt-0.5 ${isValid ? 'text-emerald-700' : 'text-rose-700'}`}>
              {isValid
                ? 'All prerequisite checks passed: Active product linked, valid recipient snapshot, verified AI disclosure, and safe template variables.'
                : 'The campaign cannot be marked ready until the following items are resolved:'}
            </p>
            {!isValid && validation?.issues && (
              <ul className="mt-2 list-disc list-inside text-xs text-rose-800 space-y-0.5">
                {validation.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* Voice Stack Sanitized Payload Inspection */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3">
        <div className="flex justify-between items-center">
          <div>
            <h4 className="text-xs font-bold text-gray-900">What the Voice Stack Receives</h4>
            <p className="text-[11px] text-gray-500">
              Sanitized outbound dispatch payload. Financial metrics (income, credit score) and contact info are strictly omitted.
            </p>
          </div>
          <span className="text-[10px] font-mono bg-brand-50 text-brand-700 px-2 py-0.5 rounded border border-brand-200">
            Phase 5 Contract Compliant
          </span>
        </div>

        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-[11px] overflow-x-auto max-h-72">
          {preview ? (
            <pre>{JSON.stringify(preview, null, 2)}</pre>
          ) : (
            <span className="text-gray-400">// No preview available. Ensure recipients are selected.</span>
          )}
        </div>
      </div>

      {/* Final Action Controls */}
      <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <p className="text-xs font-bold text-gray-900">Next Stage Action</p>
          <p className="text-[11px] text-gray-500">
            Marking ready locks configuration and approves campaign for automated dispatch.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleMarkReady}
            disabled={!isValid || marking || isReady}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50"
          >
            {marking ? 'Marking...' : isReady ? '✓ Marked Ready' : 'Mark Ready for Outreach'}
          </button>

          <button
            type="button"
            disabled
            className="px-4 py-2 bg-gray-200 text-gray-400 rounded-lg text-xs font-semibold cursor-not-allowed flex items-center gap-1.5"
          >
            <span>🚀</span> Launch Dispatch <span className="bg-gray-300 text-gray-600 text-[10px] px-1 py-0.2 rounded">Phase 5</span>
          </button>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
          ← Back to Voice Config
        </button>
        <button onClick={onFinish} className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-semibold">
          Done / Return to Campaigns
        </button>
      </div>
    </div>
  )
}
