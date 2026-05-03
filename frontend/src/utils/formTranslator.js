/**
 * NJIT AI-Assisted Digital Badge Classification Tool
 * Author: R
 * Institution: New Jersey Institute of Technology
 * Capstone Project — Spring 2026
 *
 * formTranslator.js
 * Translates plain-language guided form answers → BadgeFactSheet fields
 * for POST /ingest with input_type="form".
 * Also exports option arrays and helper translators used by the follow-up
 * panels in the JSON and free-text tabs (Parts 3 & 4).
 */

// ── Option arrays (shared between GuidedForm steps and follow-up panels) ────

export const AREA_OPTIONS = [
  'Learning and Development / Continuing Education',
  'Student Programs / Leadership Development',
  'Makerspace / Technical Skills Training',
  'Academic Department or College Program',
  'Administrative Office / Student Services',
  'Other',
]

export const LDI_AUDIENCE_OPTIONS = [
  'Working professionals or adult learners (outside NJIT)',
  'NJIT faculty or staff',
  'NJIT students',
]

// Used when missing_signals contains "audience_type" (free-text follow-up)
export const AUDIENCE_OPTIONS = [
  'Working professionals or adult learners (outside NJIT)',
  'NJIT faculty or staff',
  'NJIT students',
]

export const VERIFICATION_OPTIONS = [
  'The platform tracks their progress automatically',
  'They take a quiz or test that is automatically graded',
  'A person (instructor, supervisor, expert) reviews their work',
  'They show up and participate — no grading needed',
  'They submit a project or portfolio evaluated by an expert',
  'They demonstrate a skill observed in person by an expert',
  'They document real-world experience (internship, competition, project)',
  'Not sure',
]

export const PASS_SCORE_OPTIONS = [
  'No pass score required',
  '80% or higher',
  '90% or higher',
  'Other',
]

// ── Internal mapping tables ──────────────────────────────────────────────────

const AREA_TO_ISSUER = {
  'Learning and Development / Continuing Education': 'LDI',
  'Student Programs / Leadership Development': 'OSIL',
  'Makerspace / Technical Skills Training': 'Makerspace',
  'Academic Department or College Program': 'NCE',
  'Administrative Office / Student Services': 'OGI',
}

const AREA_TO_AUDIENCE = {
  'Student Programs / Leadership Development': 'njit_student',
  'Makerspace / Technical Skills Training': 'njit_student',
  'Academic Department or College Program': 'njit_student',
}

const LDI_AUDIENCE_MAP = {
  'Working professionals or adult learners (outside NJIT)': 'external_professional',
  'NJIT faculty or staff': 'njit_employee',
  'NJIT students': 'njit_student',
}

const VERIFICATION_MAP = {
  'The platform tracks their progress automatically': {
    assessment_evaluator: 'auto_assessed',
    assessment_type: 'module_completion',
    assessment_required: 'yes',
    expert_evaluation_required: false,
    evidence_type: 'platform_tracked',
  },
  'They take a quiz or test that is automatically graded': {
    assessment_evaluator: 'auto_assessed',
    assessment_type: 'final_assessment',
    assessment_required: 'yes',
    expert_evaluation_required: false,
    evidence_type: 'scored_assessment',
  },
  'A person (instructor, supervisor, expert) reviews their work': {
    assessment_evaluator: 'expert_scored',
    assessment_required: 'yes',
    expert_evaluation_required: true,
    evidence_type: 'expert_rubric',
  },
  'They show up and participate — no grading needed': {
    assessment_type: 'attendance',
    assessment_required: 'no',
    expert_evaluation_required: false,
    evidence_type: 'attendance_record',
  },
  'They submit a project or portfolio evaluated by an expert': {
    assessment_evaluator: 'expert_scored',
    assessment_type: 'portfolio',
    assessment_required: 'yes',
    expert_evaluation_required: true,
    evidence_type: 'project_output',
  },
  'They demonstrate a skill observed in person by an expert': {
    assessment_evaluator: 'expert_scored',
    assessment_type: 'practical',
    assessment_required: 'yes',
    expert_evaluation_required: true,
    evidence_type: 'observed',
  },
  'They document real-world experience (internship, competition, project)': {
    achievement_type: 'Competency',
    assessment_evaluator: 'expert_scored',
    assessment_required: 'yes',
    expert_evaluation_required: true,
    evidence_type: 'self_reported',
    real_world_context: true,
  },
  'Not sure': {},
}

// Displayed pathway label → internal key used in the if/else chain below
const PATHWAY_LABEL_TO_KEY = {
  'No — this badge stands alone': 'standalone',
  'Yes — it is one course in a series': 'series',
  'Yes — it is the final badge completing the whole series': 'final',
  'Not sure': 'not_sure',
}

const PATHWAY_POSITION_MAP = {
  '1st': { canvas_sequence_number: 1, pathway_position: '1st' },
  '2nd': { canvas_sequence_number: 2 },
  '3rd': { canvas_sequence_number: 3 },
  '4th': { canvas_sequence_number: 4 },
  'Later': {},
}

// ── Main translator ──────────────────────────────────────────────────────────

/**
 * Translate all guided form answers into a BFS-compatible payload for /ingest.
 *
 * @param {object} answers
 *   badge_title, badge_description,
 *   area, area_other, ldi_audience,
 *   earning_criteria,
 *   verification, pass_score, pass_score_other,
 *   pathway, pathway_position, canvas_code,
 *   submitter_email, reviewer_email  (stored for future use, not sent)
 * @returns {object} BFS form payload
 */
export function translateFormAnswers(answers) {
  const fields = {}

  // Step 1 — Badge identity
  fields.badge_title = answers.badge_title.trim()
  fields.badge_description = answers.badge_description.trim()

  // Step 2 — Issuer + audience_type
  const area = answers.area
  if (area === 'Other') {
    if (answers.area_other?.trim()) fields.issuer = answers.area_other.trim()
    // issuer stays unresolved → backend flags it
  } else if (AREA_TO_ISSUER[area]) {
    fields.issuer = AREA_TO_ISSUER[area]
    if (AREA_TO_AUDIENCE[area]) {
      fields.audience_type = AREA_TO_AUDIENCE[area]
    }
  }

  // Step 2b — LDI audience sub-question (overrides any AREA_TO_AUDIENCE entry)
  if (area === 'Learning and Development / Continuing Education' && answers.ldi_audience) {
    const mapped = LDI_AUDIENCE_MAP[answers.ldi_audience]
    if (mapped) fields.audience_type = mapped
  }

  // Step 3 — Earning criteria
  fields.earning_criteria_text = answers.earning_criteria.trim()

  // Step 4 — Verification method
  if (answers.verification && VERIFICATION_MAP[answers.verification]) {
    Object.assign(fields, VERIFICATION_MAP[answers.verification])
  }

  // Step 4 — Pass score
  const score = answers.pass_score
  if (score === '80% or higher') {
    fields.assessment_pass_threshold = '80%'
  } else if (score === '90% or higher') {
    fields.assessment_pass_threshold = '90%'
  } else if (score === 'Other' && answers.pass_score_other?.trim()) {
    fields.assessment_pass_threshold = answers.pass_score_other.trim()
  }

  // Step 5 — Pathway (answers.pathway stores the display label; map to internal key)
  const pathwayKey = PATHWAY_LABEL_TO_KEY[answers.pathway] || answers.pathway
  if (pathwayKey === 'standalone') {
    fields.pathway_position = 'Standalone'
  } else if (pathwayKey === 'final') {
    fields.is_capstone = true
  } else if (pathwayKey === 'series' && answers.pathway_position) {
    const pos = PATHWAY_POSITION_MAP[answers.pathway_position]
    if (pos) Object.assign(fields, pos)
  }

  if (answers.canvas_code?.trim()) {
    fields.canvas_course_code = answers.canvas_code.trim()
  }

  return fields
}

// ── Follow-up helpers (used by JSON and free-text follow-up panels) ──────────

/**
 * Translate a plain-language area answer to BFS issuer + audience_type fields.
 */
export function translateAreaAnswer(area) {
  if (!area || area === 'Other') return {}
  const result = {}
  if (AREA_TO_ISSUER[area]) result.issuer = AREA_TO_ISSUER[area]
  if (AREA_TO_AUDIENCE[area]) result.audience_type = AREA_TO_AUDIENCE[area]
  return result
}

/**
 * Translate a plain-language verification answer to BFS assessment fields.
 */
export function translateVerificationAnswer(verification) {
  return { ...VERIFICATION_MAP[verification] } || {}
}

/**
 * Translate a plain-language audience answer to audience_type.
 */
export function translateAudienceAnswer(answer) {
  const mapped = LDI_AUDIENCE_MAP[answer]
  return mapped ? { audience_type: mapped } : {}
}
