import React from 'react'

/**
 * Step 1: Campaign details, product selection, audience type, and objectives.
 */
export default function WizardStep1Details({
  campaignData,
  setCampaignData,
  products,
  onNext,
  isEditMode,
}) {
  const isValid =
    campaignData.name.trim().length >= 2 &&
    campaignData.product_id &&
    campaignData.audience_type

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <label className="block text-xs font-semibold text-gray-700 mb-1">
          Campaign Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={campaignData.name}
          onChange={(e) => setCampaignData({ ...campaignData, name: e.target.value })}
          placeholder="e.g. Festive Personal Loan Outreach 2026"
          className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Product <span className="text-red-500">*</span>
          </label>
          <select
            value={campaignData.product_id}
            disabled={isEditMode}
            onChange={(e) => setCampaignData({ ...campaignData, product_id: e.target.value })}
            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:bg-gray-100"
          >
            <option value="">Select an active product...</option>
            {products.map((p) => (
              <option key={p.product_id} value={p.product_id}>
                {p.name} ({p.category})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Target Audience <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-2">
            {['customers', 'leads'].map((type) => (
              <button
                key={type}
                type="button"
                disabled={isEditMode}
                onClick={() => setCampaignData({ ...campaignData, audience_type: type })}
                className={`flex-1 py-2 text-xs font-semibold rounded-lg capitalize border transition ${
                  campaignData.audience_type === type
                    ? 'bg-brand-50 border-brand-500 text-brand-700 shadow-xs'
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                } ${isEditMode ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-700 mb-1">
          Campaign Objective
        </label>
        <input
          type="text"
          value={campaignData.objective}
          onChange={(e) => setCampaignData({ ...campaignData, objective: e.target.value })}
          placeholder="e.g. Inform eligible pre-approved users of special interest rates"
          className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-700 mb-1">
          Description & Notes
        </label>
        <textarea
          rows={3}
          value={campaignData.description}
          onChange={(e) => setCampaignData({ ...campaignData, description: e.target.value })}
          placeholder="Optional notes for compliance, audit, or team context..."
          className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      <div className="pt-4 flex justify-end">
        <button
          onClick={onNext}
          disabled={!isValid}
          className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50 transition"
        >
          Continue to Audience Targeting →
        </button>
      </div>
    </div>
  )
}
