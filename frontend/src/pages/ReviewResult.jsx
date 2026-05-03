/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Displays classification results with extracted signals, explanation, and reviewer note.
 */

import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { getLog } from '../services/api'

// ─── Confidence badge ─────────────────────────────────────────────────────────
function ConfBadge({ level }) {
  const cls = {
    High:   'bg-green-100 text-green-800 border-green-300',
    Medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    Low:    'bg-red-100 text-red-800 border-red-300',
  }[level] || 'bg-gray-100 text-gray-700 border-gray-300'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>{level || '—'}</span>
  )
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const cls = {
    pending:    'bg-gray-100 text-gray-700',
    accepted:   'bg-green-100 text-green-800',
    overridden: 'bg-blue-100 text-blue-800',
  }[status] || 'bg-gray-100 text-gray-700'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{status}</span>
}

// ─── Signal Panel (Section 9 NLP signals) ────────────────────────────────────

const SIGNAL_FIELDS = [
  ['audience_signal', 'Audience Signal'],
  ['context_signal', 'Context Signal'],
  ['rigor_signal', 'Rigor Signal'],
  ['evidence_signal', 'Evidence Signal'],
  ['self_declared_level', 'Declared Level'],
  ['level_phrase_matched', 'Level Phrase'],
  ['bloom_level', 'Bloom Level'],
  ['bloom_verbs_detected', 'Bloom Verbs'],
]

function SignalPanel({ bfs, missingSignals }) {
  if (!bfs) return null
  const missing = missingSignals || []

  const sourceCls = (src) => {
    if (!src) return 'bg-gray-50 border-gray-200'
    if (src === 'structured_field' || src === 'keyword_rule') return 'bg-green-50 border-green-200'
    if (src === 'regex_pattern' || src === 'spacy_verb') return 'bg-yellow-50 border-yellow-200'
    return 'bg-gray-50 border-gray-200'
  }

  const presentSignals = SIGNAL_FIELDS.filter(([field]) => {
    const val = bfs[field]
    return val !== null && val !== undefined && val !== '' && !(Array.isArray(val) && val.length === 0)
  })

  return (
    <div className="border border-gray-200 rounded-lg p-5 space-y-3">
      <h2 className="text-base font-semibold text-njit-navy">Extracted Signals</h2>

      {presentSignals.length === 0 && missing.length === 0 && (
        <p className="text-sm text-gray-500 italic">No signals detected.</p>
      )}

      <div className="space-y-2">
        {presentSignals.map(([field, label]) => {
          const val = bfs[field]
          const src = field === 'bloom_level' || field === 'bloom_verbs_detected'
            ? 'spacy_verb'
            : (bfs.level_signal_source || bfs.audience_signal_source || null)
          const displayVal = Array.isArray(val) ? val.join(', ') : String(val)

          return (
            <div key={field} className={`flex items-center gap-2 border rounded px-3 py-1.5 text-sm ${sourceCls(src)}`}>
              <span className="font-medium text-gray-600 w-36 shrink-0">{label}</span>
              <span className="text-gray-900 flex-1">{displayVal}</span>
              {src && <span className="text-xs text-gray-400 shrink-0">{src}</span>}
            </div>
          )
        })}

        {missing.map(field => (
          <div key={field} className="flex items-center gap-2 border border-red-300 rounded px-3 py-1.5 text-sm bg-red-50">
            <span className="font-medium text-red-700 w-36 shrink-0">{field}</span>
            <span className="text-red-600 italic flex-1">not extracted</span>
            <span className="text-xs text-red-500 shrink-0">missing</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Classification Result Panel ──────────────────────────────────────────────

function ClassificationPanel({ result }) {
  const { classification, rules_triggered } = result
  const stages = [
    { label: 'Stage 1 — Category', value: classification.category },
    { label: 'Stage 2 — Type', value: classification.type },
    { label: 'Stage 3 — Level', value: classification.level },
  ]
  const s1Rules = rules_triggered.filter(r => r.startsWith('S1') || r.startsWith('IR'))
  const s2Rules = rules_triggered.filter(r => r.startsWith('S2'))
  const s3Rules = rules_triggered.filter(r => r.startsWith('S3'))
  const ruleGroups = [s1Rules, s2Rules, s3Rules]

  return (
    <div className="border border-gray-200 rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-njit-navy">Classification Result</h2>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          Overall: <ConfBadge level={classification.confidence} />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stages.map(({ label, value }, i) => (
          <div key={label} className="border border-gray-200 rounded-lg p-4 space-y-2 text-center">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
            <p className="text-lg font-bold text-njit-navy">{value || '—'}</p>
            <ConfBadge level={classification.confidence} />
            <p className="text-xs text-gray-400">{ruleGroups[i].join(', ') || '—'}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Explanation Panel ────────────────────────────────────────────────────────

function ExplanationPanel({ explanation }) {
  return (
    <div className="border border-gray-200 rounded-lg p-5 space-y-3">
      <h2 className="text-base font-semibold text-njit-navy">Classification Explanation</h2>
      <div className="bg-gray-50 rounded p-4 text-sm font-mono leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap">
        {explanation || 'No explanation available.'}
      </div>
    </div>
  )
}

// ─── Reviewer Note Panel ──────────────────────────────────────────────────────

function ReviewerNotePanel({ logId }) {
  const navigate = useNavigate()
  return (
    <div className="border border-blue-200 rounded-lg p-5 bg-blue-50 space-y-2">
      <h2 className="text-base font-semibold text-njit-navy">Ready for Review</h2>
      <p className="text-sm text-blue-800">
        This badge classification is pending reviewer approval.
        Reviewers can accept or override classifications from the{' '}
        <button
          onClick={() => navigate('/reviewer/dashboard')}
          className="font-medium underline hover:text-njit-navy"
        >
          Reviewer Dashboard
        </button>.
      </p>
      <p className="text-xs text-blue-600">Log ID: {logId}</p>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ReviewResult() {
  const { logId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  // Try to use state passed from SubmitBadge, otherwise fetch from API
  const [result, setResult] = useState(location.state?.result || null)
  const [bfs, setBfs] = useState(location.state?.bfs || null)
  const [log, setLog] = useState(null)
  const [loading, setLoading] = useState(!result)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!result) {
      // Page was refreshed or navigated directly — load from logs
      setLoading(true)
      getLog(logId)
        .then(logData => {
          setLog(logData)
          // Reconstruct minimal result shape from log data
          setResult({
            badge_id: logData.badge_id,
            badge_title: logData.badge_title,
            issuer: logData.issuer,
            classification: {
              category: logData.recommended_category,
              type: logData.recommended_type,
              level: logData.recommended_level,
              confidence: logData.confidence,
              level_branch_used: null,
            },
            rules_triggered: JSON.parse(logData.triggered_rules || '[]'),
            explanation: logData.explanation_text,
            follow_up_needed: false,
            missing_signals: [],
            review_recommended: false,
            governance: {
              log_id: logData.id,
              reviewer_status: logData.reviewer_status,
            },
          })
          try {
            setBfs(JSON.parse(logData.normalized_facts))
          } catch { /* ignore */ }
        })
        .catch(err => setError(err.message))
        .finally(() => setLoading(false))
    }
  }, [logId, result])

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
        <div className="bg-red-50 border border-red-300 text-red-800 rounded p-4">{error}</div>
      </div>
    )
  }

  if (!result) return null

  const alreadyReviewed = log?.reviewer_status === 'accepted' || log?.reviewer_status === 'overridden'

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-njit-navy">{result.badge_title}</h1>
          {result.issuer && <p className="text-gray-600 text-sm mt-0.5">Issuer: {result.issuer}</p>}
        </div>
        <button
          onClick={() => navigate('/logs')}
          className="text-sm text-njit-navy hover:underline"
        >
          ← View all logs
        </button>
      </div>

      {result.follow_up_needed && (
        <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 rounded p-3 text-sm">
          <strong>Follow-up recommended:</strong> Some signals were missing — review may benefit from additional context.
        </div>
      )}

      <SignalPanel bfs={bfs} missingSignals={result.missing_signals} />
      <ClassificationPanel result={result} />
      <ExplanationPanel explanation={result.explanation} />

      {alreadyReviewed && log ? (
        <div className="border border-green-300 rounded-lg p-5 bg-green-50 space-y-1">
          <p className="font-semibold text-green-800">
            Already reviewed — <StatusBadge status={log.reviewer_status} />
          </p>
          {log.final_locked_decision && (
            <p className="text-sm text-green-700">Final: <strong>{log.final_locked_decision}</strong></p>
          )}
        </div>
      ) : (
        <ReviewerNotePanel logId={logId} />
      )}
    </div>
  )
}
