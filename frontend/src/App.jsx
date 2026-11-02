import VoiceCheck from './components/VoiceCheck'

/**
 * App root – Phase 1 only renders the Voice Check page.
 * Navigation and routing come in later phases.
 */
export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">TARA</h1>
            <p className="text-xs text-gray-500">Targeted Acquisition &amp; Reach Agent</p>
          </div>
          <span className="ml-auto text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
            Phase 1 – Voice Check
          </span>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-8">
        <VoiceCheck />
      </main>
    </div>
  )
}

