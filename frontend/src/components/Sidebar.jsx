import React from 'react'
import { useAuth } from '../context/AuthContext'

/**
 * Platform left-navigation sidebar displaying workspace identity, routes, and logout.
 */
export default function Sidebar({ activeNav, setActiveNav }) {
  const { tenant, user, logout } = useAuth()

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'customers', label: 'Customers', icon: '👥' },
    { id: 'leads', label: 'Leads', icon: '🎯' },
    { id: 'products', label: 'Products', icon: '💳' },
    { id: 'import', label: 'Data Import', icon: '📥' },
    { id: 'voice', label: 'Live Voice Agent', icon: '🎙️' },
    { id: 'history', label: 'Session History', icon: '📜' },
  ]

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Workspace Branding */}
      <div className="p-5 border-b border-gray-100 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
          T
        </div>
        <div className="overflow-hidden">
          <h2 className="text-xs font-bold text-gray-900 truncate">
            {tenant?.name || 'TARA Platform'}
          </h2>
          <span className="text-[10px] text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded font-medium">
            Active Workspace
          </span>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveNav(item.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all text-left ${
              activeNav === item.id
                ? 'bg-brand-50 text-brand-700 font-semibold shadow-xs'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-sm">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* User profile & Logout */}
      <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
        <div className="overflow-hidden pr-2">
          <p className="text-xs font-semibold text-gray-900 truncate">{user?.full_name || 'Admin'}</p>
          <p className="text-[10px] text-gray-500 truncate">{user?.email}</p>
        </div>
        <button
          onClick={logout}
          title="Sign out"
          className="text-xs text-gray-500 hover:text-red-600 p-1.5 rounded-lg hover:bg-white border border-transparent hover:border-gray-200"
        >
          Logout
        </button>
      </div>
    </aside>
  )
}
