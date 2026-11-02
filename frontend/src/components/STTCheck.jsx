import React, { useState, useRef, useCallback } from 'react'
import { MicIcon, StopIcon } from './Icons'

/** Maximum recording duration in seconds before auto-stopping (Gnani STT max limit is 30s). */
const MAX_RECORD_SECONDS = 25

/**
 * STTCheck – Speech-to-Text testing section with microphone capture.
 * Captures mic stream via MediaRecorder, auto-stops at 25s, and sends audio to /api/dev/stt.
 */
export default function STTCheck() {
  const [sttState, setSttState] = useState('idle') // idle | recording | processing | done | error
  const [sttResult, setSttResult] = useState(null)
  const [sttError, setSttError] = useState('')
  const [recordSeconds, setRecordSeconds] = useState(0)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const countdownRef = useRef(null)

  const sendAudioToBackend = async () => {
    setSttState('processing')
    const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' })
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')

    try {
      const startTime = performance.now()
      const response = await fetch('/api/dev/stt', { method: 'POST', body: formData })
      const roundTripMs = performance.now() - startTime

      if (!response.ok) {
        const errPayload = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errPayload.detail || `HTTP ${response.status}`)
      }

      const resultPayload = await response.json()
      setSttResult({ ...resultPayload, clientLatency: Math.round(roundTripMs) })
      setSttState('done')
    } catch (err) {
      setSttError(`STT error: ${err.message}`)
      setSttState('error')
    }
  }

  const startRecording = useCallback(async () => {
    setSttError('')
    setSttResult(null)
    setRecordSeconds(0)

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setSttError('Microphone access denied. Please allow microphone permissions and try again.')
      return
    }

    chunksRef.current = []
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    mediaRecorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }

    recorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop())
      clearInterval(countdownRef.current)
      clearTimeout(timerRef.current)
      await sendAudioToBackend()
    }

    recorder.start(250)
    setSttState('recording')

    countdownRef.current = setInterval(() => {
      setRecordSeconds((sec) => sec + 1)
    }, 1000)

    // Auto-stop at 25 seconds to respect the 30-second Gnani API limit
    timerRef.current = setTimeout(() => {
      if (recorder.state === 'recording') {
        recorder.stop()
      }
    }, MAX_RECORD_SECONDS * 1000)
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-base font-semibold text-gray-900 mb-1">
        Speech-to-Text — Gnani Prisma v3.0
      </h2>
      <p className="text-sm text-gray-500 mb-5">
        Record up to {MAX_RECORD_SECONDS}s. Auto-stops at {MAX_RECORD_SECONDS}s (Gnani limit: 30s).
      </p>

      <div className="flex items-center gap-3 mb-5">
        {sttState !== 'recording' ? (
          <button
            onClick={startRecording}
            disabled={sttState === 'processing'}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <MicIcon />
            {sttState === 'processing' ? 'Processing…' : 'Record'}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
          >
            <StopIcon />
            Stop ({MAX_RECORD_SECONDS - recordSeconds}s left)
          </button>
        )}

        {sttState === 'recording' && (
          <span className="flex items-center gap-1.5 text-sm text-red-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            Recording {recordSeconds}s
          </span>
        )}
      </div>

      {sttError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {sttError}
        </div>
      )}

      {sttResult && (
        <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 space-y-2">
          <p className="text-sm font-medium text-gray-700">Transcript</p>
          <p className="text-gray-900">{sttResult.transcript || '(empty transcript returned)'}</p>
          <div className="flex flex-wrap gap-4 text-xs text-gray-500 pt-1">
            <span>Detected language: <strong className="text-gray-700">{sttResult.detected_language_code}</strong></span>
            <span>Server latency: <strong className="text-gray-700">{sttResult.latency_ms} ms</strong></span>
            <span>Client RTT: <strong className="text-gray-700">{sttResult.clientLatency} ms</strong></span>
            <span>Request ID: <code className="text-gray-600">{sttResult.request_id}</code></span>
          </div>
        </div>
      )}
    </section>
  )
}
