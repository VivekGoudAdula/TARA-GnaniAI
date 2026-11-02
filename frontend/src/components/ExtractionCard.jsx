import React from 'react'

/**
 * Renders the structured post-call extraction summary.
 */
export default function ExtractionCard({ data, durationSeconds }) {
  if (!data) return null

  const outcomeColors = {
    agreed: 'bg-green-100 text-green-800 border-green-200',
    declined: 'bg-red-100 text-red-800 border-red-200',
    callback_requested: 'bg-blue-100 text-blue-800 border-blue-200',
    wrong_number: 'bg-gray-100 text-gray-800 border-gray-200',
    unanswered: 'bg-amber-100 text-amber-800 border-amber-200',
  }

  const sentimentColors = {
    positive: 'text-green-600',
    neutral: 'text-gray-600',
    negative: 'text-red-600',
  }

  const fields = data.fields_collected || {}

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b pb-3 border-gray-100">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Post-Call Extraction</h3>
          <p className="text-xs text-gray-500">Call duration: {durationSeconds}s</p>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide border ${
            outcomeColors[data.outcome] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {data.outcome || 'Unknown'}
        </span>
      </div>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Call Summary</h4>
        <p className="text-sm text-gray-800 bg-gray-50 p-3 rounded-lg border border-gray-100 leading-relaxed">
          {data.call_summary || 'No summary available.'}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-xs text-gray-500 block">User Sentiment</span>
          <span className={`text-sm font-semibold capitalize ${sentimentColors[data.user_sentiment] || ''}`}>
            {data.user_sentiment || 'Neutral'}
          </span>
        </div>
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-xs text-gray-500 block">Follow-up Needed</span>
          <span className="text-sm font-semibold text-gray-800">
            {data.follow_up_needed ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
          <span className="text-xs text-gray-500 block">Confidence</span>
          <span className="text-sm font-semibold text-gray-800">
            {Math.round((data.confidence || 0) * 100)}%
          </span>
        </div>
      </div>

      <div>
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">Collected Fields</h4>
        {Object.keys(fields).length === 0 ? (
          <p className="text-xs text-gray-400 italic">No specific fields were collected during this turn.</p>
        ) : (
          <div className="space-y-1.5">
            {Object.entries(fields).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs py-1 px-2 bg-gray-50 rounded border border-gray-100">
                <span className="font-medium text-gray-600">{k}:</span>
                <span className="text-gray-900 font-semibold">{String(v || 'N/A')}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
