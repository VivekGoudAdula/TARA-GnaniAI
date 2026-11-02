import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import CampaignLaunchModal from './campaign_detail/CampaignLaunchModal'
import CampaignOutcomesTab from './campaign_detail/CampaignOutcomesTab'

/**
 * Campaign Detail view with tester call links, lifecycle controls, and live outcomes.
 */
export default function CampaignDetail({ campaignId, onBack, onEdit }) {
  const { authFetch } = useAuth()
  const [campaign, setCampaign] = useState(null)
  const [recipients, setRecipients] = useState([])
  const [totalRecipients, setTotalRecipients] = useState(0)
  const [voiceConfig, setVoiceConfig] = useState(null)
  const [activeTab, setActiveTab] = useState('recipients')
  const [showLaunchModal, setShowLaunchModal] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    try {
      setLoading(true)
      const [cRes, rRes, vRes] = await Promise.all([
        authFetch(`/api/campaigns/${campaignId}`),
        authFetch(`/api/campaigns/${campaignId}/recipients?limit=50`),
        authFetch(`/api/campaigns/${campaignId}/voice-config`),
      ])
      if (cRes.ok) setCampaign(await cRes.json())
      if (rRes.ok) {
        const rData = await rRes.json()
        setRecipients(rData.recipients || [])
        setTotalRecipients(rData.total || 0)
      }
      if (vRes.ok) setVoiceConfig((await vRes.json()).config)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [campaignId])

  const handleLifecycle = async (action) => {
    try {
      const res = await authFetch(`/api/campaigns/${campaignId}/${action}`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || `Action ${action} failed`)
      }
      loadData()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleCopyTesterLink = (taskToken) => {
    if (!taskToken) {
      alert('No tester link available yet. Launch campaign in test mode to generate tester links.')
      return
    }
    const url = `${window.location.origin}/call/${taskToken}`
    navigator.clipboard.writeText(url)
    alert(`Tester link copied to clipboard!\n${url}`)
  }

  if (loading) return <div className="p-8 text-center text-xs text-gray-400">Loading campaign details...</div>
  if (!campaign) return <div className="p-8 text-center text-xs text-red-500">Campaign not found.</div>

  const isReady = campaign.status === 'ready'
  const isRunning = campaign.status === 'running'
  const isPaused = campaign.status === 'paused'

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <button onClick={onBack} className="text-xs text-gray-500 hover:text-gray-900 mb-1 inline-flex items-center gap-1">
            ← Back to Campaigns
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">{campaign.name}</h1>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${
              isRunning ? 'bg-emerald-100 text-emerald-800 animate-pulse' : isReady ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              {campaign.status}
            </span>
            <span className="text-[10px] font-mono bg-amber-50 text-amber-800 px-2 py-0.5 rounded border border-amber-200 font-bold">
              TEST MODE ONLY
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">Product: <strong className="text-gray-700">{campaign.product_name || campaign.product_id}</strong> • Audience: <strong className="capitalize text-gray-700">{campaign.audience_type}</strong></p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <button onClick={() => onEdit(campaign.id)} className="px-3.5 py-1.5 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
              Edit Wizard
            </button>
          )}
          {isReady && (
            <button onClick={() => setShowLaunchModal(true)} className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs">
              🚀 Launch (TEST Mode)
            </button>
          )}
          {isRunning && (
            <button onClick={() => handleLifecycle('pause')} className="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-semibold shadow-xs">
              ⏸ Pause
            </button>
          )}
          {isPaused && (
            <button onClick={() => handleLifecycle('resume')} className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs">
              ▶ Resume
            </button>
          )}
          {['running', 'paused'].includes(campaign.status) && (
            <button onClick={() => handleLifecycle('cancel')} className="px-3.5 py-1.5 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded-lg text-xs font-semibold">
              Cancel Campaign
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 gap-4 text-xs font-semibold">
        <button onClick={() => setActiveTab('recipients')} className={`pb-2 ${activeTab === 'recipients' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500'}`}>
          Audience Snapshot ({totalRecipients})
        </button>
        <button onClick={() => setActiveTab('outcomes')} className={`pb-2 ${activeTab === 'outcomes' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500'}`}>
          Live Outcomes &amp; Metrics
        </button>
        <button onClick={() => setActiveTab('config')} className={`pb-2 ${activeTab === 'config' ? 'border-b-2 border-brand-600 text-brand-700' : 'text-gray-500'}`}>
          Voice Script (v{campaign.current_voice_config_version || 1})
        </button>
      </div>

      {/* Tab 1: Recipients Table with Tester Link Button */}
      {activeTab === 'recipients' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th className="py-2.5 px-4">Name</th>
                <th className="py-2.5 px-4">Language</th>
                <th className="py-2.5 px-4">Fit Score</th>
                <th className="py-2.5 px-4">Band</th>
                <th className="py-2.5 px-4">Dispatch Status</th>
                <th className="py-2.5 px-4 text-right">Tester Call Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recipients.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50/50">
                  <td className="py-2.5 px-4 font-semibold text-gray-900">{r.first_name}</td>
                  <td className="py-2.5 px-4 font-mono text-gray-600">{r.preferred_language}</td>
                  <td className="py-2.5 px-4 font-mono font-bold text-gray-900">{r.fit_score}</td>
                  <td className="py-2.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.band === 'HIGH' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{r.band}</span>
                  </td>
                  <td className="py-2.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'blocked' ? 'bg-rose-50 text-rose-700' : r.status === 'queued' ? 'bg-amber-50 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>
                      {r.status || 'PENDING'}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    {r.task_token ? (
                      <button onClick={() => handleCopyTesterLink(r.task_token)} className="px-2.5 py-1 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded text-xs font-semibold">
                        🔗 Copy Tester Link
                      </button>
                    ) : (
                      <span className="text-[11px] text-gray-400 italic">Available after launch</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Live Outcomes */}
      {activeTab === 'outcomes' && <CampaignOutcomesTab campaignId={campaignId} authFetch={authFetch} />}

      {/* Tab 3: Script Preview */}
      {activeTab === 'config' && voiceConfig && (
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-3 text-xs">
          <div><span className="font-bold text-gray-700">Opening Message:</span> <p className="mt-1 p-2 bg-gray-50 rounded font-mono text-[11px] text-gray-800">{voiceConfig.opening_message}</p></div>
          <div><span className="font-bold text-gray-700">System Prompt:</span> <p className="mt-1 p-2 bg-gray-50 rounded font-mono text-[11px] text-gray-800">{voiceConfig.system_prompt}</p></div>
        </div>
      )}

      {/* Launch Modal */}
      {showLaunchModal && (
        <CampaignLaunchModal campaign={campaign} onClose={() => setShowLaunchModal(false)} onLaunchSuccess={loadData} authFetch={authFetch} />
      )}
    </div>
  )
}
