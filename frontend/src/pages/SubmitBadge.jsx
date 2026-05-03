/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * Three-tab badge submission page: structured form, JSON paste, and free text.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ingestBadge, classifyBadge } from '../services/api'
import {
  translateFormAnswers,
  translateAreaAnswer,
  translateVerificationAnswer,
  translateAudienceAnswer,
  AREA_OPTIONS,
  LDI_AUDIENCE_OPTIONS,
  AUDIENCE_OPTIONS,
  VERIFICATION_OPTIONS,
  PASS_SCORE_OPTIONS,
} from '../utils/formTranslator'

// ── Small shared UI primitives ────────────────────────────────────────────────

function Label({ children }) {
  return <label className="block text-sm font-medium text-gray-700 mb-1">{children}</label>
}

function Input({ error, ...props }) {
  return (
    <input
      className={`w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-njit-red
        ${error ? 'border-red-500' : 'border-gray-300'}`}
      {...props}
    />
  )
}

function Textarea({ error, rows = 4, ...props }) {
  return (
    <textarea
      rows={rows}
      className={`w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-njit-red
        ${error ? 'border-red-500' : 'border-gray-300'}`}
      {...props}
    />
  )
}

function FieldGroup({ label, children, helper }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      {children}
      {helper && <p className="text-xs text-gray-500 mt-1">{helper}</p>}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="w-8 h-8 border-4 border-njit-red border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div className="bg-red-50 border border-red-300 text-red-800 rounded p-3 text-sm">
      {message}
    </div>
  )
}

function FieldError({ message }) {
  if (!message) return null
  return <p className="text-red-600 text-xs mt-1">{message}</p>
}

/**
 * Radio card group — renders a list of options as styled selectable cards.
 */
function RadioGroup({ options, value, onChange, name, error }) {
  return (
    <div className={`space-y-2 ${error ? 'ring-1 ring-red-400 rounded-lg p-1' : ''}`}>
      {options.map(opt => (
        <label
          key={opt}
          className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors select-none
            ${value === opt
              ? 'border-njit-red bg-red-50'
              : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'}`}
        >
          <input
            type="radio"
            name={name}
            value={opt}
            checked={value === opt}
            onChange={() => onChange(opt)}
            className="mt-0.5 accent-njit-red flex-shrink-0"
          />
          <span className="text-sm leading-snug text-gray-800">{opt}</span>
        </label>
      ))}
    </div>
  )
}

// ── BFS Confirmation Panel ────────────────────────────────────────────────────

/**
 * Follow-up question for a single missing field.
 * Translates the selected answer immediately and reports BFS fields to parent.
 */
function FollowupQuestion({ field, onAnswer }) {
  const [selected, setSelected] = useState('')

  const QUESTIONS = {
    issuer: {
      label: 'Which area of NJIT issued this badge?',
      options: AREA_OPTIONS,
      translate: translateAreaAnswer,
    },
    assessment_evaluator: {
      label: 'How is the earner evaluated for this badge?',
      options: VERIFICATION_OPTIONS,
      translate: translateVerificationAnswer,
    },
    audience_type: {
      label: 'Who earns this badge?',
      options: AUDIENCE_OPTIONS,
      translate: translateAudienceAnswer,
    },
  }

  const q = QUESTIONS[field]
  if (!q) return null

  function handleSelect(opt) {
    setSelected(opt)
    onAnswer(q.translate(opt))
  }

  return (
    <div>
      <p className="text-sm font-semibold text-gray-800 mb-2">{q.label}</p>
      <RadioGroup
        options={q.options}
        value={selected}
        onChange={handleSelect}
        name={`followup_${field}`}
      />
    </div>
  )
}

/**
 * Plain-language follow-up section shown inside BfsConfirmPanel.
 * inputMode='json': show for missing issuer and/or assessment_evaluator (max 2)
 * inputMode='free_text': show for fields in missing_signals (max 3)
 * inputMode='form': nothing shown
 */
function PlainLanguageFollowups({ bfs, inputMode, onAnswer }) {
  const missing = bfs.missing_signals || []
  const questions = []

  if (inputMode === 'json') {
    if (!bfs.issuer) questions.push('issuer')
    if (!bfs.assessment_evaluator) questions.push('assessment_evaluator')
  } else if (inputMode === 'free_text') {
    const priority = ['issuer', 'assessment_evaluator', 'audience_type']
    for (const f of priority) {
      if (missing.includes(f) && questions.length < 3) questions.push(f)
    }
  }

  if (questions.length === 0) return null

  return (
    <div className="border border-yellow-200 rounded-lg p-4 space-y-5 bg-yellow-50">
      <p className="text-sm font-medium text-yellow-900">
        Please answer {questions.length === 1 ? 'this question' : `these ${questions.length} questions`} to improve the classification:
      </p>
      {questions.map(q => (
        <FollowupQuestion key={q} field={q} onAnswer={onAnswer} />
      ))}
    </div>
  )
}

function BfsConfirmPanel({ bfs, inputMode, onConfirm, onFollowupChange, loading }) {
  const keyFields = [
    ['badge_title', 'Badge Title'],
    ['issuer', 'Issuer'],
    ['badge_description', 'Description'],
    ['earning_criteria_text', 'Earning Criteria'],
    ['assessment_required', 'Assessment Required'],
    ['assessment_type', 'Assessment Type'],
    ['assessment_evaluator', 'Assessment Evaluator'],
    ['canvas_course_code', 'Canvas Course Code'],
    ['canvas_sequence_number', 'Sequence Number'],
    ['audience_type', 'Audience Type'],
    ['bloom_level', 'Bloom Level'],
    ['self_declared_level', 'Declared Level'],
  ]
  const missing = bfs.missing_signals || []
  const needsFollowup = bfs.needs_followup_questions

  

  return (
    <div className="border border-gray-200 rounded-lg p-6 space-y-4">
      <h2 className="text-lg font-semibold text-njit-navy">Extracted Badge Fact Sheet</h2>

      {needsFollowup && (
        <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 rounded p-3 text-sm">
          <strong>Follow-up required:</strong> Some signals could not be extracted automatically.
          Please answer the questions below before classifying.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {keyFields.map(([field, label]) => {
          const val = bfs[field]
          const isMissing = missing.includes(field)
          const hasVal = val !== null && val !== undefined && val !== ''
          return (
            <div
              key={field}
              className={`rounded p-2 text-sm border
                ${isMissing ? 'bg-yellow-50 border-yellow-300' : 'bg-gray-50 border-gray-200'}`}
            >
              <span className="font-medium text-gray-600">{label}: </span>
              <span className={hasVal ? 'text-gray-900' : 'text-gray-400 italic'}>
                {hasVal ? String(val) : 'not detected'}
              </span>
              {isMissing && <span className="ml-2 text-yellow-700 font-semibold text-xs">⚠ missing</span>}
            </div>
          )
        })}
      </div>

      <PlainLanguageFollowups
        bfs={bfs}
        inputMode={inputMode}
        onAnswer={onFollowupChange}
      />

      <button
        onClick={onConfirm}
        disabled={loading}
        className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
      >
        {loading ? 'Classifying…' : 'Confirm & Classify →'}
      </button>
    </div>
  )
}

// ── Free Text Student Follow-up Panel ────────────────────────────────────────
//
// Shown instead of BfsConfirmPanel when input_type === "free_text".
// Asks plain-language student questions (max 3), merges answers, then
// calls classify immediately — no second confirmation round.

const _FT_Q1 = {
  label: 'Where did this activity or training take place at NJIT?',
  signal: 'issuer',
  options: [
    { text: 'It was a professional development or continuing education program', fields: { issuer: 'LDI', audience_type: 'external_professional' } },
    { text: 'It was a student club, leadership, or involvement program',         fields: { issuer: 'OSIL', audience_type: 'njit_student' } },
    { text: 'It was in the Makerspace (3D printing, laser cutting, etc.)',        fields: { issuer: 'Makerspace', audience_type: 'njit_student' } },
    { text: 'It was part of a class or academic program',                         fields: { issuer: 'NCE', audience_type: 'njit_student' } },
    { text: 'It was an administrative requirement (visa, work authorization)',    fields: { issuer: 'OGI', audience_type: 'njit_student' } },
    { text: "I'm not sure", fields: null },
  ],
}

const _FT_Q2 = {
  label: 'How was your work or participation checked?',
  signal: 'assessment_evaluator',
  options: [
    { text: 'I took an online quiz or test',                               fields: { assessment_evaluator: 'auto_assessed',  assessment_type: 'final_assessment' } },
    { text: 'A person watched me do something and said I passed',          fields: { assessment_evaluator: 'expert_scored',  expert_evaluation_required: true, assessment_type: 'practical' } },
    { text: 'I submitted a project or portfolio that someone reviewed',    fields: { assessment_evaluator: 'expert_scored',  expert_evaluation_required: true, assessment_type: 'portfolio' } },
    { text: 'I just showed up — no grading was required',                  fields: { assessment_evaluator: null, assessment_type: 'attendance', assessment_required: 'no' } },
    { text: "I'm not sure", fields: null },
  ],
}

// Q4 — shown only when level signal is genuinely missing.
// Student-reported level uses confidence Medium and source "student_reported".
const _FT_Q4 = {
  label: 'Where does this badge fit in your learning journey?',
  signal: 'self_declared_level',
  options: [
    {
      text: 'It was my first time learning about this topic',
      fields: { self_declared_level: 'Foundational', level_signal_source: 'student_reported' },
    },
    {
      text: 'I had some background and this built on what I knew',
      fields: { self_declared_level: 'Milestone', level_signal_source: 'student_reported' },
    },
    {
      text: 'This was the final or most advanced step in the program',
      fields: { self_declared_level: 'Terminal', level_signal_source: 'student_reported' },
    },
    // "I'm not sure" — never blocks; level stays Unknown; reviewer handles
    { text: "I'm not sure", fields: null },
  ],
}

function FreeTextFollowupPanel({ bfs, onClassify, loading }) {
  const missing = bfs.missing_signals || []

  const showQ1 = !bfs.issuer && missing.includes('issuer')
  const showQ2 = missing.includes('assessment_evaluator')
  const showQ3 = missing.includes('badge_title')
  // Q4 — level is genuinely unknown: no NLP level phrase extracted AND
  // no canvas_sequence_number to drive a structural level rule.
  const showQ4 = !bfs.self_declared_level && bfs.canvas_sequence_number == null

  const [q1, setQ1] = useState(null)   // selected option object
  const [q2, setQ2] = useState(null)
  const [titleText, setTitleText] = useState('')
  const [q4, setQ4] = useState(null)

  // Summary fields — what the NLP already extracted.
  // assessment_type is an internal derived field — never shown as a student concern.
  const summaryFields = [
    ['issuer',           'Issuer'],
    ['audience_type',    'Audience Type'],
    ['badge_description','Description (first 120 chars)'],
  ]

  function buildMergedBfs() {
    const extra = {}
    if (q1?.fields) Object.assign(extra, q1.fields)
    if (q2?.fields) Object.assign(extra, q2.fields)
    if (titleText.trim()) extra.badge_title = titleText.trim()
    // Q4 — student-reported level uses Medium confidence, not High.
    // "I'm not sure" leaves self_declared_level null; reviewer handles it.
    if (q4?.fields) Object.assign(extra, q4.fields)

    // Derive audience_type from issuer when not already set by Q1 answer or BFS.
    // This covers issuers detected by Layer 0 keyword matching on the backend
    // where Q1 was never shown (issuer already present in BFS).
    const effectiveIssuer = extra.issuer ?? bfs.issuer
    const effectiveAudience = extra.audience_type ?? bfs.audience_type
    if (!effectiveAudience && effectiveIssuer) {
      const _ISSUER_AUDIENCE = {
        OSIL:       'njit_student',
        Makerspace: 'njit_student',
        NCE:        'njit_student',
        OGI:        'njit_student',
        // LDI: left null — backend Layer 0 infers from faculty/professional context
      }
      if (_ISSUER_AUDIENCE[effectiveIssuer]) {
        extra.audience_type = _ISSUER_AUDIENCE[effectiveIssuer]
      }
    }

    // Remove from missing_signals any field we showed a question for — whether
    // the student answered it or chose "I'm not sure" or left it blank.
    let updatedMissing = [...missing]
    if (showQ1) updatedMissing = updatedMissing.filter(s => s !== 'issuer')
    if (showQ2) updatedMissing = updatedMissing.filter(s => s !== 'assessment_evaluator')
    updatedMissing = updatedMissing.filter(s => s !== 'badge_title')
    if (showQ4) updatedMissing = updatedMissing.filter(s => s !== 'self_declared_level')

    return {
      ...bfs,
      ...extra,
      missing_signals: updatedMissing,
      needs_followup_questions: updatedMissing.length > 0,
    }
  }

  const questionCount = [showQ1, showQ2, showQ3, showQ4].filter(Boolean).length

  return (
    <div className="border border-gray-200 rounded-lg p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-njit-navy">Almost there!</h2>
        <p className="text-sm text-gray-600 mt-1">
          {questionCount > 0
            ? `We extracted what we could. Answer ${questionCount === 1 ? 'this quick question' : `these ${questionCount} quick questions`} to get a better classification.`
            : 'We extracted everything we need. Click Classify to continue.'}
        </p>
      </div>

      {/* What NLP already found */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {summaryFields.map(([field, label]) => {
          const raw = bfs[field]
          const hasVal = raw !== null && raw !== undefined && raw !== ''
          const display = hasVal
            ? (field === 'badge_description' ? String(raw).slice(0, 120) + (String(raw).length > 120 ? '…' : '') : String(raw))
            : null
          return (
            <div key={field} className="rounded p-2 text-sm border bg-gray-50 border-gray-200">
              <span className="font-medium text-gray-600">{label}: </span>
              <span className={display ? 'text-gray-900' : 'text-gray-400 italic'}>
                {display || 'not detected'}
              </span>
            </div>
          )
        })}
      </div>

      {/* Question 1 — issuer */}
      {showQ1 && (
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{_FT_Q1.label}</p>
          <RadioGroup
            options={_FT_Q1.options.map(o => o.text)}
            value={q1?.text || ''}
            onChange={txt => setQ1(_FT_Q1.options.find(o => o.text === txt))}
            name="ft_q1"
          />
        </div>
      )}

      {/* Question 2 — assessment_evaluator */}
      {showQ2 && (
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{_FT_Q2.label}</p>
          <RadioGroup
            options={_FT_Q2.options.map(o => o.text)}
            value={q2?.text || ''}
            onChange={txt => setQ2(_FT_Q2.options.find(o => o.text === txt))}
            name="ft_q2"
          />
        </div>
      )}

      {/* Question 3 — badge_title */}
      {showQ3 && (
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-1">
            What would you call this badge or achievement?
          </p>
          <p className="text-xs text-gray-500 mb-2">
            Optional — for example: Leadership Workshop, AI Training, Laser Cutting Certification
          </p>
          <Input
            value={titleText}
            onChange={e => setTitleText(e.target.value)}
            placeholder="e.g. Leadership Workshop"
          />
        </div>
      )}

      {/* Question 4 — level (only when genuinely unknown) */}
      {showQ4 && (
        <div>
          <p className="text-sm font-semibold text-gray-800 mb-2">{_FT_Q4.label}</p>
          <p className="text-xs text-gray-500 mb-2">
            Optional — helps us decide whether this is a beginner, intermediate, or advanced badge.
          </p>
          <RadioGroup
            options={_FT_Q4.options.map(o => o.text)}
            value={q4?.text || ''}
            onChange={txt => setQ4(_FT_Q4.options.find(o => o.text === txt))}
            name="ft_q4"
          />
        </div>
      )}

      <button
        onClick={() => onClassify(buildMergedBfs())}
        disabled={loading}
        className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
      >
        {loading ? 'Classifying…' : 'Classify →'}
      </button>
    </div>
  )
}

// ── Tab 1: Guided Form (replaces Proposal Form) ───────────────────────────────

const STEP_TITLES = [
  'Badge Identity',
  'Who Is This For',
  'Earning Criteria',
  'How Is It Verified',
  'Pathway',
  'Notifications',
]

const PATHWAY_OPTIONS = [
  'No — this badge stands alone',
  'Yes — it is one course in a series',
  'Yes — it is the final badge completing the whole series',
  'Not sure',
]

const PATHWAY_POSITION_OPTIONS = ['1st', '2nd', '3rd', '4th', 'Later']

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function GuidedForm({ onIngested }) {
  const [step, setStep] = useState(1)
  const [answers, setAnswers] = useState({
    badge_title: '',
    badge_description: '',
    area: '',
    area_other: '',
    ldi_audience: '',
    earning_criteria: '',
    verification: '',
    pass_score: '',
    pass_score_other: '',
    pathway: '',
    pathway_position: '',
    canvas_code: '',
    submitter_email: '',
    reviewer_email: '',
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  function set(field, val) {
    setAnswers(a => ({ ...a, [field]: val }))
    if (errors[field]) setErrors(e => ({ ...e, [field]: '' }))
  }

  function validateStep(s) {
    const e = {}
    if (s === 1) {
      if (answers.badge_title.trim().length < 5)
        e.badge_title = 'At least 5 characters required'
      if (answers.badge_description.trim().length < 50)
        e.badge_description = 'At least 50 characters required'
    }
    if (s === 2) {
      if (!answers.area) e.area = 'Please select an option'
      if (
        answers.area === 'Learning and Development / Continuing Education' &&
        !answers.ldi_audience
      )
        e.ldi_audience = 'Please select who will earn this badge'
    }
    if (s === 3) {
      if (answers.earning_criteria.trim().length < 30)
        e.earning_criteria = 'At least 30 characters required'
    }
    if (s === 4) {
      if (!answers.verification)
        e.verification = 'Please select how the earner is verified'
    }
    if (s === 5) {
      if (!answers.pathway) e.pathway = 'Please select an option'
      if (
        answers.pathway === 'Yes — it is one course in a series' &&
        !answers.pathway_position
      )
        e.pathway_position = 'Please select the position in the series'
    }
    if (s === 6) {
      if (!answers.submitter_email.trim()) e.submitter_email = 'Required'
      else if (!EMAIL_RE.test(answers.submitter_email))
        e.submitter_email = 'Valid email required'
      if (!answers.reviewer_email.trim()) e.reviewer_email = 'Required'
      else if (!EMAIL_RE.test(answers.reviewer_email))
        e.reviewer_email = 'Valid email required'
    }
    return e
  }

  function goNext() {
    const e = validateStep(step)
    if (Object.keys(e).length) { setErrors(e); return }
    setErrors({})
    setStep(s => s + 1)
  }

  function goBack() {
    setErrors({})
    setStep(s => s - 1)
  }

  async function handleSubmit() {
    const e = validateStep(6)
    if (Object.keys(e).length) { setErrors(e); return }
    setLoading(true)
    setApiError('')
    try {
      const fields = translateFormAnswers(answers)
      const bfs = await ingestBadge('form', fields)
      onIngested(bfs, 'form', {
        submitter_email: answers.submitter_email.trim(),
        reviewer_email: answers.reviewer_email.trim(),
      })
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const isLDI = answers.area === 'Learning and Development / Continuing Education'
  const totalSteps = 6

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm font-semibold text-njit-navy">
            Step {step} of {totalSteps}
          </span>
          <span className="text-sm text-gray-500">{STEP_TITLES[step - 1]}</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-njit-red transition-all duration-300 rounded-full"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>

      <ErrorBanner message={apiError} />

      {/* ── Step 1: Badge Identity ── */}
      {step === 1 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">What is this badge called?</p>

          <FieldGroup label="Badge Title *">
            <Input
              value={answers.badge_title}
              error={errors.badge_title}
              onChange={e => set('badge_title', e.target.value)}
              placeholder="e.g. AI Fundamentals"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.badge_title} />
              <span className={`text-xs ml-auto ${answers.badge_title.trim().length < 5 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.badge_title.trim().length} / 5 min
              </span>
            </div>
          </FieldGroup>

          <FieldGroup label="Badge Description *">
            <Textarea
              value={answers.badge_description}
              error={errors.badge_description}
              onChange={e => set('badge_description', e.target.value)}
              rows={5}
              placeholder="Describe what this badge represents and who it is for…"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.badge_description} />
              <span className={`text-xs ml-auto ${answers.badge_description.trim().length < 50 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.badge_description.trim().length} / 50 min
              </span>
            </div>
          </FieldGroup>
        </div>
      )}

      {/* ── Step 2: Who Is This For ── */}
      {step === 2 && (
        <div className="space-y-5">
          <p className="text-base font-semibold text-njit-navy">
            Which area of NJIT is this badge from?
          </p>

          <RadioGroup
            options={AREA_OPTIONS}
            value={answers.area}
            onChange={val => { set('area', val); set('ldi_audience', '') }}
            name="area"
            error={errors.area}
          />
          <FieldError message={errors.area} />

          {answers.area === 'Other' && (
            <div className="pl-2">
              <FieldGroup label="Please describe the issuing area:">
                <Input
                  value={answers.area_other}
                  onChange={e => set('area_other', e.target.value)}
                  placeholder="e.g. Center for Pre-College Programs"
                />
              </FieldGroup>
            </div>
          )}

          {isLDI && (
            <div className="mt-4 pl-2 border-l-2 border-njit-red space-y-3">
              <p className="text-sm font-semibold text-njit-navy">
                Who will earn this badge?
              </p>
              <RadioGroup
                options={LDI_AUDIENCE_OPTIONS}
                value={answers.ldi_audience}
                onChange={val => set('ldi_audience', val)}
                name="ldi_audience"
                error={errors.ldi_audience}
              />
              <FieldError message={errors.ldi_audience} />
            </div>
          )}
        </div>
      )}

      {/* ── Step 3: Earning Criteria ── */}
      {step === 3 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">
            What must someone do to earn this badge?
          </p>
          <FieldGroup
            helper='Describe the specific actions, activities, or requirements the earner must complete.'
          >
            <Textarea
              value={answers.earning_criteria}
              error={errors.earning_criteria}
              onChange={e => set('earning_criteria', e.target.value)}
              rows={7}
              placeholder="e.g. Attend the full workshop session and pass the final assessment with 80% or higher…"
            />
            <div className="flex items-center justify-between mt-1">
              <FieldError message={errors.earning_criteria} />
              <span className={`text-xs ml-auto ${answers.earning_criteria.trim().length < 30 ? 'text-gray-400' : 'text-green-600'}`}>
                {answers.earning_criteria.trim().length} / 30 min
              </span>
            </div>
          </FieldGroup>
        </div>
      )}

      {/* ── Step 4: How Is It Verified ── */}
      {step === 4 && (
        <div className="space-y-5">
          <div>
            <p className="text-base font-semibold text-njit-navy mb-3">
              How is the earner's work checked?
            </p>
            <RadioGroup
              options={VERIFICATION_OPTIONS}
              value={answers.verification}
              onChange={val => set('verification', val)}
              name="verification"
              error={errors.verification}
            />
            <FieldError message={errors.verification} />
          </div>

          <div>
            <p className="text-sm font-semibold text-gray-700 mb-3">
              Is there a minimum pass score required?
            </p>
            <RadioGroup
              options={PASS_SCORE_OPTIONS}
              value={answers.pass_score}
              onChange={val => { set('pass_score', val); set('pass_score_other', '') }}
              name="pass_score"
            />
            {answers.pass_score === 'Other' && (
              <div className="mt-2 pl-2">
                <Input
                  value={answers.pass_score_other}
                  onChange={e => set('pass_score_other', e.target.value)}
                  placeholder="e.g. 75%"
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Step 5: Pathway ── */}
      {step === 5 && (
        <div className="space-y-5">
          <div>
            <p className="text-base font-semibold text-njit-navy mb-3">
              Is this badge part of a learning series?
            </p>
            <RadioGroup
              options={PATHWAY_OPTIONS}
              value={answers.pathway}
              onChange={val => { set('pathway', val); set('pathway_position', '') }}
              name="pathway"
              error={errors.pathway}
            />
            <FieldError message={errors.pathway} />

            {answers.pathway === 'Yes — it is one course in a series' && (
              <div className="mt-3 pl-2 border-l-2 border-njit-red">
                <p className="text-sm font-semibold text-njit-navy mb-2">Which position?</p>
                <div className="flex flex-wrap gap-2">
                  {PATHWAY_POSITION_OPTIONS.map(pos => (
                    <button
                      key={pos}
                      type="button"
                      onClick={() => set('pathway_position', pos)}
                      className={`px-4 py-1.5 rounded-full text-sm border transition-colors
                        ${answers.pathway_position === pos
                          ? 'bg-njit-red text-white border-njit-red'
                          : 'border-gray-300 text-gray-700 hover:border-njit-red hover:text-njit-red'}`}
                    >
                      {pos}
                    </button>
                  ))}
                </div>
                <FieldError message={errors.pathway_position} />
              </div>
            )}
          </div>

          <FieldGroup
            label="Canvas course code (optional):"
            helper="Leave blank if you don't have this."
          >
            <Input
              value={answers.canvas_code}
              onChange={e => set('canvas_code', e.target.value)}
              placeholder="MCAI.002.03"
            />
          </FieldGroup>
        </div>
      )}

      {/* ── Step 6: Notifications ── */}
      {step === 6 && (
        <div className="space-y-4">
          <p className="text-base font-semibold text-njit-navy">
            Who should be notified about this classification?
          </p>

          <FieldGroup label="Your email address *">
            <Input
              type="email"
              value={answers.submitter_email}
              error={errors.submitter_email}
              onChange={e => set('submitter_email', e.target.value)}
              placeholder="you@njit.edu"
            />
            <FieldError message={errors.submitter_email} />
          </FieldGroup>

          <FieldGroup
            label="Reviewer email address *"
            helper="The person who will review and approve this classification."
          >
            <Input
              type="email"
              value={answers.reviewer_email}
              error={errors.reviewer_email}
              onChange={e => set('reviewer_email', e.target.value)}
              placeholder="reviewer@njit.edu"
            />
            <FieldError message={errors.reviewer_email} />
          </FieldGroup>
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex items-center gap-3 pt-2">
        {step > 1 && (
          <button
            type="button"
            onClick={goBack}
            className="px-5 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
          >
            ← Back
          </button>
        )}
        {step < totalSteps && (
          <button
            type="button"
            onClick={goNext}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark text-sm"
          >
            Next →
          </button>
        )}
        {step === totalSteps && (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50 text-sm"
          >
            {loading ? 'Submitting…' : 'Submit Badge →'}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Tab 2: JSON Paste ─────────────────────────────────────────────────────────

function JsonPasteTab({ onIngested }) {
  const [raw, setRaw] = useState('')
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  function handleParse() {
    setParseError('')
    setParsed(null)
    try {
      const obj = JSON.parse(raw)
      setParsed(obj)
    } catch {
      setParseError('Invalid JSON — please check your input.')
    }
  }

  async function handleSubmit() {
    if (!raw.trim()) { setParseError('Paste JSON before submitting.'); return }
    setLoading(true)
    setApiError('')
    try {
      // Always parse fresh from raw — never rely on stale `parsed` state.
      // This is the correct pattern: const parsed = JSON.parse(text); ingestBadge("obv3_json", parsed)
      let jsonObj
      try {
        jsonObj = JSON.parse(raw)
      } catch {
        setParseError('Invalid JSON — please check your input.')
        setLoading(false)
        return
      }
      const bfs = await ingestBadge('obv3_json', jsonObj)
      onIngested(bfs, 'json')
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <ErrorBanner message={apiError} />
      <FieldGroup label="Paste OBv3 JSON">
        <Textarea
          value={raw}
          onChange={e => { setRaw(e.target.value); setParsed(null); setParseError('') }}
          rows={12}
          placeholder={'{\n  "@context": "https://purl.imsglobal.org/spec/ob/v3p0/...",\n  "name": "Badge Name",\n  ...\n}'}
          error={!!parseError}
        />
      </FieldGroup>

      {parseError && <p className="text-red-600 text-sm">{parseError}</p>}

      {parsed && (
        <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
          <strong>Valid JSON detected.</strong>{' '}
          Fields found: {Object.keys(parsed).join(', ')}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleParse}
          className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
        >
          Parse JSON
        </button>
        <button
          onClick={handleSubmit}
          disabled={!raw.trim() || loading}
          className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
        >
          {loading ? 'Submitting…' : 'Submit & Extract →'}
        </button>
      </div>
    </div>
  )
}

// ── Tab 3: Free Text ──────────────────────────────────────────────────────────

function FreeTextTab({ onIngested }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  async function handleSubmit() {
    if (!text.trim()) return
    setLoading(true)
    setApiError('')
    try {
      const bfs = await ingestBadge('free_text', { text })
      onIngested(bfs, 'free_text')
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <ErrorBanner message={apiError} />
      <FieldGroup label="Describe the badge in plain language">
        <Textarea
          value={text}
          onChange={e => setText(e.target.value)}
          rows={12}
          placeholder="This badge is awarded to faculty who complete the AI for Education course series. Learners must pass the final assessment with 80% or higher…"
        />
      </FieldGroup>
      <button
        onClick={handleSubmit}
        disabled={!text.trim() || loading}
        className="bg-njit-red text-white px-6 py-2 rounded font-medium hover:bg-njit-red-dark disabled:opacity-50"
      >
        {loading ? 'Submitting…' : 'Submit & Extract →'}
      </button>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const TABS = ['Proposal Form', 'JSON Paste', 'Free Text']

export default function SubmitBadge() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState(0)
  const [bfs, setBfs] = useState(null)
  const [inputMode, setInputMode] = useState('form')
  const [followupValues, setFollowupValues] = useState({})
  const [submissionMeta, setSubmissionMeta] = useState({})
  const [classifying, setClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState('')

// Tanay's Changes
//  useEffect(() => {
//  const correctionBfs = localStorage.getItem("review_correction_bfs")
//  const correctionMeta = localStorage.getItem("review_correction_meta")

 // if (correctionBfs) {
 //   setBfs(JSON.parse(correctionBfs))
 //   setInputMode("form")
 //   setActiveTab(0)

 //   if (correctionMeta) {
 //     setSubmissionMeta(JSON.parse(correctionMeta))
 //   }
 // }
//}, [])
// Tanay's Changes

  function handleIngested(bfsData, mode, meta = {}) {
    // For free_text: NLP runs at /classify time, so assessment_evaluator is never
    // flagged as missing at /ingest time even when it is null. Add it here so
    // FreeTextFollowupPanel's condition missing_signals.includes('assessment_evaluator')
    // works correctly.
    if (mode === 'free_text' && bfsData.assessment_evaluator == null) {
      const ms = bfsData.missing_signals || []
      if (!ms.includes('assessment_evaluator')) {
        bfsData = { ...bfsData, missing_signals: [...ms, 'assessment_evaluator'] }
      }
    }
    setBfs(bfsData)
    setInputMode(mode)
    setFollowupValues({})
    setSubmissionMeta(meta)
    setClassifyError('')
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  // Accepts either a multi-field object or (field, val) for backward compat
  function handleFollowupChange(fieldsOrField, val) {
    if (typeof fieldsOrField === 'object' && fieldsOrField !== null) {
      setFollowupValues(v => ({ ...v, ...fieldsOrField }))
    } else {
      setFollowupValues(v => ({ ...v, [fieldsOrField]: val }))
    }
  }

  // Free-text path: receives a fully merged BFS from FreeTextFollowupPanel,
  // classifies immediately, navigates directly to the review page.
  async function handleFreeTextClassify(mergedBfs) {
    setClassifying(true)
    setClassifyError('')
    try {
// Tanay's Changes
      const previousBfs = JSON.parse(
        localStorage.getItem("review_correction_bfs") || "{}"
      )

      const enrichedBfs = {
        ...previousBfs,
        ...mergedBfs,
      }

      const result = await classifyBadge(enrichedBfs, submissionMeta)

      localStorage.removeItem("review_correction_bfs")
      localStorage.removeItem("review_correction_meta")
// Tanay's Changes
      const logId = result.governance.log_id
      navigate(`/review/${logId}`, { state: { result, bfs: enrichedBfs } }) // Tanay's Changes
    } catch (err) {
      setClassifyError(err.message)
    } finally {
      setClassifying(false)
    }
  }

  async function handleConfirmClassify() {
    setClassifying(true)
    setClassifyError('')
    //Tanay
    try {
    const enrichedBfs = { ...bfs, ...followupValues }
    const result = await classifyBadge(enrichedBfs, submissionMeta)

    const logId = result.governance.log_id

    if (submissionMeta.submitter_email || submissionMeta.reviewer_email) {
      navigate('/submit/confirmation', {
        state: {
          badgeTitle: result.badge_title || enrichedBfs.badge_title,
          submitterEmail: submissionMeta.submitter_email,
          reviewerEmail: submissionMeta.reviewer_email,
          logId,
        },
      })
    } else {
      navigate(`/review/${logId}`, { state: { result, bfs: enrichedBfs } })
    }
    //Tanay
    } catch (err) {
      setClassifyError(err.message)
    } finally {
      setClassifying(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-njit-navy">Submit Badge for Classification</h1>
        <p className="text-gray-600 text-sm mt-1">
          Choose an input method below. The system will extract signals and recommend a classification.
        </p>
      </div>

      {/* Tab headers */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-0">
          {TABS.map((tab, i) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(i); setBfs(null) }}
              className={`px-5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors
                ${activeTab === i
                  ? 'border-njit-red text-njit-red'
                  : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 0 && <GuidedForm onIngested={handleIngested} />}
        {activeTab === 1 && <JsonPasteTab onIngested={handleIngested} />}
        {activeTab === 2 && <FreeTextTab onIngested={handleIngested} />}
      </div>

      {/* Post-ingest panel — student follow-ups for free text, BFS confirm for others */}
      {bfs && (
        <>
          <hr className="border-gray-200" />
          <ErrorBanner message={classifyError} />
          {inputMode === 'free_text' ? (
            <FreeTextFollowupPanel
              bfs={bfs}
              onClassify={handleFreeTextClassify}
              loading={classifying}
            />
          ) : (
            <BfsConfirmPanel
              bfs={bfs}
              inputMode={inputMode}
              onConfirm={handleConfirmClassify}
              onFollowupChange={handleFollowupChange}
              loading={classifying}
            />
          )}
        </>
      )}
    </div>
  )
}
