import React from 'react'

/**
 * Control buttons for live call interaction: Start, End, Interrupt, Mic, and Text Input.
 */
export default function AgentControls({
  sessionActive,
  agentState,
  isRecording,
  inputText,
  setInputText,
  startCall,
  endCall,
  interruptSpeech,
  startMic,
  stopMic,
  sendTextMessage,
}) {
  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className={`w-3.5 h-3.5 rounded-full ${
              agentState === 'speaking'
                ? 'bg-blue-500 animate-pulse'
                : agentState === 'thinking'
                ? 'bg-amber-500 animate-spin'
                : agentState === 'listening'
                ? 'bg-green-500 animate-ping'
                : 'bg-gray-300'
            }`}
          />
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Tara Voice Agent</h2>
            <p className="text-[11px] text-gray-500 capitalize">Status: {agentState}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {sessionActive && (
            <button
              onClick={interruptSpeech}
              className="px-3 py-1.5 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-lg border border-amber-200"
            >
              Interrupt Agent
            </button>
          )}
          {!sessionActive ? (
            <button
              onClick={startCall}
              className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
            >
              Start Call
            </button>
          ) : (
            <button
              onClick={endCall}
              className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm"
            >
              End Call
            </button>
          )}
        </div>
      </div>

      {sessionActive && (
        <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-sm flex items-center gap-3">
          <button
            onMouseDown={startMic}
            onMouseUp={stopMic}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              isRecording
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {isRecording ? 'Listening... (Release to send)' : 'Hold to Speak (Mic)'}
          </button>
          <form onSubmit={sendTextMessage} className="flex-1 flex gap-2">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Or type a response (English, Hindi, Telugu)..."
              className="flex-1 text-xs border border-gray-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-brand-500"
            />
            <button
              type="submit"
              className="px-3 py-2 text-xs font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
