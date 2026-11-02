import React, { useEffect, useRef, useState } from 'react'

/**
 * Public Tester Session: web-based tester call interface bound to single-use token.
 * Default experience uses real microphone; typed fallback is always available.
 * Simulated buttons appear only when VITE_DEV_TOOLS is enabled.
 */
export default function TesterCallView({ token, onBack }) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sessionActive, setSessionActive] = useState(false)
  const [sessionState, setSessionState] = useState('idle')
  const [turns, setTurns] = useState([])
  const [extraction, setExtraction] = useState(null)
  const [isRecording, setIsRecording] = useState(false)
  const [typedText, setTypedText] = useState('')
  const [callError, setCallError] = useState(null)

  const isDevTools = import.meta.env.VITE_DEV_TOOLS === 'true'
  const wsRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => {
    const fetchTask = async () => {
      try {
        setLoading(true)
        const res = await fetch(`http://localhost:8000/api/call-task/${token}`)
        if (!res.ok) throw new Error((await res.json()).detail || 'Call task expired')
        setTask(await res.json())
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchTask()
  }, [token])

  const startCall = async () => {
    try {
      setSessionState('connecting')
      setCallError(null)
      const ws = new WebSocket(`ws://localhost:8000/ws/voice?token=${token}`)
      wsRef.current = ws
      ws.onopen = () => { setSessionActive(true); setSessionState('connected') }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === 'agent_text') setTurns((p) => [...p, { speaker: 'agent', text: msg.text, voice: msg.voice, lang: msg.language }])
        else if (msg.type === 'agent_audio') new Audio(`data:audio/wav;base64,${msg.audio_b64}`).play().catch(() => {})
        else if (msg.type === 'extraction') setExtraction(msg.extraction)
        else if (msg.type === 'error') setCallError(msg.message || 'Call processing error')
        else if (msg.type === 'session_ended') { setSessionActive(false); setSessionState('ended') }
      }
      ws.onerror = () => setCallError('WebSocket connection error')
      ws.onclose = () => { setSessionActive(false); setSessionState('ended') }
    } catch (err) {
      setCallError(err.message)
    }
  }

  const endCall = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ type: 'end' }))
    if (mediaRecorderRef.current && isRecording) mediaRecorderRef.current.stop()
    setSessionActive(false)
    setSessionState('ended')
  }

  const startMicRecording = async () => {
    try {
      setCallError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      audioChunksRef.current = []
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
      recorder.onstop = () => {
        const reader = new FileReader()
        reader.onloadend = () => {
          const b64 = reader.result.split(',')[1]
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'user_audio', audio_b64: b64, duration_ms: 2000 }))
          }
        }
        reader.readAsDataURL(new Blob(audioChunksRef.current, { type: 'audio/webm' }))
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
      setIsRecording(true)
    } catch {
      setCallError('Microphone access denied: please use typed fallback.')
    }
  }

  const stopMicRecording = () => {
    if (mediaRecorderRef.current && isRecording) { mediaRecorderRef.current.stop(); setIsRecording(false) }
  }

  const sendTyped = (e) => {
    e?.preventDefault()
    if (!typedText.trim() || wsRef.current?.readyState !== WebSocket.OPEN) return
    setTurns((p) => [...p, { speaker: 'user', text: typedText }])
    wsRef.current.send(JSON.stringify({ type: 'user_text', text: typedText, duration_ms: 1000, stt_ms: 100 }))
    setTypedText('')
  }

  const sendSim = (text) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setTurns((p) => [...p, { speaker: 'user', text }])
      wsRef.current.send(JSON.stringify({ type: 'user_text', text, duration_ms: 1000, stt_ms: 150 }))
    }
  }

  if (loading) return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-xs text-gray-500">Loading tester session...</div>
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="bg-white p-6 rounded-2xl border border-gray-200 max-w-md w-full text-center space-y-3">
          <div className="w-10 h-10 mx-auto rounded-full bg-rose-50 text-rose-600 flex items-center justify-center text-lg font-bold">✕</div>
          <h2 className="text-sm font-bold text-gray-900">Session Expired or Unavailable</h2>
          <p className="text-xs text-gray-500">{error}</p>
          {onBack && <button onClick={onBack} className="text-xs text-brand-600 font-semibold hover:underline mt-2">← Return to Dashboard</button>}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-8 flex flex-col items-center">
      <div className="max-w-xl w-full space-y-4">
        <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl text-xs text-amber-900 flex items-center justify-between">
          <span><span className="font-bold">TEST MODE:</span> Verified synthetic tester session. No telephone calls are placed.</span>
          {onBack && <button onClick={onBack} className="text-[11px] font-semibold text-amber-800 hover:underline">Exit</button>}
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold uppercase bg-brand-50 text-brand-700 px-2 py-0.5 rounded">Synthetic Persona</span>
              <h1 className="text-base font-bold text-gray-900 mt-1">{task.first_name}</h1>
              <p className="text-xs text-gray-500">Targeting: <strong>{task.product_name}</strong> from <strong>{task.bank_name}</strong></p>
            </div>
            <span className="text-xs font-mono bg-gray-100 text-gray-700 px-2.5 py-1 rounded-lg capitalize">{task.language}</span>
          </div>
          <p className="text-[11px] text-gray-400 border-t pt-2">AI Disclosure: Automated representative call. No sensitive financial data is stored.</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${sessionActive ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'}`} />
              <span className="text-xs font-bold text-gray-800 capitalize">Status: {sessionState}</span>
            </div>
            {!sessionActive && sessionState !== 'ended' ? (
              <button onClick={startCall} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs">
                📞 Start Voice Call
              </button>
            ) : sessionActive ? (
              <button onClick={endCall} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-xs">
                End Call
              </button>
            ) : (
              <span className="text-xs text-gray-400 font-medium">Session Concluded</span>
            )}
          </div>

          {callError && (
            <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex justify-between items-center">
              <span>{callError}</span>
              <button onClick={() => setCallError(null)} className="text-[11px] font-semibold underline">Retry Turn</button>
            </div>
          )}

          {sessionActive && (
            <div className="space-y-3 pt-2 border-t border-gray-100">
              <div className="flex items-center gap-2">
                {!isRecording ? (
                  <button onClick={startMicRecording} className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg shadow-xs">
                    🎤 Speak (Record)
                  </button>
                ) : (
                  <button onClick={stopMicRecording} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg animate-pulse">
                    ⏹ Stop & Send Audio
                  </button>
                )}
                <span className="text-[11px] text-gray-400">{isRecording ? 'Listening...' : 'Tap speak to use mic'}</span>
              </div>

              <form onSubmit={sendTyped} className="flex gap-2">
                <input
                  type="text" value={typedText} onChange={(e) => setTypedText(e.target.value)}
                  placeholder="Typed fallback: enter response..."
                  className="flex-1 px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <button type="submit" className="px-3 py-1.5 bg-gray-800 hover:bg-black text-white text-xs font-semibold rounded-lg">
                  Typed fallback
                </button>
              </form>

              {isDevTools && (
                <div className="space-y-1.5 pt-2 border-t border-gray-100">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase">Simulate Customer Responses (Dev Tools Only)</p>
                  <div className="flex flex-wrap gap-1.5">
                    <button onClick={() => sendSim('हाँ, मुझे लोन के बारे में और जानना है।')} className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]">"हाँ, लोन जानना है" (Hindi)</button>
                    <button onClick={() => sendSim('నాకు ₹5 లక్షల వ్యక్తిగత రుణం కావాలి.')} className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]">"₹5 లక్షలు కావాలి" (Telugu)</button>
                    <button onClick={() => sendSim('Please call me back tomorrow at 2 PM.')} className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]">"Call back tomorrow" (English)</button>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 max-h-60 overflow-y-auto space-y-2 text-xs">
            {turns.length === 0 ? (
              <p className="text-gray-400 text-center italic text-[11px]">Conversation turns will appear here once connected...</p>
            ) : (
              turns.map((t, idx) => (
                <div key={idx} className={`p-2 rounded-lg ${t.speaker === 'agent' ? 'bg-white border border-gray-200' : 'bg-brand-50 border border-brand-100'}`}>
                  <span className="text-[10px] font-bold uppercase text-gray-400 block">{t.speaker === 'agent' ? `Tara (${t.voice || 'AI Voice'})` : task.first_name}</span>
                  <p className="text-gray-800 mt-0.5">{t.text}</p>
                </div>
              ))
            )}
          </div>

          {extraction && (
            <div className="bg-emerald-50/75 p-3.5 rounded-xl border border-emerald-200 text-xs space-y-1">
              <span className="text-[10px] font-bold text-emerald-800 uppercase block">Extracted Call Outcome</span>
              <p className="font-semibold text-emerald-950">Outcome: <span className="capitalize">{extraction.outcome}</span> • Interest: <span className="capitalize">{extraction.interest_level}</span></p>
              {extraction.loan_amount_inr && <p className="text-gray-700">Amount: ₹{Number(extraction.loan_amount_inr).toLocaleString('en-IN')}</p>}
              {extraction.callback_time && <p className="text-gray-700">Callback: {extraction.callback_time}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
