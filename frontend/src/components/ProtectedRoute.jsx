/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * ProtectedRoute — redirects unauthenticated users to the reviewer login page.
 */

import { Navigate } from 'react-router-dom'
import { useReviewer } from '../context/ReviewerContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated } = useReviewer()
  if (!isAuthenticated) {
    return <Navigate to="/reviewer/login" replace />
  }
  return children
}
