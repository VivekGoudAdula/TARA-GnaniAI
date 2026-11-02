import React, { useState, useEffect } from 'react'
import ExtractionCard from './ExtractionCard'

const API_BASE = 'http://localhost:8000/api'

export default function SessionHistory() {
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchSessions = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/voice/sessions`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSessions(data)
    } catch (err) {
      setError(`Failed to load sessions: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const loadSessionDetails = async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/voice/sessions/${sessionId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSelectedSession(data)
    } catch (err) {
      alert(`Could not load session details: ${err.message}`)
    }
  }

  useEffect(() => {
    fetchSessions()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Session History</h2>
          <p className="text-xs text-gray-500">Stored voice sessions in MongoDB</p>
        </div>
        <button
          onClick={fetchSessions}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 shadow-sm"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-xs text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Sessions Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50 text-gray-500 font-medium">
            <tr>
              <th className="px-4 py-3 text-left">Session ID</th>
              <th className="px-4 py-3 text-left">Started</th>
              <th className="px-4 py-3 text-left">Duration</th>
              <th className="px-4 py-3 text-left">Turns</th>
              <th className="px-4 py-3 text-left">Outcome</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-700">
            {sessions.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-8 text-center text-gray-400">
                  {loading ? 'Loading sessions...' : 'No voice sessions found in database.'}
                </td>
              </tr>
            ) : (
              sessions.map((s) => (
                <tr key={s.session_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono font-medium text-gray-900">{s.session_id}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {s.started_at ? new Date(s.started_at).toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-4 py-3">{s.duration_seconds ? `${s.duration_seconds}s` : '—'}</td>
                  <td className="px-4 py-3">{(s.turns || []).length}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-700 capitalize">
                      {s.extracted_data?.outcome || 'Pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => loadSessionDetails(s.session_id)}
                      className="text-brand-600 hover:text-brand-800 font-medium"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Selected Session Details Modal/Card */}
      {selectedSession && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b pb-3 border-gray-100">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                Session: <span className="font-mono">{selectedSession.session_id}</span>
              </h3>
              <p className="text-xs text-gray-500">
                Duration: {selectedSession.duration_seconds}s · Turns: {(selectedSession.turns || []).length}
              </p>
            </div>
            <button
              onClick={() => setSelectedSession(null)}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              ✕ Close
            </button>
          </div>

          {/* Turn-by-turn Transcript with Latencies */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Conversation Turns</h4>
            {(selectedSession.turns || []).map((t) => (
              <div key={t.turn_num} className="bg-gray-50 rounded-lg p-3 text-xs space-y-1.5 border border-gray-100">
                <div className="flex justify-between items-center text-gray-400 text-[11px]">
                  <span className="font-semibold text-gray-600">Turn #{t.turn_num}</span>
                  <span>⏱ {((t.total_turn_ms || 0) / 1000).toFixed(1)}s turn (STT {t.stt_ms}ms · LLM {t.llm_ms}ms · TTS 1st {t.tts_first_audio_ms}ms)</span>
                </div>
                <p><span className="font-semibold text-brand-700">User:</span> {t.user_transcript}</p>
                <p><span className="font-semibold text-gray-700">Agent:</span> {t.agent_response}</p>
              </div>
            ))}
          </div>

          {/* Post-Call Extraction */}
          {selectedSession.extracted_data && (
            <ExtractionCard
              data={selectedSession.extracted_data}
              durationSeconds={selectedSession.duration_seconds}
            />
          )}
        </div>
      )}
    </div>
  )
}
