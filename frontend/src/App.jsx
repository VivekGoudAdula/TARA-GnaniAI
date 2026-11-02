import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import AuthView from './components/AuthView'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import RecordsTable from './components/RecordsTable'
import ProductsView from './components/ProductsView'
import DataImport from './components/DataImport'
import LiveAgent from './components/LiveAgent'
import SessionHistory from './components/SessionHistory'
import VoiceCheck from './components/VoiceCheck'

function MainLayout() {
  const { user, token } = useAuth()
  const [activeNav, setActiveNav] = useState('dashboard')

  if (!token || !user) {
    return <AuthView />
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Platform Navigation Sidebar */}
      <Sidebar activeNav={activeNav} setActiveNav={setActiveNav} />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="bg-white border-b border-gray-200 px-8 py-3.5 sticky top-0 z-20 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="font-semibold text-gray-800 capitalize">{activeNav.replace('_', ' ')}</span>
            <span>/</span>
            <span>TARA Enterprise</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveNav('check')}
              className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
                activeNav === 'check'
                  ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                  : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100'
              }`}
            >
              Dev Audio Check
            </button>
            <span className="text-[11px] bg-brand-50 text-brand-700 px-2.5 py-1 rounded-full font-bold border border-brand-200">
              Phase 3 – Foundation &amp; Scoring
            </span>
          </div>
        </header>

        <main className="p-8 max-w-6xl w-full mx-auto">
          {activeNav === 'dashboard' && <Dashboard setActiveNav={setActiveNav} />}
          {activeNav === 'customers' && <RecordsTable recordType="customers" />}
          {activeNav === 'leads' && <RecordsTable recordType="leads" />}
          {activeNav === 'products' && <ProductsView />}
          {activeNav === 'import' && <DataImport />}
          {activeNav === 'voice' && <LiveAgent />}
          {activeNav === 'history' && <SessionHistory />}
          {activeNav === 'check' && <VoiceCheck />}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  )
}
