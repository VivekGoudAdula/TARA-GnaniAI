import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'

const API_BASE = 'http://localhost:8000/api'

/**
 * Product Catalogue Management: list, create, edit, and toggle active status.
 */
export default function ProductsView() {
  const { token } = useAuth()
  const [products, setProducts] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    category: 'Lending',
    description: '',
    min_income: 25000,
    min_age: 21,
    max_age: 60,
    min_credit_score: 650,
    employment_types: 'salaried, self_employed',
    default_prompt: 'You are Tara, calling regarding an outreach offer.',
    default_opening_message: 'Hello, this is Tara calling regarding your pre-approved offer.',
  })

  const loadProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/products`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      setProducts(data)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    if (token) loadProducts()
  }, [token])

  const handleCreate = async (e) => {
    e.preventDefault()
    setLoading(true)
    const payload = {
      name: formData.name,
      category: formData.category,
      description: formData.description,
      active: true,
      eligibility_rules: {
        min_income: Number(formData.min_income),
        min_age: Number(formData.min_age),
        max_age: Number(formData.max_age),
        min_credit_score: Number(formData.min_credit_score),
        employment_types: formData.employment_types.split(',').map((s) => s.trim().toLowerCase()),
      },
      default_prompt: formData.default_prompt,
      default_opening_message: formData.default_opening_message,
    }

    try {
      const res = await fetch(`${API_BASE}/products`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('Failed to create product')
      setShowModal(false)
      loadProducts()
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleActive = async (product) => {
    try {
      await fetch(`${API_BASE}/products/${product.product_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ active: !product.active }),
      })
      loadProducts()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-lg font-bold text-gray-900">Product Catalogue</h1>
          <p className="text-xs text-gray-500">Configure lending products and deterministic underwriting rules</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg shadow-sm"
        >
          + Add New Product
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {products.map((p) => (
          <div key={p.product_id} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[10px] bg-brand-50 text-brand-700 px-2 py-0.5 rounded font-semibold uppercase tracking-wider">
                  {p.category}
                </span>
                <h3 className="text-sm font-bold text-gray-900 mt-1">{p.name}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
              </div>
              <button
                onClick={() => toggleActive(p)}
                className={`text-[10px] px-2.5 py-1 rounded-full font-bold uppercase transition-all ${
                  p.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {p.active ? 'Active' : 'Inactive'}
              </button>
            </div>

            <div className="bg-gray-50 rounded-lg p-2.5 border border-gray-100 text-[11px] space-y-1">
              <span className="font-semibold text-gray-500 uppercase block text-[10px]">Eligibility Rules</span>
              <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-gray-700">
                <span>Min Income: <strong>₹{p.eligibility_rules?.min_income?.toLocaleString('en-IN')}</strong></span>
                <span>Min Credit: <strong>{p.eligibility_rules?.min_credit_score}</strong></span>
                <span>Age: <strong>{p.eligibility_rules?.min_age}–{p.eligibility_rules?.max_age} yrs</strong></span>
                <span>Types: <strong>{(p.eligibility_rules?.employment_types || []).join(', ')}</strong></span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <h3 className="text-sm font-bold text-gray-900">Add Lending Product</h3>
              <button onClick={() => setShowModal(false)} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Product Name</label>
                  <input
                    type="text" required
                    value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. MSME Working Capital"
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5"
                  />
                </div>
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Category</label>
                  <input
                    type="text" required
                    value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5"
                  />
                </div>
              </div>

              <div>
                <label className="font-medium text-gray-700 block mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Short value proposition"
                  className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Min Income (₹)</label>
                  <input type="number" required value={formData.min_income} onChange={(e) => setFormData({ ...formData, min_income: e.target.value })} className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5" />
                </div>
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Min Score</label>
                  <input type="number" required value={formData.min_credit_score} onChange={(e) => setFormData({ ...formData, min_credit_score: e.target.value })} className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5" />
                </div>
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Age (Min–Max)</label>
                  <div className="flex gap-1">
                    <input type="number" required value={formData.min_age} onChange={(e) => setFormData({ ...formData, min_age: e.target.value })} className="w-1/2 border border-gray-300 rounded-lg px-2 py-1.5" />
                    <input type="number" required value={formData.max_age} onChange={(e) => setFormData({ ...formData, max_age: e.target.value })} className="w-1/2 border border-gray-300 rounded-lg px-2 py-1.5" />
                  </div>
                </div>
              </div>

              <div>
                <label className="font-medium text-gray-700 block mb-1">Allowed Employment (comma-separated)</label>
                <input type="text" required value={formData.employment_types} onChange={(e) => setFormData({ ...formData, employment_types: e.target.value })} placeholder="salaried, self_employed" className="w-full border border-gray-300 rounded-lg px-2.5 py-1.5" />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button type="button" onClick={() => setShowModal(false)} className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={loading} className="px-4 py-1.5 rounded-lg bg-brand-600 text-white font-semibold hover:bg-brand-700">
                  {loading ? 'Saving...' : 'Save Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

