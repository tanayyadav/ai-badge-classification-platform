/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * api.js — all HTTP calls to the backend, centralised here.
 * All components import from this file only.
 * No direct fetch or axios calls anywhere else.
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const http = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

/** Extract a human-readable error message from an axios error. */
function apiError(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return new Error(detail)
  if (Array.isArray(detail)) return new Error(detail.map(d => d.msg).join('; '))
  return new Error(err.message || 'Unknown API error')
}

/**
 * POST /ingest
 * @param {string} inputType  "obv3_json" | "form" | "free_text"
 * @param {object} payload    Parsed JSON object, form fields object, or {text: string}
 * @returns {Promise<object>} BadgeFactSheet
 */
export async function ingestBadge(inputType, payload) {
  try {
    const { data } = await http.post('/ingest', { input_type: inputType, payload })
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * POST /classify
 * @param {object} badgeFactSheet  Full BFS object returned by /ingest
 * @param {object} [meta]          Optional { submitter_email, reviewer_email }
 * @returns {Promise<object>}      ClassificationResult
 */
export async function classifyBadge(badgeFactSheet, meta = {}) {
  try {
    const { data } = await http.post('/classify', { ...badgeFactSheet, ...meta })
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * POST /review
 * @param {object} reviewPayload  {log_id?, review_token?, reviewer_status, reviewer_id,
 *                                  override_reason, override_category,
 *                                  override_type, override_level}
 * @returns {Promise<object>}     Updated GovernanceLog
 */
export async function submitReview(reviewPayload) {
  try {
    const { data } = await http.post('/review', reviewPayload)
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * GET /logs
 * @param {number} limit   Records per page (default 20)
 * @param {number} offset  Skip N records (default 0)
 * @returns {Promise<{total:number, offset:number, limit:number, records:object[]}>}
 */
export async function getLogs(limit = 20, offset = 0) {
  try {
    const { data } = await http.get('/logs', { params: { limit, offset } })
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * GET /logs/{logId}
 * @param {string} logId
 * @returns {Promise<object>} Full GovernanceLog record
 */
export async function getLog(logId) {
  try {
    const { data } = await http.get(`/logs/${logId}`)
    return data
  } catch (err) {
    throw apiError(err)
  }
}

// ---------------------------------------------------------------------------
// Reviewer API
// ---------------------------------------------------------------------------

/**
 * POST /reviewer/auth
 * @param {string} password  Reviewer shared password
 * @returns {Promise<{access_token: string}>}
 */
export async function reviewerAuth(password) {
  try {
    const { data } = await http.post('/reviewer/auth', { password })
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * GET /reviewer/queue  (requires reviewer auth)
 * @returns {Promise<{stats, pending, recently_reviewed}>}
 */
export async function getReviewerQueue() {
  const token = _getReviewerToken()
  try {
    const { data } = await http.get('/reviewer/queue', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * GET /reviewer/review/{token}
 * @param {string} reviewToken  Opaque review token from the email link
 * @returns {Promise<object>}   Log data ready for reviewer UI
 */
export async function getLogByToken(reviewToken) {
  try {
    const { data } = await http.get(`/reviewer/review/${reviewToken}`)
    return data
  } catch (err) {
    throw apiError(err)
  }
}

/**
 * GET /health
 * @returns {Promise<{status:string, version:string}>}
 */
export async function getHealth() {
  try {
    const { data } = await http.get('/health')
    return data
  } catch (err) {
    throw apiError(err)
  }
}

// ---------------------------------------------------------------------------
// Internal helper — reads reviewer access token from ReviewerContext is not
// possible here (no React hooks in a plain module). Components that call
// getReviewerQueue must inject the token via the ReviewerContext instead.
// We use a simple module-level variable kept in sync by ReviewerContext.
// ---------------------------------------------------------------------------

let _reviewerAccessToken = null

/** Called by ReviewerContext when token changes. */
export function _setReviewerToken(token) {
  _reviewerAccessToken = token
}

function _getReviewerToken() {
  if (!_reviewerAccessToken) throw new Error('Not authenticated as reviewer.')
  return _reviewerAccessToken
}
