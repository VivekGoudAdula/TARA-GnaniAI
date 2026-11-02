import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import WizardStep1Details from './campaign_wizard/WizardStep1Details'
import WizardStep2Audience from './campaign_wizard/WizardStep2Audience'
import WizardStep3Voice from './campaign_wizard/WizardStep3Voice'
import WizardStep4Review from './campaign_wizard/WizardStep4Review'

/**
 * 4-Step Campaign Creation and Configuration Wizard.
 */
export default function CampaignWizard({ existingCampaignId, onCancel, onComplete }) {
  const { authFetch } = useAuth()
  const [step, setStep] = useState(1)
  const [products, setProducts] = useState([])
  const [campaignId, setCampaignId] = useState(existingCampaignId || null)
  const [allowOverride, setAllowOverride] = useState(false)

  const [campaignData, setCampaignData] = useState({
    name: '',
    product_id: '',
    audience_type: 'customers',
    objective: '',
    description: '',
  })

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const res = await authFetch('/api/products')
        if (res.ok) {
          const list = await res.json()
          setProducts(list.filter((p) => p.active))
        }
      } catch (err) {
        console.error('Failed to load products', err)
      }
    }
    fetchProducts()
  }, [])

  useEffect(() => {
    if (existingCampaignId) {
      const fetchExisting = async () => {
        try {
          const res = await authFetch(`/api/campaigns/${existingCampaignId}`)
          if (res.ok) {
            const data = await res.json()
            setCampaignData({
              name: data.name,
              product_id: data.product_id,
              audience_type: data.audience_type,
              objective: data.objective || '',
              description: data.description || '',
            })
            setAllowOverride(data.allow_ineligible_override || false)
          }
        } catch (err) {
          console.error(err)
        }
      }
      fetchExisting()
    }
  }, [existingCampaignId])

  const handleStep1Next = async () => {
    if (!campaignId) {
      // Create new draft campaign
      try {
        const res = await authFetch('/api/campaigns', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...campaignData,
            allow_ineligible_override: allowOverride,
          }),
        })
        if (!res.ok) throw new Error('Failed to create campaign')
        const created = await res.json()
        setCampaignId(created.id)
        setStep(2)
      } catch (err) {
        alert(err.message)
      }
    } else {
      // Update existing draft metadata
      try {
        await authFetch(`/api/campaigns/${campaignId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: campaignData.name,
            objective: campaignData.objective,
            description: campaignData.description,
            allow_ineligible_override: allowOverride,
          }),
        })
        setStep(2)
      } catch (err) {
        alert(err.message)
      }
    }
  }

  const steps = [
    { num: 1, label: 'Details & Objective' },
    { num: 2, label: 'Target Audience' },
    { num: 3, label: 'Voice Config' },
    { num: 4, label: 'Review & Validate' },
  ]

  return (
    <div className="space-y-6">
      {/* Wizard Header & Stepper */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <button
            onClick={onCancel}
            className="text-xs text-gray-500 hover:text-gray-900 mb-1 inline-flex items-center gap-1"
          >
            ← Cancel & Back to Campaigns
          </button>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">
            {existingCampaignId ? 'Edit Campaign' : 'Create New Campaign'}
          </h1>
        </div>

        {/* Stepper indicators */}
        <div className="flex items-center gap-2">
          {steps.map((s, idx) => (
            <React.Fragment key={s.num}>
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  step === s.num
                    ? 'bg-brand-50 text-brand-700 border border-brand-200'
                    : step > s.num
                    ? 'bg-emerald-50 text-emerald-700'
                    : 'text-gray-400 bg-gray-50'
                }`}
              >
                <span>{step > s.num ? '✓' : s.num}.</span>
                <span className="hidden md:inline">{s.label}</span>
              </div>
              {idx < steps.length - 1 && <span className="text-gray-300 text-xs">→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Wizard Step Body */}
      {step === 1 && (
        <WizardStep1Details
          campaignData={campaignData}
          setCampaignData={setCampaignData}
          products={products}
          onNext={handleStep1Next}
          isEditMode={!!existingCampaignId}
        />
      )}

      {step === 2 && (
        <WizardStep2Audience
          campaignId={campaignId}
          productId={campaignData.product_id}
          audienceType={campaignData.audience_type}
          allowOverride={allowOverride}
          setAllowOverride={setAllowOverride}
          onNext={() => setStep(3)}
          onBack={() => setStep(1)}
        />
      )}

      {step === 3 && (
        <WizardStep3Voice
          campaignId={campaignId}
          onNext={() => setStep(4)}
          onBack={() => setStep(2)}
        />
      )}

      {step === 4 && (
        <WizardStep4Review
          campaignId={campaignId}
          onFinish={onComplete}
          onBack={() => setStep(3)}
        />
      )}
    </div>
  )
}
