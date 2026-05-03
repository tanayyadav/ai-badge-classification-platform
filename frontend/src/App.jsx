/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Root component — routing, navigation, and reviewer route protection.
 */

import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import SubmitBadge from './pages/SubmitBadge'
import ReviewResult from './pages/ReviewResult'
import GovernanceLogs from './pages/GovernanceLogs'
import SubmissionConfirmation from './pages/SubmissionConfirmation'
import ReviewerLogin from './pages/reviewer/ReviewerLogin'
import ReviewerDashboard from './pages/reviewer/ReviewerDashboard'
import ReviewerReview from './pages/reviewer/ReviewerReview'
import ProtectedRoute from './components/ProtectedRoute'
import { useReviewer } from './context/ReviewerContext'

function Nav() {
  const { isAuthenticated, logout } = useReviewer()
  const navigate = useNavigate()

  const linkCls = ({ isActive }) =>
    `text-sm font-medium px-3 py-1.5 rounded transition-colors
     ${isActive
       ? 'bg-white text-njit-red font-semibold'
       : 'text-white/80 hover:text-white hover:bg-white/10'}`

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <header className="bg-njit-navy text-white">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <NavLink to="/" className="text-white font-bold text-lg tracking-tight hover:opacity-90">
          NJIT Badge Classification
        </NavLink>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkCls}>Submit Badge</NavLink>
          <NavLink to="/logs" className={linkCls}>Logs</NavLink>
          {isAuthenticated ? (
            <>
              <NavLink to="/reviewer/dashboard" className={linkCls}>Dashboard</NavLink>
              <button
                onClick={handleLogout}
                className="text-sm font-medium px-3 py-1.5 rounded transition-colors text-white/80 hover:text-white hover:bg-white/10"
              >
                Sign Out
              </button>
            </>
          ) : (
            <NavLink to="/reviewer/login" className={linkCls}>Reviewer</NavLink>
          )}
        </nav>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Nav />
        <main>
          <Routes>
            <Route path="/" element={<SubmitBadge />} />
            <Route path="/review/:logId" element={<ReviewResult />} />
            <Route path="/logs" element={<GovernanceLogs />} />
            <Route path="/submit/confirmation" element={<SubmissionConfirmation />} />
            <Route path="/reviewer/login" element={<ReviewerLogin />} />
            <Route
              path="/reviewer/dashboard"
              element={
                <ProtectedRoute>
                  <ReviewerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reviewer/review/:token"
              element={<ReviewerReview />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
