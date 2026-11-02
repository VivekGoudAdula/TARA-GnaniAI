import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Authentication screen: Login, Tenant Registration, and Quick Demo log-ins.
 */
export default function AuthView() {
  const { login, signup, loading } = useAuth()
  const [isSignup, setIsSignup] = useState(false)
  const [workspaceName, setWorkspaceName] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      if (isSignup) {
        await signup(workspaceName, email, password, fullName)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const handleQuickLogin = (demoEmail, demoPass) => {
    setEmail(demoEmail)
    setPassword(demoPass)
    login(demoEmail, demoPass).catch((err) => setError(err.message))
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full shadow-sm space-y-6">
        <div className="text-center space-y-1">
          <div className="inline-flex w-10 h-10 rounded-xl bg-brand-600 items-center justify-center text-white font-bold text-lg mb-2 shadow-sm">
            T
          </div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">TARA Banking Platform</h1>
          <p className="text-xs text-gray-500">Targeted Acquisition &amp; Reach Agent</p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-xs text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex bg-gray-100 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => { setIsSignup(false); setError(null) }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              !isSignup ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsSignup(true); setError(null) }}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              isSignup ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Register Workspace
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignup && (
            <>
              <div>
                <label className="text-[11px] font-medium text-gray-700 block mb-1">Bank / Institution Name</label>
                <input
                  type="text"
                  required
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="e.g. Apex National Bank"
                  className="w-full text-xs border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-1 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-gray-700 block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Priya Sharma"
                  className="w-full text-xs border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-1 focus:ring-brand-500"
                />
              </div>
            </>
          )}

          <div>
            <label className="text-[11px] font-medium text-gray-700 block mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@bank.com"
              className="w-full text-xs border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="text-[11px] font-medium text-gray-700 block mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full text-xs border border-gray-300 rounded-lg px-3 py-2.5 focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
          >
            {loading ? 'Authenticating...' : isSignup ? 'Create Workspace' : 'Sign In'}
          </button>
        </form>

        {/* Quick Demo Logins */}
        <div className="pt-2 border-t border-gray-100">
          <p className="text-[10px] text-gray-400 uppercase tracking-wider text-center mb-2">Pre-Seeded Demo Access</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin('admin@testbank.com', 'password123')}
              className="flex-1 py-1.5 px-2 bg-gray-50 border border-gray-200 hover:bg-gray-100 text-[11px] font-medium text-gray-700 rounded-lg text-center"
            >
              Test Bank (400 leads)
            </button>
            <button
              type="button"
              onClick={() => handleQuickLogin('admin@otherbank.com', 'password123')}
              className="flex-1 py-1.5 px-2 bg-gray-50 border border-gray-200 hover:bg-gray-100 text-[11px] font-medium text-gray-700 rounded-lg text-center"
            >
              Other Bank (Isolated)
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

