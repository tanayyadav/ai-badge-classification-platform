/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Audit trail table with expandable detail view and issuer/status filtering.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getLogs } from '../services/api'

const PAGE_SIZE = 20

function ConfBadge({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low:    'bg-red-100 text-red-800',
  }[level] || 'bg-gray-100 text-gray-700'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{level || '—'}</span>
}

function StatusBadge({ status }) {
  const cls = {
    pending:    'bg-gray-100 text-gray-700',
    accepted:   'bg-green-100 text-green-800',
    overridden: 'bg-blue-100 text-blue-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{status}</span>
}

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch { return iso }
}

function DetailRow({ expanded, log }) {
  if (!expanded) return null

  let rules = []
  try { rules = JSON.parse(log.triggered_rules || '[]') } catch { /* */ }

  return (
    <tr>
      <td colSpan={8} className="bg-gray-50 px-6 py-4 border-b border-gray-200">
        <div className="space-y-3 text-sm">

          {/* Explanation */}
          <div>
            <p className="font-medium text-gray-700 mb-1">Explanation</p>
            <pre className="whitespace-pre-wrap font-mono text-xs bg-white border border-gray-200 rounded p-3 max-h-64 overflow-y-auto">
              {log.explanation_text || '—'}
            </pre>
          </div>

          {/* Rules triggered */}
          <div>
            <p className="font-medium text-gray-700 mb-1">Rules Triggered</p>
            <div className="flex flex-wrap gap-1">
              {rules.length ? rules.map(r => (
                <span key={r} className="bg-njit-navy text-white text-xs px-2 py-0.5 rounded font-mono">{r}</span>
              )) : <span className="text-gray-400 italic">none</span>}
            </div>
          </div>

          {/* Override details */}
          {log.reviewer_status === 'overridden' && (
            <div className="border border-blue-200 rounded p-3 bg-blue-50">
              <p className="font-medium text-blue-800 mb-1">Override Details</p>
              <p className="text-blue-700"><strong>Reason:</strong> {log.override_reason || '—'}</p>
              <p className="text-blue-700 mt-1">
                <strong>Changed:</strong>{' '}
                {[
                  log.override_category && `Category → ${log.override_category}`,
                  log.override_type && `Type → ${log.override_type}`,
                  log.override_level && `Level → ${log.override_level}`,
                ].filter(Boolean).join(' | ') || '—'}
              </p>
              {log.final_locked_decision && (
                <p className="text-blue-700 mt-1">
                  <strong>Final Decision:</strong> {log.final_locked_decision}
                </p>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="flex gap-6 text-xs text-gray-500">
            <span>Classified: {fmtDate(log.created_at)}</span>
            {log.reviewed_at && <span>Reviewed: {fmtDate(log.reviewed_at)}</span>}
            {log.reviewer_id && <span>Reviewer: {log.reviewer_id}</span>}
          </div>
        </div>
      </td>
    </tr>
  )
}

export default function GovernanceLogs() {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)         // 0-based
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedId, setExpandedId] = useState(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchPage = useCallback(async (p) => {
    setLoading(true); setError('')
    try {
      const data = await getLogs(PAGE_SIZE, p * PAGE_SIZE)
      setRecords(data.records)
      setTotal(data.total)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchPage(page) }, [page, fetchPage])

  // Client-side search on current page
  const filtered = search.trim()
    ? records.filter(r => r.badge_title?.toLowerCase().includes(search.toLowerCase()))
    : records

  function toggleExpand(id) {
    setExpandedId(prev => prev === id ? null : id)
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">Governance Logs</h1>
          <p className="text-gray-600 text-sm mt-0.5">{total} total classification records</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="bg-njit-red text-white px-4 py-2 rounded text-sm font-medium hover:bg-njit-red-dark"
        >
          + Submit Badge
        </button>
      </div>

      {/* Search bar */}
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Filter by badge title…"
        className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-sm focus:outline-none focus:ring-2 focus:ring-njit-red"
      />

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <tr>
                  <th className="px-4 py-3 text-left">Badge Title</th>
                  <th className="px-4 py-3 text-left">Issuer</th>
                  <th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Level</th>
                  <th className="px-4 py-3 text-left">Confidence</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center text-gray-400 italic py-8">
                      {search ? 'No records match your search.' : 'No records yet.'}
                    </td>
                  </tr>
                )}
                {filtered.map(log => (
                  <>
                    <tr
                      key={log.id}
                      onClick={() => toggleExpand(log.id)}
                      className="hover:bg-gray-50 cursor-pointer"
                    >
                      <td className="px-4 py-3 font-medium text-njit-navy max-w-[200px] truncate">
                        {log.badge_title}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{log.issuer || '—'}</td>
                      <td className="px-4 py-3 text-gray-700 max-w-[180px] truncate">
                        {log.recommended_category || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-700">{log.recommended_type || '—'}</td>
                      <td className="px-4 py-3 text-gray-700">{log.recommended_level || '—'}</td>
                      <td className="px-4 py-3">
                        <ConfBadge level={log.confidence} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={log.reviewer_status} />
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(log.created_at)}</td>
                    </tr>
                    <DetailRow expanded={expandedId === log.id} log={log} />
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>Page {page + 1} of {totalPages} ({total} records)</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                ← Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
