/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * SubmissionConfirmation — shown after a badge is classified.
 * Displays:
 * - Green checkmark + badge title
 * - Submitter email confirmation
 * - Reviewer email who will receive the review link
 * - Two action buttons: Submit Another | View Logs
 */

import { useLocation, useNavigate } from 'react-router-dom'

export default function SubmissionConfirmation() {
  const location = useLocation()
  const navigate = useNavigate()

  const {
    badgeTitle,
    submitterEmail,
    reviewerEmail,
    logId,
  } = location.state || {}

  // Fallback if navigated directly without state
  if (!logId) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4 text-center space-y-4">
        <p className="text-gray-500">No submission data found.</p>
        <button
          onClick={() => navigate('/')}
          className="bg-njit-red text-white px-5 py-2 rounded font-medium hover:bg-njit-red-dark"
        >
          Submit a Badge
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto py-16 px-4 space-y-6 text-center">
      {/* Checkmark */}
      <div className="flex items-center justify-center">
        <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-njit-navy">Badge Submitted!</h1>
        {badgeTitle && (
          <p className="text-gray-600 text-sm">
            <span className="font-medium">{badgeTitle}</span> has been classified and is pending review.
          </p>
        )}
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-5 text-left space-y-3 text-sm">
        {submitterEmail && (
          <div className="flex items-start gap-3">
            <span className="text-gray-400 mt-0.5">📬</span>
            <div>
              <p className="font-medium text-gray-700">Your confirmation</p>
              <p className="text-gray-500">A notification will be sent to <strong>{submitterEmail}</strong> once the review is complete.</p>
            </div>
          </div>
        )}
        {reviewerEmail && (
          <div className="flex items-start gap-3">
            <span className="text-gray-400 mt-0.5">🔗</span>
            <div>
              <p className="font-medium text-gray-700">Reviewer notified</p>
              <p className="text-gray-500">A review link has been sent to <strong>{reviewerEmail}</strong>.</p>
            </div>
          </div>
        )}
        {!submitterEmail && !reviewerEmail && (
          <p className="text-gray-500">The classification is pending review. Check the Logs page for status.</p>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="bg-njit-red text-white px-6 py-2.5 rounded font-medium hover:bg-njit-red-dark w-full sm:w-auto"
        >
          Submit Another Badge
        </button>
        <button
          onClick={() => navigate('/logs')}
          className="border border-gray-300 text-gray-700 px-6 py-2.5 rounded font-medium hover:bg-gray-50 w-full sm:w-auto"
        >
          View All Logs
        </button>
      </div>
    </div>
  )
}
