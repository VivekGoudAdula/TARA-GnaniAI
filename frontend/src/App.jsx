import React, { useState } from 'react'
import LiveAgent from './components/LiveAgent'
import VoiceCheck from './components/VoiceCheck'
import SessionHistory from './components/SessionHistory'

/**
 * App root navigation – toggles between Live Voice Agent, Voice Check, and Session History.
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('live')

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-sm">T</span>
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-900 tracking-tight">TARA</h1>
              <p className="text-[11px] text-gray-500">Targeted Acquisition &amp; Reach Agent</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 bg-gray-100 p-1 rounded-xl">
            <button
              onClick={() => setActiveTab('live')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'live'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              Live Voice Agent
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'history'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              Session History
            </button>
            <button
              onClick={() => setActiveTab('check')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'check'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              Voice Check (Dev)
            </button>
          </nav>

          <span className="text-xs bg-brand-50 text-brand-700 px-2.5 py-1 rounded-full font-semibold border border-brand-200">
            Phase 2 – Active Loop
          </span>
        </div>
      </header>

      <main className="max-w-4xl w-full mx-auto px-6 py-8 flex-1">
        {activeTab === 'live' && <LiveAgent />}
        {activeTab === 'history' && <SessionHistory />}
        {activeTab === 'check' && <VoiceCheck />}
      </main>
    </div>
  )
}
