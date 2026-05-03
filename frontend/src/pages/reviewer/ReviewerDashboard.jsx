/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ReviewerDashboard — shows stats, pending queue, and recently reviewed badges.
 * Protected: requires reviewer authentication.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReviewer } from '../../context/ReviewerContext'
import { getReviewerQueue } from '../../services/api'

function StatCard({ label, value, color }) {
  const colorMap = {
    blue: 'text-blue-700 bg-blue-50 border-blue-200',
    yellow: 'text-yellow-700 bg-yellow-50 border-yellow-200',
    green: 'text-green-700 bg-green-50 border-green-200',
    purple: 'text-purple-700 bg-purple-50 border-purple-200',
  }
  return (
    <div className={`border rounded-lg p-4 text-center ${colorMap[color] || colorMap.blue}`}>
      <div className="text-3xl font-bold">{value ?? '—'}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
    </div>
  )
}

function StatusPill({ status }) {
  const cls = {
    pending:        'bg-gray-100 text-gray-700',
    pending_review: 'bg-yellow-100 text-yellow-800',
    accepted:       'bg-green-100 text-green-800',
    overridden:     'bg-blue-100 text-blue-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>
      {status?.replace('_', ' ')}
    </span>
  )
}

function ConfPill({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800 border-green-300',
    Medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    Low:    'bg-red-100 text-red-800 border-red-300',
  }[level] || 'bg-gray-100 text-gray-700 border-gray-300'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>{level || '—'}</span>
  )
}

function QueueTable({ rows, onReview, emptyMsg }) {
  if (!rows || rows.length === 0) {
    return <p className="text-sm text-gray-500 italic py-4">{emptyMsg}</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <th className="pb-2 pr-4">Badge</th>
            <th className="pb-2 pr-4">Issuer</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Confidence</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2 pr-4">Submitted</th>
            <th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(log => (
            <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium text-njit-navy max-w-[200px] truncate">
                {log.badge_title}
              </td>
              <td className="py-2 pr-4 text-gray-600">{log.issuer || '—'}</td>
              <td className="py-2 pr-4 text-gray-600">
                {log.recommended_type || '—'} / {log.recommended_level || '—'}
              </td>
              <td className="py-2 pr-4"><ConfPill level={log.confidence} /></td>
              <td className="py-2 pr-4"><StatusPill status={log.reviewer_status} /></td>
              <td className="py-2 pr-4 text-gray-400 text-xs">
                {log.created_at ? new Date(log.created_at).toLocaleDateString() : '—'}
              </td>
              <td className="py-2">
                {log.review_token ? (
                  <button
                    onClick={() => onReview(log.review_token)}
                    className="text-njit-red text-xs font-medium hover:underline"
                  >
                    Review →
                  </button>
                ) : (
                  <button
                    onClick={() => onReview(null, log.id)}
                    className="text-gray-500 text-xs font-medium hover:underline"
                  >
                    View →
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ReviewerDashboard() {
  const { logout } = useReviewer()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getReviewerQueue()
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  function handleReview(token, logId) {
    if (token) {
      navigate(`/reviewer/review/${token}`)
    } else if (logId) {
      navigate(`/review/${logId}`)
    }
  }

  function handleLogout() {
    logout()
    navigate('/')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">Reviewer Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Review and approve badge classifications.</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700 border border-gray-300 px-3 py-1.5 rounded"
        >
          Sign Out
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-4 text-sm">{error}</div>
      )}

      {data && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Total Badges" value={data.stats.total} color="blue" />
            <StatCard label="Pending Review" value={data.stats.pending_review} color="yellow" />
            <StatCard label="Accepted" value={data.stats.accepted} color="green" />
            <StatCard label="Overridden" value={data.stats.overridden} color="purple" />
          </div>

          {/* Pending queue */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-njit-navy">
              Pending Review
              {data.stats.pending_review > 0 && (
                <span className="ml-2 text-sm font-normal text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded">
                  {data.stats.pending_review} waiting
                </span>
              )}
            </h2>
            <QueueTable
              rows={data.pending}
              onReview={handleReview}
              emptyMsg="No badges pending review."
            />
          </div>

          {/* Recently reviewed */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-njit-navy">Recently Reviewed</h2>
            <QueueTable
              rows={data.recently_reviewed}
              onReview={handleReview}
              emptyMsg="No badges reviewed yet."
            />
          </div>
        </>
      )}
    </div>
  )
}
