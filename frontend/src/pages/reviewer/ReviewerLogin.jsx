/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ReviewerLogin — password gate for the reviewer dashboard.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReviewer } from '../../context/ReviewerContext'

export default function ReviewerLogin() {
  const { login } = useReviewer()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!password.trim()) { setError('Password is required.'); return }
    setLoading(true)
    setError('')
    try {
      await login(password)
      navigate('/reviewer/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Incorrect password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white border border-gray-200 rounded-xl shadow-sm p-8 space-y-6">
        <div className="text-center space-y-1">
          <div className="text-4xl">🔒</div>
          <h1 className="text-xl font-bold text-njit-navy">Reviewer Login</h1>
          <p className="text-sm text-gray-500">Enter the reviewer password to access the dashboard.</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoFocus
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-njit-red"
              placeholder="Enter reviewer password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-njit-red text-white py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
