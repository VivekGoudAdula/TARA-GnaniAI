import React from 'react'
import STTCheck from './STTCheck'
import TTSCheck from './TTSCheck'

/**
 * VoiceCheck – top-level test screen for Gnani STT (Prisma v3.0) and TTS (Timbre v2.5).
 */
export default function VoiceCheck() {
  return (
    <div className="space-y-8">
      <STTCheck />
      <TTSCheck />
      <p className="text-xs text-gray-400 text-center">
        Phase 1 dev-only page. All API calls use DEV_ENDPOINTS=true.
        No real customer data is stored. Synthetic audio only.
      </p>
    </div>
  )
}
