import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Campaign Detail view showing status, recipients table, and versioned voice configurations.
 */
export default function CampaignDetail({ campaignId, onBack, onEdit }) {
  const { authFetch } = useAuth()
  const [campaign, setCampaign] = useState(null)
  const [recipients, setRecipients] = useState([])
  const [totalRecipients, setTotalRecipients] = useState(0)
  const [voiceConfig, setVoiceConfig] = useState(null)
  const [versions, setVersions] = useState([])
  const [preview, setPreview] = useState(null)
  const [activeTab, setActiveTab] = useState('recipients')
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      setLoading(true)
      const [cRes, rRes, vRes, versRes, prevRes] = await Promise.all([
        authFetch(`/api/campaigns/${campaignId}`),
        authFetch(`/api/campaigns/${campaignId}/recipients?limit=50`),
        authFetch(`/api/campaigns/${campaignId}/voice-config`),
        authFetch(`/api/campaigns/${campaignId}/voice-config/versions`),
        authFetch(`/api/campaigns/${campaignId}/preview`, { method: 'POST' }),
      ])
      if (cRes.ok) setCampaign(await cRes.json())
      if (rRes.ok) {
        const rData = await rRes.json()
        setRecipients(rData.recipients || [])
        setTotalRecipients(rData.total || 0)
      }
      if (vRes.ok) setVoiceConfig((await vRes.json()).config)
      if (versRes.ok) setVersions(await versRes.json())
      if (prevRes.ok) setPreview(await prevRes.json())
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [campaignId])

  const handleMarkReady = async () => {
    try {
      const res = await authFetch(`/api/campaigns/${campaignId}/mark-ready`, { method: 'POST' })
      if (res.ok) {
        alert('Campaign marked as READY!')
        loadData()
      } else {
        const err = await res.json()
        alert(err.detail?.message || 'Validation failed')
      }
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) return <div className="p-8 text-center text-xs text-gray-400">Loading campaign details...</div>
  if (!campaign) return <div className="p-8 text-center text-xs text-red-500">Campaign not found.</div>

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <button onClick={onBack} className="text-xs text-gray-500 hover:text-gray-900 mb-1 inline-flex items-center gap-1">
            ← Back to Campaigns
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">{campaign.name}</h1>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${
              campaign.status === 'ready' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              {campaign.status}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">Product: <strong className="text-gray-700">{campaign.product_name || campaign.product_id}</strong> • Audience: <strong className="capitalize text-gray-700">{campaign.audience_type}</strong></p>
        </div>

        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <>
              <button onClick={() => onEdit(campaign.id)} className="px-3.5 py-1.5 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
                Edit Wizard
              </button>
              <button onClick={handleMarkReady} className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs">
                Mark Ready
              </button>
            </>
          )}
          <button disabled className="px-3.5 py-1.5 bg-gray-200 text-gray-400 rounded-lg text-xs font-semibold cursor-not-allowed">
            Dispatch (Phase 5)
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 gap-4 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('recipients')}
          className={`pb-2 transition ${activeTab === 'recipients' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500 hover:text-gray-900'}`}
        >
          Audience Snapshot ({totalRecipients})
        </button>
        <button
          onClick={() => setActiveTab('config')}
          className={`pb-2 transition ${activeTab === 'config' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500 hover:text-gray-900'}`}
        >
          Voice Config (v{campaign.current_voice_config_version || 1})
        </button>
        <button
          onClick={() => setActiveTab('versions')}
          className={`pb-2 transition ${activeTab === 'versions' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500 hover:text-gray-900'}`}
        >
          Version History ({versions.length})
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`pb-2 transition ${activeTab === 'preview' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500 hover:text-gray-900'}`}
        >
          Sanitized Payload Preview
        </button>
      </div>

      {/* Tab 1: Recipients */}
      {activeTab === 'recipients' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-2.5 px-4">Name</th>
                <th className="py-2.5 px-4">Language</th>
                <th className="py-2.5 px-4">Fit Score</th>
                <th className="py-2.5 px-4">Band</th>
                <th className="py-2.5 px-4">Eligibility</th>
                <th className="py-2.5 px-4">Snapshot Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recipients.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50/50">
                  <td className="py-2.5 px-4 font-semibold text-gray-900">{r.first_name}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-600">{r.preferred_language}</td>
                  <td className="py-2.5 px-4 font-mono font-bold text-gray-900">{r.fit_score}</td>
                  <td className="py-2.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      r.band === 'HIGH' ? 'bg-emerald-50 text-emerald-700' : r.band === 'MEDIUM' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'
                    }`}>{r.band}</span>
                  </td>
                  <td className="py-2.5 px-4">{r.eligible ? <span className="text-emerald-600 font-semibold">Eligible</span> : <span className="text-rose-500">Ineligible (Overridden)</span>}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-500">{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Voice Config */}
      {activeTab === 'config' && voiceConfig && (
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3 text-xs">
          <div><span className="font-bold text-gray-700">Opening Message:</span> <p className="mt-1 p-2 bg-gray-50 rounded text-gray-800 font-mono text-[11px]">{voiceConfig.opening_message}</p></div>
          <div><span className="font-bold text-gray-700">System Instructions:</span> <p className="mt-1 p-2 bg-gray-50 rounded text-gray-800 font-mono text-[11px]">{voiceConfig.system_prompt}</p></div>
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div><span className="font-bold text-gray-700">Tone:</span> <p className="text-gray-600">{voiceConfig.tone}</p></div>
            <div><span className="font-bold text-gray-700">Default Language:</span> <p className="font-mono text-gray-600">{voiceConfig.default_language}</p></div>
          </div>
        </div>
      )}

      {/* Tab 3: Version History */}
      {activeTab === 'versions' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-2.5 px-4">Version</th>
                <th className="py-2.5 px-4">Created At</th>
                <th className="py-2.5 px-4">Opening Script Preview</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {versions.map((v) => (
                <tr key={v.version} className="hover:bg-gray-50/50">
                  <td className="py-2.5 px-4 font-mono font-bold text-brand-600">v{v.version}</td>
                  <td className="py-2.5 px-4 text-gray-500">{new Date(v.created_at).toLocaleString()}</td>
                  <td className="py-2.5 px-4 text-gray-700 truncate max-w-md">{v.config?.opening_message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 4: Sanitized Preview */}
      {activeTab === 'preview' && (
        <div className="bg-gray-900 text-gray-100 p-4 rounded-xl font-mono text-xs overflow-x-auto">
          <pre>{JSON.stringify(preview, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
