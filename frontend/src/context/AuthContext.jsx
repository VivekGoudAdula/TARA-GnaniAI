import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)
const API_BASE = 'http://localhost:8000/api'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('tara_token'))
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('tara_user')
    return saved ? JSON.parse(saved) : null
  })
  const [tenant, setTenant] = useState(() => {
    const saved = localStorage.getItem('tara_tenant')
    return saved ? JSON.parse(saved) : null
  })
  const [loading, setLoading] = useState(false)

  const login = async (email, password) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Login failed')
      }
      const data = await res.json()
      setToken(data.access_token)
      setUser(data.user)
      setTenant(data.tenant)
      localStorage.setItem('tara_token', data.access_token)
      localStorage.setItem('tara_user', JSON.stringify(data.user))
      localStorage.setItem('tara_tenant', JSON.stringify(data.tenant))
      return data
    } finally {
      setLoading(false)
    }
  }

  const signup = async (workspaceName, email, password, fullName) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_name: workspaceName,
          email,
          password,
          full_name: fullName,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Registration failed')
      }
      const data = await res.json()
      setToken(data.access_token)
      setUser(data.user)
      setTenant(data.tenant)
      localStorage.setItem('tara_token', data.access_token)
      localStorage.setItem('tara_user', JSON.stringify(data.user))
      localStorage.setItem('tara_tenant', JSON.stringify(data.tenant))
      return data
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    setTenant(null)
    localStorage.removeItem('tara_token')
    localStorage.removeItem('tara_user')
    localStorage.removeItem('tara_tenant')
  }

  return (
    <AuthContext.Provider value={{ token, user, tenant, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

