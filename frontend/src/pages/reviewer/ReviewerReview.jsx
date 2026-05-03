/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ReviewerReview — full review page accessed via a review token link.
 * Route: /reviewer/review/:token
 * - Loads badge data via GET /reviewer/review/{token}
 * - Shows classification result, signals, explanation
 * - Allows Accept or Override
 * - Navigates to /reviewer/dashboard after submit
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getLogByToken, submitReview } from '../../services/api'

const LEVEL_OPTIONS = {
  Souvenir:   ['Souvenir'],
  Achievement:['Foundational', 'Milestone', 'Terminal'],
  Skill:      ['Awareness', 'Application', 'Mastery'],
  Competency: ['Demonstrated', 'Integrated', 'Exemplary'],
}
const CATEGORIES = [
  'Continuing & Professional Education',
  'Faculty & Staff Development',
  'Co-Curricular and Extra-Curricular',
  'Academic',
]
const TYPES = ['Souvenir', 'Achievement', 'Skill', 'Competency']

function ConfBadge({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800 border-green-300',
    Medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    Low:    'bg-red-100 text-red-800 border-red-300',
  }[level] || 'bg-gray-100 text-gray-700 border-gray-300'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>{level || '—'}</span>
}

function ClassificationCard({ label, value, rules, confidence }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-2 text-center">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-bold text-njit-navy">{value || '—'}</p>
      <ConfBadge level={confidence} />
      <p className="text-xs text-gray-400">{rules.join(', ') || '—'}</p>
    </div>
  )
}

export default function ReviewerReview() {
  const { token } = useParams()
  const navigate = useNavigate()

  const [logData, setLogData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [reviewerName, setReviewerName] = useState('')
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [overrideCat, setOverrideCat] = useState('')
  const [overrideType, setOverrideType] = useState('')
  const [overrideLevel, setOverrideLevel] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [overrideSaved, setOverrideSaved] = useState(false)

  useEffect(() => {
    getLogByToken(token)
      .then(data => {
        setLogData(data)
        setOverrideCat(data.recommended_category || '')
        setOverrideType(data.recommended_type || '')
        setOverrideLevel(data.recommended_level || '')
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [token])

  function handleTypeChange(t) {
    setOverrideType(t)
    const opts = LEVEL_OPTIONS[t] || []
    if (!opts.includes(overrideLevel)) setOverrideLevel(opts[0] || '')
  }

  // Tanay's Changes:

  async function handleAccept() {
    if (!reviewerName.trim()) { setSubmitError('Reviewer name is required.'); return }
    setSubmitting(true); setSubmitError('')
    try {
      await submitReview({
        review_token: token,
        reviewer_status: 'accepted',
        reviewer_id: reviewerName.trim(),
      })
      navigate('/reviewer/dashboard')
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }
// Tanay's Change
  async function handleOverride() {
  if (!reviewerName.trim()) {
    setSubmitError('Reviewer name is required.')
    return
  }

  if (!overrideReason.trim()) {
    setSubmitError('Override reason is required.')
    return
  }

  if (!overrideCat && !overrideType && !overrideLevel) {
    setSubmitError('Please select at least one override value.')
    return
  }

  setSubmitting(true)
  setSubmitError('')

  try {
    await submitReview({
      review_token: token,
      reviewer_status: 'overridden',
      reviewer_id: reviewerName.trim(),
      override_reason: overrideReason.trim(),
      override_category: overrideCat || null,
      override_type: overrideType || null,
      override_level: overrideLevel || null,
    })

    // Show popup instead of redirect
    setOverrideSaved(true)

  } catch (err) {
    setSubmitError(err.message)
  } finally {
    setSubmitting(false)
  }
}

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-8 px-4">
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-5 space-y-2">
          <p className="font-semibold">Unable to load this review</p>
          <p className="text-sm">{error}</p>
          <button
            onClick={() => navigate('/reviewer/dashboard')}
            className="text-sm text-njit-navy hover:underline"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const triggeredRules = logData?.triggered_rules || []
  const s1Rules = triggeredRules.filter(r => r.startsWith('S1') || r.startsWith('IR'))
  const s2Rules = triggeredRules.filter(r => r.startsWith('S2'))
  const s3Rules = triggeredRules.filter(r => r.startsWith('S3'))

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">{logData?.badge_title}</h1>
          {logData?.issuer && <p className="text-gray-600 text-sm mt-0.5">Issuer: {logData.issuer}</p>}
          {logData?.submitter_email && (
            <p className="text-gray-500 text-xs mt-0.5">Submitted by: {logData.submitter_email}</p>
          )}
        </div>
        <button
          onClick={() => navigate('/reviewer/dashboard')}
          className="text-sm text-njit-navy hover:underline"
        >
          ← Dashboard
        </button>
      </div>

      {/* Classification Result */}
      <div className="border border-gray-200 rounded-lg p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-njit-navy">System Recommendation</h2>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            Confidence: <ConfBadge level={logData?.confidence} />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <ClassificationCard
            label="Stage 1 — Category"
            value={logData?.recommended_category}
            rules={s1Rules}
            confidence={logData?.confidence}
          />
          <ClassificationCard
            label="Stage 2 — Type"
            value={logData?.recommended_type}
            rules={s2Rules}
            confidence={logData?.confidence}
          />
          <ClassificationCard
            label="Stage 3 — Level"
            value={logData?.recommended_level}
            rules={s3Rules}
            confidence={logData?.confidence}
          />
        </div>
      </div>

      {/* Explanation */}
      <div className="border border-gray-200 rounded-lg p-5 space-y-3">
        <h2 className="text-base font-semibold text-njit-navy">Classification Explanation</h2>
        <div className="bg-gray-50 rounded p-4 text-sm font-mono leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
          {logData?.explanation_text || 'No explanation available.'}
        </div>
      </div>

      {/* Review Actions */}
      <div className="border border-gray-200 rounded-lg p-5 space-y-4">
        <h2 className="text-base font-semibold text-njit-navy">Your Decision</h2>

        {submitError && (
          <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">{submitError}</div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Your Name *</label>
          <input
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-xs focus:outline-none focus:ring-2 focus:ring-njit-red"
            placeholder="Your name"
            value={reviewerName}
            onChange={e => setReviewerName(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={handleAccept}
            disabled={submitting}
            className="bg-green-600 text-white px-6 py-2 rounded font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {submitting && !overrideOpen ? 'Submitting…' : 'Accept Classification'}
          </button>
          <span className="text-sm text-gray-500">or</span>
          <button
            onClick={() => setOverrideOpen(o => !o)}
            className="border border-gray-300 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-50"
          >
            {overrideOpen ? 'Cancel Override' : 'Override Classification'}
          </button>
        </div>

        {overrideOpen && (
          <div className="border border-yellow-200 rounded-lg p-4 bg-yellow-50 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={overrideCat}
                  onChange={e => setOverrideCat(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                >
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                <select
                  value={overrideType}
                  onChange={e => handleTypeChange(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                >
                  {TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Level</label>
                <select
                  value={overrideLevel}
                  onChange={e => setOverrideLevel(e.target.value)}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                >
                  {(LEVEL_OPTIONS[overrideType] || []).map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Override Reason *</label>
              <textarea
                rows={3}
                value={overrideReason}
                onChange={e => setOverrideReason(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                placeholder="Explain why the classification needs to be changed…"
              />
            </div>
            <button
              onClick={handleOverride}
              disabled={submitting}
              className="bg-njit-navy text-white px-5 py-2 rounded text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {submitting && overrideOpen ? 'Submitting…' : 'Submit Override'}
            </button>
          </div>
        )}
      </div>
      {overrideSaved && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 text-center space-y-4">

            <div className="mx-auto w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
              <span className="text-green-700 text-3xl">✓</span>
            </div>

            <h2 className="text-xl font-bold text-njit-navy">
              Override Saved Successfully
            </h2>

            <p className="text-sm text-gray-600">
              This overridden classification has been saved and will be used for future badge assignments.
            </p>

            <button
              onClick={() => navigate('/reviewer/dashboard')}
              className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark"
            >
              Go to Dashboard
            </button>

          </div>
        </div>
      )}
    </div>
  )
}
