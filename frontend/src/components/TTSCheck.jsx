import React, { useState, useRef } from 'react'
import { SpeakerIcon } from './Icons'

const LANGUAGES = [
  { code: 'en-IN', label: 'English (India)', voice: 'Nalini' },
  { code: 'hi-IN', label: 'Hindi', voice: 'Nalini' },
  { code: 'te-IN', label: 'Telugu', voice: 'Nalini' },
]

/**
 * TTSCheck – Text-to-Speech testing section with audio playback.
 * Allows entering text, picking a target language, calling /api/dev/tts, and streaming the audio.
 */
export default function TTSCheck() {
  const [ttsText, setTtsText] = useState('')
  const [ttsLang, setTtsLang] = useState('en-IN')
  const [ttsState, setTtsState] = useState('idle') // idle | loading | done | error
  const [ttsLatency, setTtsLatency] = useState(null)
  const [ttsError, setTtsError] = useState('')

  const audioRef = useRef(null)

  const handleSpeak = async () => {
    if (!ttsText.trim()) return
    setTtsError('')
    setTtsLatency(null)
    setTtsState('loading')

    const selectedLang = LANGUAGES.find((item) => item.code === ttsLang) ?? LANGUAGES[0]

    try {
      const startTime = performance.now()
      const response = await fetch('/api/dev/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: ttsText.trim(),
          language_code: selectedLang.code,
          voice: selectedLang.voice,
        }),
      })
      const roundTripMs = performance.now() - startTime

      if (!response.ok) {
        const errPayload = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errPayload.detail || `HTTP ${response.status}`)
      }

      const audioBlob = await response.blob()
      const audioUrl = URL.createObjectURL(audioBlob)
      if (audioRef.current) {
        audioRef.current.src = audioUrl
        audioRef.current.play()
      }
      setTtsLatency(Math.round(roundTripMs))
      setTtsState('done')
    } catch (err) {
      setTtsError(`TTS error: ${err.message}`)
      setTtsState('error')
    }
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-base font-semibold text-gray-900 mb-1">
        Text-to-Speech — Gnani Timbre v2.5
      </h2>
      <p className="text-sm text-gray-500 mb-5">
        Type text, choose language, and hear it spoken.
      </p>

      <div className="space-y-3">
        <textarea
          value={ttsText}
          onChange={(e) => setTtsText(e.target.value)}
          placeholder="Type text to synthesise…"
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
        />

        <div className="flex items-center gap-3">
          <select
            value={ttsLang}
            onChange={(e) => setTtsLang(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>

          <button
            onClick={handleSpeak}
            disabled={!ttsText.trim() || ttsState === 'loading'}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SpeakerIcon />
            {ttsState === 'loading' ? 'Generating…' : 'Speak'}
          </button>
        </div>
      </div>

      {ttsError && (
        <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {ttsError}
        </div>
      )}

      {ttsLatency !== null && (
        <p className="mt-3 text-xs text-gray-500">
          Audio ready in <strong className="text-gray-700">{ttsLatency} ms</strong> (client RTT) — playing below.
        </p>
      )}

      <audio
        ref={audioRef}
        controls
        className="mt-3 w-full"
        style={{ display: ttsState === 'done' ? 'block' : 'none' }}
      />
    </section>
  )
}
