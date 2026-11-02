import React, { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'

/**
 * Step 3: Multi-channel configuration, prompt engineering, template validation, and voice settings.
 */
export default function WizardStep3Voice({ campaignId, onNext, onBack }) {
  const { authFetch } = useAuth()
  const [activeChannel, setActiveChannel] = useState('voice')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [currentVersion, setCurrentVersion] = useState(1)
  const [previewPayload, setPreviewPayload] = useState(null)
  const [previewError, setPreviewError] = useState(null)

  const [voiceConfig, setVoiceConfig] = useState({
    default_language: 'en-IN',
    tone: 'polite, helpful, professional',
    system_prompt: 'You are an AI representative calling on behalf of {{bank_name}} regarding {{product_name}} for {{first_name}}.',
    opening_message: 'Hello {{first_name}}, I am an automated AI assistant calling from {{bank_name}} regarding {{product_name}}. Do you have a moment?',
    conversation_objective: 'Explain product benefits and determine interest in application or callback.',
    info_to_collect: [{ field: 'interest', question: 'Would you like to proceed?', required: true }],
    success_condition: 'Customer expresses interest or agrees to callback.',
    closing_message: 'Thank you for your time, {{first_name}}. Have a wonderful day!',
    max_turns: 8,
    retry_policy: { max_attempts: 3, retry_interval_minutes: 60 },
  })

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true)
        const res = await authFetch(`/api/campaigns/${campaignId}/voice-config`)
        if (res.ok) {
          const data = await res.json()
          if (data.config) setVoiceConfig(data.config)
          if (data.version) setCurrentVersion(data.version)
        }
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    loadConfig()
  }, [campaignId])

  const handleSaveConfig = async () => {
    try {
      setSaving(true)
      const res = await authFetch(`/api/campaigns/${campaignId}/voice-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(voiceConfig),
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentVersion(data.version)
        alert(`Voice config saved as version ${data.version}!`)
      } else {
        const err = await res.json()
        alert(err.detail?.[0]?.msg || 'Validation failed: Check template variables')
      }
    } catch (err) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleTestPreview = async () => {
    try {
      setPreviewError(null)
      const res = await authFetch(`/api/campaigns/${campaignId}/preview`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setPreviewPayload(data)
      } else {
        const err = await res.json()
        setPreviewError(err.detail || 'Preview generation failed')
      }
    } catch (err) {
      setPreviewError(err.message)
    }
  }

  if (loading) return <div className="p-8 text-center text-xs text-gray-400">Loading voice configuration...</div>

  return (
    <div className="space-y-6">
      {/* Channel Tabs */}
      <div className="flex border-b border-gray-200 gap-2">
        <button type="button" onClick={() => setActiveChannel('voice')} className="pb-2 px-3 text-xs font-semibold border-b-2 border-brand-600 text-brand-700 flex items-center gap-1.5">
          <span>🎙️</span> Voice Agent <span className="bg-brand-100 text-brand-800 text-[10px] px-1.5 py-0.2 rounded font-mono">Active (v{currentVersion})</span>
        </button>
        {['WhatsApp', 'SMS', 'Email'].map((ch) => (
          <button key={ch} type="button" disabled className="pb-2 px-3 text-xs font-medium text-gray-400 border-b-2 border-transparent cursor-not-allowed flex items-center gap-1.5">
            <span>{ch === 'WhatsApp' ? '💬' : ch === 'SMS' ? '📱' : '✉️'}</span> {ch} <span className="bg-gray-100 text-gray-500 text-[10px] px-1 py-0.2 rounded">Roadmap, not built</span>
          </button>
        ))}
      </div>

      {/* Voice Config Form */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Default Language</label>
            <select
              value={voiceConfig.default_language}
              onChange={(e) => setVoiceConfig({ ...voiceConfig, default_language: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg bg-white"
            >
              <option value="en-IN">English (India)</option>
              <option value="hi-IN">Hindi (India)</option>
              <option value="te-IN">Telugu (India)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Tone & Persona</label>
            <input
              type="text"
              value={voiceConfig.tone}
              onChange={(e) => setVoiceConfig({ ...voiceConfig, tone: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg"
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-xs font-semibold text-gray-700">Opening Message (Must include AI disclosure)</label>
            <span className="text-[10px] text-gray-400">Allowed: {'{{first_name}}'}, {'{{bank_name}}'}, {'{{product_name}}'}</span>
          </div>
          <textarea
            rows={2}
            value={voiceConfig.opening_message}
            onChange={(e) => setVoiceConfig({ ...voiceConfig, opening_message: e.target.value })}
            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">System Instructions</label>
          <textarea
            rows={3}
            value={voiceConfig.system_prompt}
            onChange={(e) => setVoiceConfig({ ...voiceConfig, system_prompt: e.target.value })}
            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg font-mono text-[11px]"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Conversation Objective</label>
            <input
              type="text"
              value={voiceConfig.conversation_objective}
              onChange={(e) => setVoiceConfig({ ...voiceConfig, conversation_objective: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Success Condition</label>
            <input
              type="text"
              value={voiceConfig.success_condition}
              onChange={(e) => setVoiceConfig({ ...voiceConfig, success_condition: e.target.value })}
              className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Closing Message</label>
            <input type="text" value={voiceConfig.closing_message} onChange={(e) => setVoiceConfig({ ...voiceConfig, closing_message: e.target.value })} className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg" />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-700 mb-1">Max Turns</label>
              <input type="number" min={2} max={20} value={voiceConfig.max_turns} onChange={(e) => setVoiceConfig({ ...voiceConfig, max_turns: parseInt(e.target.value) || 8 })} className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg" />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-700 mb-1">Max Retries</label>
              <input type="number" min={1} max={5} value={voiceConfig.retry_policy.max_attempts} onChange={(e) => setVoiceConfig({ ...voiceConfig, retry_policy: { ...voiceConfig.retry_policy, max_attempts: parseInt(e.target.value) || 3 } })} className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg" />
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-between items-center border-t border-gray-100">
          <button type="button" onClick={handleTestPreview} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-semibold">
            🔍 Test Render Preview
          </button>
          <button type="button" onClick={handleSaveConfig} disabled={saving} className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50">
            {saving ? 'Saving...' : `Save as v${currentVersion + 1}`}
          </button>
        </div>
      </div>

      {/* Live Preview Box */}
      {previewPayload && (
        <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200 text-xs space-y-2">
          <p className="font-bold text-emerald-900">Rendered Voice Stack Preview (Recipient: {previewPayload.first_name})</p>
          <div className="bg-white p-3 rounded border border-emerald-100 font-mono text-[11px] text-gray-700">
            <p><strong>Opening:</strong> "{previewPayload.opening_message}"</p>
            <p className="mt-1"><strong>System Prompt:</strong> "{previewPayload.system_prompt}"</p>
          </div>
        </div>
      )}
      {previewError && <div className="p-3 bg-red-50 text-red-700 text-xs rounded-lg">{previewError}</div>}

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <button onClick={onBack} className="px-4 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-xs font-semibold">
          ← Back to Audience
        </button>
        <button onClick={onNext} className="px-5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold shadow-xs">
          Review & Validate →
        </button>
      </div>
    </div>
  )
}
