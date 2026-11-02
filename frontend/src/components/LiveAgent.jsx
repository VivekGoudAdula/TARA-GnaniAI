import React, { useState, useEffect, useRef } from 'react'
import AgentControls from './AgentControls'
import ExtractionCard from './ExtractionCard'

const WS_BASE = `ws://${window.location.hostname}:8000/ws/voice`

/**
 * Live Voice Agent interaction screen featuring bi-directional audio streaming,
 * per-turn latency metrics, barge-in support, and automatic extraction.
 */
export default function LiveAgent() {
  const [sessionActive, setSessionActive] = useState(false)
  const [agentState, setAgentState] = useState('idle')
  const [currentLang, setCurrentLang] = useState('en-IN')
  const [messages, setMessages] = useState([])
  const [extraction, setExtraction] = useState(null)
  const [callDuration, setCallDuration] = useState(0)
  const [isRecording, setIsRecording] = useState(false)
  const [inputText, setInputText] = useState('')

  const wsRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false
      return
    }
    isPlayingRef.current = true
    const audioBlob = audioQueueRef.current.shift()
    const audio = new Audio(URL.createObjectURL(audioBlob))
    audio.onended = () => playNextAudio()
    audio.onerror = () => playNextAudio()
    audio.play().catch(() => playNextAudio())
  }

  const queueAudioChunk = (base64Data) => {
    const binary = atob(base64Data)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    audioQueueRef.current.push(new Blob([bytes], { type: 'audio/wav' }))
    if (!isPlayingRef.current) playNextAudio()
  }

  const startCall = () => {
    setMessages([])
    setExtraction(null)
    setSessionActive(true)
    setAgentState('connecting')

    const ws = new WebSocket(WS_BASE)
    wsRef.current = ws

    ws.onopen = () => setAgentState('listening')
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'state') setAgentState(data.state)
        if (data.type === 'transcript') {
          if (data.language) setCurrentLang(data.language)
          setMessages((prev) => [...prev, {
            id: Date.now() + Math.random(),
            role: data.role,
            text: data.text,
            language: data.language,
          }])
        }
        if (data.type === 'audio') queueAudioChunk(data.data)
        if (data.type === 'turn_metrics') {
          setMessages((prev) => {
            const next = [...prev]
            for (let i = next.length - 1; i >= 0; i--) {
              if (next[i].role === 'assistant' && !next[i].metrics) {
                next[i].metrics = data.metrics
                break
              }
            }
            return next
          })
        }
        if (data.type === 'session_ended') {
          setExtraction(data.data)
          setCallDuration(data.duration_seconds || 0)
          setAgentState('ended')
          setSessionActive(false)
        }
      } catch (err) {
        console.error('WS error:', err)
      }
    }
    ws.onclose = () => {
      setSessionActive(false)
      setAgentState('ended')
    }
  }

  const endCall = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end' }))
    }
    stopMic()
    setSessionActive(false)
    setAgentState('ended')
  }

  const interruptSpeech = () => {
    audioQueueRef.current = []
    isPlayingRef.current = false
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'barge_in' }))
    }
  }

  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      audioChunksRef.current = []
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const b64 = reader.result.split(',')[1]
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              type: 'user_audio',
              audio_b64: b64,
              duration_ms: 1500,
            }))
          }
        }
        reader.readAsDataURL(new Blob(audioChunksRef.current, { type: 'audio/wav' }))
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
      setIsRecording(true)
    } catch {
      alert('Microphone access denied or unavailable.')
    }
  }

  const stopMic = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
  }

  const sendTextMessage = (e) => {
    e.preventDefault()
    if (!inputText.trim() || !sessionActive) return
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'user_text',
        text: inputText.trim(),
        duration_ms: 1000,
      }))
    }
    setInputText('')
  }

  return (
    <div className="space-y-6">
      <AgentControls
        sessionActive={sessionActive}
        agentState={agentState}
        isRecording={isRecording}
        inputText={inputText}
        setInputText={setInputText}
        startCall={startCall}
        endCall={endCall}
        interruptSpeech={interruptSpeech}
        startMic={startMic}
        stopMic={stopMic}
        sendTextMessage={sendTextMessage}
      />

      {/* Transcript Chat Stream */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm min-h-[320px] max-h-[440px] overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-52 text-gray-400">
            <p className="text-sm font-medium">Click "Start Call" to talk with Tara.</p>
            <p className="text-xs text-gray-400 mt-1">Realtime STT + Streaming TTS + Barge-in support</p>
          </div>
        ) : (
          messages.map((m) => (
            <div key={m.id} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[11px] font-semibold text-gray-500 capitalize">{m.role}</span>
                {m.language && (
                  <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                    {m.language}
                  </span>
                )}
              </div>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white rounded-br-sm'
                    : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                }`}
              >
                {m.text}
              </div>
              {m.metrics && (
                <div className="text-[10px] text-gray-400 mt-1 px-1">
                  ⏱ {(m.metrics.total_turn_ms / 1000).toFixed(1)}s turn (STT {m.metrics.stt_ms}ms · LLM {m.metrics.llm_ms}ms · TTS 1st {m.metrics.tts_first_audio_ms}ms)
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {extraction && <ExtractionCard data={extraction} durationSeconds={callDuration} />}
    </div>
  )
}
