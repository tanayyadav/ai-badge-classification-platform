/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * React application entry point with ReviewerProvider context.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ReviewerProvider } from './context/ReviewerContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ReviewerProvider>
      <App />
    </ReviewerProvider>
  </StrictMode>,
)
