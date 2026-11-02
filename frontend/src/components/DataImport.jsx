import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const API_BASE = 'http://localhost:8000/api'

/**
 * CSV Import page supporting Customers and Leads with consent attestation and synthetic phone validation.
 */
export default function DataImport() {
  const { token } = useAuth()
  const [recordType, setRecordType] = useState('leads')
  const [file, setFile] = useState(null)
  const [attestation, setAttestation] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return alert('Please choose a CSV file.')
    if (!attestation) return alert('Consent attestation is mandatory.')

    setUploading(true)
    setError(null)
    setReport(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('attestation', 'true')

    try {
      const res = await fetch(`${API_BASE}/import/${recordType}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      setReport(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-lg font-bold text-gray-900">Audience Data Ingestion</h1>
        <p className="text-xs text-gray-500">Import customers or leads with strict consent enforcement</p>
      </div>

      {/* Safety Notice */}
      <div className="bg-blue-50 border border-blue-200 text-blue-900 p-4 rounded-xl text-xs space-y-1">
        <p className="font-semibold">⚠️ Safety Guardrail: Synthetic Phone Numbers Only</p>
        <p className="text-blue-800 leading-relaxed">
          To prevent real-world accidental outreach, the ingestion engine rejects any phone number that does not match the test pattern <code className="bg-blue-100 px-1 py-0.5 rounded font-mono font-bold">+91 90000 xxxxx</code>.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-xs text-red-700 rounded-lg">
          {error}
        </div>
      )}

      <form onSubmit={handleUpload} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm space-y-5">
        <div>
          <label className="text-xs font-semibold text-gray-700 block mb-1.5">Destination Audience Type</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRecordType('leads')}
              className={`py-2 text-xs font-semibold rounded-lg border text-center transition-all ${
                recordType === 'leads'
                  ? 'border-brand-600 bg-brand-50 text-brand-700'
                  : 'border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              External Leads
            </button>
            <button
              type="button"
              onClick={() => setRecordType('customers')}
              className={`py-2 text-xs font-semibold rounded-lg border text-center transition-all ${
                recordType === 'customers'
                  ? 'border-brand-600 bg-brand-50 text-brand-700'
                  : 'border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100'
              }`}
            >
              Internal Customers
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-700 block mb-1.5">Select CSV File</label>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files[0])}
            className="w-full text-xs text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
          />
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={attestation}
              onChange={(e) => setAttestation(e.target.checked)}
              className="mt-0.5 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-xs text-gray-800 leading-snug">
              <strong>Mandatory Consent Attestation:</strong> I confirm these are synthetic/test records or have valid explicit consent for voice outreach. Records with consent=false are stored but permanently marked uncontactable.
            </span>
          </label>
        </div>

        <button
          type="submit"
          disabled={uploading || !attestation || !file}
          className="w-full py-2.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg shadow-sm"
        >
          {uploading ? 'Validating & Ingesting...' : 'Upload & Ingest Audience'}
        </button>
      </form>

      {/* Ingestion Report */}
      {report && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">Ingestion Execution Report</h3>
          <div className="grid grid-cols-4 gap-2 text-center text-xs">
            <div className="bg-gray-50 p-2 rounded-lg border border-gray-100">
              <span className="text-[10px] text-gray-400 block">Processed</span>
              <span className="font-bold text-gray-900">{report.rows_processed}</span>
            </div>
            <div className="bg-green-50 p-2 rounded-lg border border-green-200">
              <span className="text-[10px] text-green-700 block">Accepted</span>
              <span className="font-bold text-green-900">{report.rows_accepted}</span>
            </div>
            <div className="bg-amber-50 p-2 rounded-lg border border-amber-200">
              <span className="text-[10px] text-amber-700 block">Dups Skipped</span>
              <span className="font-bold text-amber-900">{report.duplicates_skipped}</span>
            </div>
            <div className="bg-red-50 p-2 rounded-lg border border-red-200">
              <span className="text-[10px] text-red-700 block">Rejected</span>
              <span className="font-bold text-red-900">{report.rows_rejected}</span>
            </div>
          </div>

          {report.rejections?.length > 0 && (
            <div className="space-y-1">
              <h4 className="text-[11px] font-semibold text-gray-500 uppercase">Rejected Rows</h4>
              <div className="max-h-36 overflow-y-auto space-y-1 text-[11px]">
                {report.rejections.map((rej, i) => (
                  <div key={i} className="p-1.5 bg-red-50 text-red-800 rounded border border-red-100">
                    Row {rej.row}: {rej.reason} {rej.phone ? `(${rej.phone})` : ''}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
