/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Shared UI primitives — used across SubmitBadge, ReviewResult, GovernanceLogs.
 * No new npm packages. Tailwind CSS only. NJIT brand colors via CSS vars.
 */

// ── ConfidenceBadge ────────────────────────────────────────────────────────────
const CONF_STYLES = {
  High:   'bg-green-100 text-green-800 border border-green-200',
  Medium: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
  Low:    'bg-red-100 text-red-800 border border-red-200',
}
const CONF_DOT = {
  High:   'bg-green-500',
  Medium: 'bg-yellow-500',
  Low:    'bg-red-500',
}

export function ConfidenceBadge({ confidence, size = 'md' }) {
  if (!confidence) return null
  const base = size === 'lg'
    ? 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold'
    : 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold'
  const styles = CONF_STYLES[confidence] || 'bg-gray-100 text-gray-700 border border-gray-200'
  const dot = CONF_DOT[confidence] || 'bg-gray-400'
  return (
    <span className={`${base} ${styles}`}>
      <span className={`rounded-full flex-shrink-0 ${size === 'lg' ? 'w-2 h-2' : 'w-1.5 h-1.5'} ${dot}`} />
      {confidence}
    </span>
  )
}

// ── StatusPill ─────────────────────────────────────────────────────────────────
const STATUS_STYLES = {
  pending:    'bg-gray-100 text-gray-600 border border-gray-200',
  accepted:   'bg-green-100 text-green-700 border border-green-200',
  overridden: 'bg-blue-100 text-blue-700 border border-blue-200',
}
const STATUS_LABELS = {
  pending:    'Pending Review',
  accepted:   'Accepted',
  overridden: 'Overridden',
}

export function StatusPill({ status }) {
  if (!status) return null
  const styles = STATUS_STYLES[status] || 'bg-gray-100 text-gray-600 border border-gray-200'
  const label = STATUS_LABELS[status] || status
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles}`}>
      {label}
    </span>
  )
}

// ── SignalChip ─────────────────────────────────────────────────────────────────
const SOURCE_STYLES = {
  structured_field: { chip: 'bg-green-50 border-green-200 text-green-800', dot: 'bg-green-500', label: 'structured' },
  keyword_rule:     { chip: 'bg-blue-50 border-blue-200 text-blue-800',    dot: 'bg-blue-500',   label: 'keyword' },
  regex_pattern:    { chip: 'bg-yellow-50 border-yellow-200 text-yellow-800', dot: 'bg-yellow-500', label: 'regex' },
  spacy_verb:       { chip: 'bg-purple-50 border-purple-200 text-purple-800', dot: 'bg-purple-500', label: 'spaCy' },
  llm_extraction:   { chip: 'bg-orange-50 border-orange-200 text-orange-800', dot: 'bg-orange-500', label: 'LLM' },
  criteria_url:     { chip: 'bg-teal-50 border-teal-200 text-teal-800',    dot: 'bg-teal-500',   label: 'URL' },
}
const DEFAULT_SOURCE = { chip: 'bg-gray-50 border-gray-200 text-gray-700', dot: 'bg-gray-400', label: 'derived' }

export function SignalChip({ label, value, source, confidence }) {
  const s = SOURCE_STYLES[source] || DEFAULT_SOURCE
  return (
    <div className={`group relative inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium ${s.chip}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.dot}`} />
      <span className="text-gray-500">{label}:</span>
      <span className="font-semibold truncate max-w-[120px]">{String(value)}</span>
      {/* Tooltip */}
      <span className={`
        absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1
        bg-gray-900 text-white text-xs rounded whitespace-nowrap pointer-events-none
        opacity-0 group-hover:opacity-100 transition-opacity z-10
      `}>
        source: {s.label}{confidence ? ` · ${confidence}` : ''}
      </span>
    </div>
  )
}

// ── StatCard ───────────────────────────────────────────────────────────────────
export function StatCard({ label, value, color = 'gray', icon }) {
  const colors = {
    gray:   'bg-white border-gray-200 text-gray-900',
    green:  'bg-white border-green-200 text-green-700',
    blue:   'bg-white border-blue-200 text-blue-700',
    yellow: 'bg-white border-yellow-200 text-yellow-700',
    red:    'bg-white border-red-200 text-red-700',
  }
  const accent = {
    gray:   'text-gray-400',
    green:  'text-green-400',
    blue:   'text-blue-400',
    yellow: 'text-yellow-400',
    red:    'text-red-400',
  }
  return (
    <div className={`rounded-xl border p-4 flex items-center gap-3 shadow-sm ${colors[color] || colors.gray}`}>
      {icon && (
        <div className={`text-2xl flex-shrink-0 ${accent[color] || accent.gray}`}>
          {icon}
        </div>
      )}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className={`text-2xl font-bold ${colors[color] || colors.gray}`}>{value}</p>
      </div>
    </div>
  )
}

// ── SectionHeader ──────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, icon }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      {icon && <span className="text-njit-red text-lg">{icon}</span>}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">{title}</h3>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

// ── Spinner ────────────────────────────────────────────────────────────────────
export function Spinner({ size = 'md', color = 'white' }) {
  const sz = size === 'sm' ? 'w-3.5 h-3.5' : size === 'lg' ? 'w-6 h-6' : 'w-4 h-4'
  const col = color === 'red' ? 'border-njit-red' : color === 'gray' ? 'border-gray-600' : 'border-white'
  return (
    <span className={`inline-block ${sz} border-2 ${col} border-t-transparent rounded-full animate-spin`} />
  )
}

// ── ErrorBanner ────────────────────────────────────────────────────────────────
export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
      <span className="flex-shrink-0 mt-0.5">⚠️</span>
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} className="flex-shrink-0 text-red-400 hover:text-red-600 font-bold text-base leading-none">
          ×
        </button>
      )}
    </div>
  )
}

// ── CopyButton ─────────────────────────────────────────────────────────────────
import { useState } from 'react'
export function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }
  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      className={`text-xs px-2 py-0.5 rounded border transition-colors ${
        copied
          ? 'bg-green-50 border-green-200 text-green-700'
          : 'bg-gray-50 border-gray-200 text-gray-500 hover:text-gray-700 hover:border-gray-300'
      } ${className}`}
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}
