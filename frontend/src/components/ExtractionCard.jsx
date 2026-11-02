import React from 'react'

/**
 * Renders the structured post-call extraction summary based on the SessionExtraction schema.
 */
export default function ExtractionCard({ data, durationSeconds }) {
  if (!data) return null

  const outcomeColors = {
    interested: 'bg-green-100 text-green-800 border-green-200',
    not_interested: 'bg-red-100 text-red-800 border-red-200',
    callback: 'bg-blue-100 text-blue-800 border-blue-200',
    no_answer: 'bg-amber-100 text-amber-800 border-amber-200',
    unclear: 'bg-gray-100 text-gray-800 border-gray-200',
  }

  const interestColors = {
    high: 'text-green-600',
    medium: 'text-blue-600',
    low: 'text-amber-600',
    none: 'text-red-600',
    unknown: 'text-gray-500',
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b pb-3 border-gray-100">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Post-Call Extraction</h3>
          <p className="text-[11px] text-gray-500">Call duration: {durationSeconds || 0}s</p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide border ${
            outcomeColors[data.outcome] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {data.outcome || 'unclear'}
        </span>
      </div>

      <div>
        <h4 className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Summary</h4>
        <p className="text-xs text-gray-800 bg-gray-50 p-3 rounded-lg border border-gray-100 leading-relaxed">
          {data.summary || 'No summary available.'}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-[10px] text-gray-500 block">Interest Level</span>
          <span className={`font-semibold capitalize ${interestColors[data.interest_level] || ''}`}>
            {data.interest_level || 'unknown'}
          </span>
        </div>
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-[10px] text-gray-500 block">Loan Amount (INR)</span>
          <span className="font-semibold text-gray-900">
            {data.loan_amount_inr != null ? `₹${Number(data.loan_amount_inr).toLocaleString('en-IN')}` : 'None spoken'}
          </span>
        </div>
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-[10px] text-gray-500 block">Callback Time</span>
          <span className="font-semibold text-gray-900">
            {data.callback_time || 'None requested'}
          </span>
        </div>
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-[10px] text-gray-500 block">Languages Heard</span>
          <span className="font-semibold text-gray-900">
            {Array.isArray(data.language_used) && data.language_used.length > 0
              ? data.language_used.join(', ')
              : 'en-IN'}
          </span>
        </div>
      </div>
    </div>
  )
}
