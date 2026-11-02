import React from 'react'

/**
 * Modal displaying applicant profile with ranked product matches and plain-English explanations.
 */
export default function PersonDetailModal({ person, onClose }) {
  if (!person) return null

  const matches = person.product_matches || []

  const bandColors = {
    High: 'bg-green-100 text-green-800 border-green-200',
    Medium: 'bg-blue-100 text-blue-800 border-blue-200',
    Low: 'bg-gray-100 text-gray-800 border-gray-200',
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl space-y-5 my-8">
        {/* Header */}
        <div className="flex justify-between items-start border-b pb-4">
          <div>
            <span className="text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono font-semibold uppercase">
              {person.record_type} · {person.external_ref}
            </span>
            <h2 className="text-base font-bold text-gray-900 mt-1">{person.full_name}</h2>
            <p className="text-xs text-gray-500">{person.phone} · {person.email || 'No email'} · {person.city}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">✕</button>
        </div>

        {/* Profile Demographics */}
        <div className="grid grid-cols-4 gap-2.5 text-xs bg-gray-50 p-3 rounded-xl border border-gray-100">
          <div>
            <span className="text-[10px] text-gray-400 block">Monthly Income</span>
            <span className="font-bold text-gray-900">₹{person.monthly_income_inr?.toLocaleString('en-IN')}</span>
          </div>
          <div>
            <span className="text-[10px] text-gray-400 block">Credit Score</span>
            <span className="font-bold text-gray-900">{person.credit_score}</span>
          </div>
          <div>
            <span className="text-[10px] text-gray-400 block">Age &amp; Employment</span>
            <span className="font-bold text-gray-900">{person.age} yrs · {person.employment_type}</span>
          </div>
          <div>
            <span className="text-[10px] text-gray-400 block">Consent / Contact</span>
            <span className={`font-bold ${person.contactable ? 'text-green-700' : 'text-red-700'}`}>
              {person.contactable ? 'Contactable' : 'Do Not Contact'}
            </span>
          </div>
        </div>

        {/* Ranked Product Matches */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
              Ranked Product Fit Matches ({matches.length})
            </h3>
            <span className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              Trained on synthetic data
            </span>
          </div>

          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {matches.map((m, idx) => (
              <div key={m.match_id || idx} className="border border-gray-200 rounded-xl p-4 bg-white shadow-xs space-y-2">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-gray-900">#{idx + 1} {m.product_name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${bandColors[m.band]}`}>
                      {m.band} Fit ({m.fit_score}/100)
                    </span>
                  </div>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                    m.eligible ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                  }`}>
                    {m.eligible ? '✓ Underwriting Eligible' : '✕ Ineligible'}
                  </span>
                </div>

                {/* Failed Rules if Ineligible */}
                {!m.eligible && m.failed_rules?.length > 0 && (
                  <div className="bg-red-50 text-red-800 text-[11px] p-2 rounded-lg border border-red-100">
                    <span className="font-bold block text-[10px] uppercase">Failed Eligibility Rules:</span>
                    <ul className="list-disc list-inside">
                      {m.failed_rules.map((rule, ri) => <li key={ri}>{rule}</li>)}
                    </ul>
                  </div>
                )}

                {/* Plain English Explanations */}
                <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100 text-[11px] space-y-1">
                  <span className="font-semibold text-gray-500 uppercase block text-[10px]">
                    Top Contributing Scoring Signals:
                  </span>
                  <ul className="space-y-0.5 text-gray-700">
                    {(m.explanation || []).map((exp, ei) => (
                      <li key={ei} className="flex items-center gap-1.5">
                        <span className="text-brand-600 font-bold">•</span>
                        <span>{exp}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end pt-2 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  )
}
