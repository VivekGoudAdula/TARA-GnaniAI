import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Campaigns list dashboard displaying tenant campaigns, status badges, and management actions.
 */
export default function CampaignsList({ onNewCampaign, onViewCampaign }) {
  const { authFetch } = useAuth()
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCampaigns = async () => {
    try {
      setLoading(true)
      const res = await authFetch('/api/campaigns')
      if (!res.ok) throw new Error('Failed to fetch campaigns')
      const data = await res.json()
      setCampaigns(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCampaigns()
  }, [])

  const handleDelete = async (campaignId, e) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this campaign?')) return
    try {
      const res = await authFetch(`/api/campaigns/${campaignId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete campaign')
      fetchCampaigns()
    } catch (err) {
      alert(err.message)
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ready':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Ready</span>
      case 'draft':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">Draft</span>
      case 'cancelled':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-600 border border-gray-200">Cancelled</span>
      default:
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700">{status}</span>
    }
  }

  const readyCount = campaigns.filter((c) => c.status === 'ready').length
  const draftCount = campaigns.filter((c) => c.status === 'draft').length

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Campaign Builder</h1>
          <p className="text-xs text-gray-500 mt-1">
            Target audiences, configure multilingual voice prompts, and stage verified voice outreach.
          </p>
        </div>
        <button
          onClick={onNewCampaign}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs transition"
        >
          <span>+</span> Create Campaign
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">Total Campaigns</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{campaigns.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[11px] font-medium text-emerald-600 uppercase tracking-wider">Ready for Outreach</p>
          <p className="text-2xl font-bold text-emerald-700 mt-1">{readyCount}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
          <p className="text-[11px] font-medium text-amber-600 uppercase tracking-wider">In Draft</p>
          <p className="text-2xl font-bold text-amber-700 mt-1">{draftCount}</p>
        </div>
      </div>

      {/* Campaign Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-xs text-gray-400">Loading campaigns...</div>
        ) : error ? (
          <div className="p-8 text-center text-xs text-red-500">{error}</div>
        ) : campaigns.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-brand-50 text-brand-600 flex items-center justify-center text-xl mb-3">
              📢
            </div>
            <h3 className="text-sm font-semibold text-gray-900">No campaigns created yet</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
              Create your first campaign to target scored customers or leads with custom multilingual voice scripts.
            </p>
            <button
              onClick={onNewCampaign}
              className="mt-4 px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              Create Campaign
            </button>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/75 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-3 px-4">Campaign Name</th>
                <th className="py-3 px-4">Product</th>
                <th className="py-3 px-4">Audience</th>
                <th className="py-3 px-4">Recipients</th>
                <th className="py-3 px-4">Config Ver</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs">
              {campaigns.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => onViewCampaign(c.id)}
                  className="hover:bg-gray-50/75 cursor-pointer transition"
                >
                  <td className="py-3 px-4 font-semibold text-gray-900">
                    <div>{c.name}</div>
                    {c.objective && <div className="text-[11px] text-gray-400 font-normal truncate max-w-xs">{c.objective}</div>}
                  </td>
                  <td className="py-3 px-4 text-gray-700">{c.product_name || c.product_id}</td>
                  <td className="py-3 px-4 capitalize text-gray-600">{c.audience_type}</td>
                  <td className="py-3 px-4 font-mono font-medium text-gray-900">{c.recipient_count || 0}</td>
                  <td className="py-3 px-4">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 bg-gray-100 rounded text-gray-600">
                      v{c.current_voice_config_version || 1}
                    </span>
                  </td>
                  <td className="py-3 px-4">{getStatusBadge(c.status)}</td>
                  <td className="py-3 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onViewCampaign(c.id)}
                      className="text-xs text-brand-600 hover:text-brand-800 font-semibold"
                    >
                      View
                    </button>
                    {['draft', 'cancelled'].includes(c.status) && (
                      <button
                        onClick={(e) => handleDelete(c.id, e)}
                        className="text-xs text-gray-400 hover:text-red-600 font-semibold"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
