import React, { useEffect, useRef, useState } from 'react'

/**
 * Public Tester Session: single-use web-based tester call interface.
 * Operates without authentication, bound strictly to the single-use token.
 */
export default function TesterCallView({ token, onBack }) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sessionActive, setSessionActive] = useState(false)
  const [turns, setTurns] = useState([])
  const [extraction, setExtraction] = useState(null)
  const [sessionState, setSessionState] = useState('idle')

  const wsRef = useRef(null)
  const mediaRecorderRef = useRef(null)

  useEffect(() => {
    const fetchTask = async () => {
      try {
        setLoading(true)
        const res = await fetch(`http://localhost:8000/api/call-task/${token}`)
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Call task not available or expired')
        }
        const data = await res.json()
        setTask(data)
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
      const wsUrl = `ws://localhost:8000/ws/voice?token=${token}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setSessionActive(true)
        setSessionState('connected')
      }

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'agent_text') {
          setTurns((prev) => [...prev, { speaker: 'agent', text: msg.text, voice: msg.voice, lang: msg.language }])
        } else if (msg.type === 'agent_audio') {
          const snd = new Audio(`data:audio/wav;base64,${msg.audio_b64}`)
          snd.play().catch(() => {})
        } else if (msg.type === 'extraction') {
          setExtraction(msg.extraction)
        } else if (msg.type === 'session_ended') {
          setSessionActive(false)
          setSessionState('ended')
        }
      }

      ws.onerror = () => {
        setError('WebSocket error during voice session')
      }

      ws.onclose = () => {
        setSessionActive(false)
        setSessionState('ended')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const endCall = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end' }))
    }
    setSessionActive(false)
    setSessionState('ended')
  }

  const sendTestResponse = (text) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setTurns((prev) => [...prev, { speaker: 'user', text }])
      wsRef.current.send(JSON.stringify({ type: 'user_text', text, duration_ms: 1000, stt_ms: 200 }))
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
        {/* Banner */}
        <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl text-xs text-amber-900 flex items-center justify-between">
          <div>
            <span className="font-bold">TEST MODE:</span> Verified synthetic tester session. No telephone calls are placed.
          </div>
          {onBack && <button onClick={onBack} className="text-[11px] font-semibold text-amber-800 hover:underline">Exit</button>}
        </div>

        {/* Profile Card */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-3">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-brand-50 text-brand-700 px-2 py-0.5 rounded">
                Synthetic Persona
              </span>
              <h1 className="text-base font-bold text-gray-900 mt-1">{task.first_name}</h1>
              <p className="text-xs text-gray-500">Targeting: <strong>{task.product_name}</strong> from <strong>{task.bank_name}</strong></p>
            </div>
            <span className="text-xs font-mono bg-gray-100 text-gray-700 px-2.5 py-1 rounded-lg capitalize">
              {task.language}
            </span>
          </div>

          <p className="text-[11px] text-gray-400 border-t pt-2">
            AI Disclosure Notice: Automated representative call. No sensitive financial data or real phone numbers are stored.
          </p>
        </div>

        {/* Live Call Controller */}
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${sessionActive ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'}`} />
              <span className="text-xs font-bold text-gray-800 capitalize">Status: {sessionState}</span>
            </div>
            {!sessionActive && sessionState !== 'ended' ? (
              <button
                onClick={startCall}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
              >
                📞 Start Voice Call
              </button>
            ) : sessionActive ? (
              <button
                onClick={endCall}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
              >
                End Call
              </button>
            ) : (
              <span className="text-xs text-gray-400 font-medium">Session Concluded</span>
            )}
          </div>

          {/* Quick tester simulation buttons */}
          {sessionActive && (
            <div className="space-y-1.5 pt-2 border-t border-gray-100">
              <p className="text-[10px] font-semibold text-gray-400 uppercase">Simulate Customer Responses</p>
              <div className="flex flex-wrap gap-1.5">
                <button
                  onClick={() => sendTestResponse('हाँ, मुझे लोन के बारे में और जानना है। ब्याज दर क्या है?')}
                  className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]"
                >
                  "हाँ, ब्याज दर क्या है?" (Hindi)
                </button>
                <button
                  onClick={() => sendTestResponse('నాకు ₹5 లక్షల వ్యక్తిగత రుణం కావాలి.')}
                  className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]"
                >
                  "నాకు ₹5 లక్షలు కావాలి" (Telugu)
                </button>
                <button
                  onClick={() => sendTestResponse('Please call me back tomorrow at 2 PM.')}
                  className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-[11px]"
                >
                  "Call back tomorrow at 2 PM" (English)
                </button>
              </div>
            </div>
          )}

          {/* Live Transcript Stream */}
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 max-h-60 overflow-y-auto space-y-2 text-xs">
            {turns.length === 0 ? (
              <p className="text-gray-400 text-center italic text-[11px]">Conversation turns will appear here once connected...</p>
            ) : (
              turns.map((t, idx) => (
                <div key={idx} className={`p-2 rounded-lg ${t.speaker === 'agent' ? 'bg-white border border-gray-200' : 'bg-brand-50 border border-brand-100'}`}>
                  <span className="text-[10px] font-bold uppercase text-gray-400 block">{t.speaker === 'agent' ? `Tara (AI • ${t.voice || 'Voice'})` : task.first_name}</span>
                  <p className="text-gray-800 mt-0.5">{t.text}</p>
                </div>
              ))
            )}
          </div>

          {/* Post-Call Extraction Result */}
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
