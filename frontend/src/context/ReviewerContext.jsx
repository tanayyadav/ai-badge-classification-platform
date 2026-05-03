/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ReviewerContext — in-memory authentication state for the reviewer dashboard.
 * The access token is kept in React state only (not localStorage) so it
 * is automatically cleared when the tab closes. This is intentional for
 * a prototype — no persistent session management needed.
 */

import { createContext, useContext, useState } from 'react'
import { reviewerAuth, _setReviewerToken } from '../services/api'

const ReviewerContext = createContext(null)

export function ReviewerProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null)

  const isAuthenticated = accessToken !== null

  async function login(password) {
    const data = await reviewerAuth(password)
    setAccessToken(data.access_token)
    _setReviewerToken(data.access_token)
  }

  function logout() {
    setAccessToken(null)
    _setReviewerToken(null)
  }

  return (
    <ReviewerContext.Provider value={{ isAuthenticated, accessToken, login, logout }}>
      {children}
    </ReviewerContext.Provider>
  )
}

export function useReviewer() {
  const ctx = useContext(ReviewerContext)
  if (!ctx) throw new Error('useReviewer must be used inside ReviewerProvider')
  return ctx
}
