"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

BadgeFactSheet — the single normalized internal representation of every badge.

The rule engine ONLY reads this object — never raw input.
Filled in across 8 stages as described in docs/badge-fact-sheet-schema.md.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_uuid() -> str:
    return str(uuid4())


class BadgeFactSheet(BaseModel):

    # -------------------------------------------------------------------------
    # Section 1 — Source and Ingestion
    # -------------------------------------------------------------------------

    badge_id: str = Field(default_factory=_new_uuid)
    # "obv2_json" | "obv3_json" | "form" | "free_text"
    structured_source_type: str = "free_text"
    obv_version: Optional[int] = None          # 2 or 3
    raw_input_text: str = ""                   # Original input preserved verbatim
    obv_fields_present: List[str] = Field(default_factory=list)
    criteria_id_url: Optional[str] = None      # criteria.id URL — used for issuer resolution
    ingested_at: str = Field(default_factory=_now_iso)

    # -------------------------------------------------------------------------
    # Section 2 — Core Identity
    # -------------------------------------------------------------------------

    badge_title: str = ""
    badge_description: str = ""
    # "LDI" | "OSIL" | "Makerspace" | "NCE" | "OGI"
    issuer: Optional[str] = None
    issuer_url: Optional[str] = None           # Raw issuer URL — OBv2 only
    governing_office: Optional[str] = None     # Derived from issuer
    created_on: Optional[str] = None
    # "Achievement" | "Competency" | "Certificate Of Completion" | "Micro Credential"
    achievement_type: Optional[str] = None
    external_partner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # -------------------------------------------------------------------------
    # Section 3 — Audience and Context
    # -------------------------------------------------------------------------

    intended_audience: Optional[str] = None
    # "external_professional" | "njit_student" | "njit_employee" | "faculty"
    audience_type: Optional[str] = None
    institutional_context: Optional[str] = None
    audience_restriction: Optional[str] = None
    is_credit_bearing: bool = False
    pdh_credits: Optional[str] = None
    # "PDH" | "CEU" | "academic" | None
    credit_type: Optional[str] = None

    # -------------------------------------------------------------------------
    # Section 4 — Earning Criteria
    # -------------------------------------------------------------------------

    earning_criteria_text: str = ""
    # "yes" | "no" | "unknown"
    assessment_required: str = "unknown"
    # "attendance" | "module_completion" | "final_assessment" | "knowledge_checks" |
    # "pre_post_assessment" | "project_presentation" | "practical" | "quiz" |
    # "portfolio" | "rubric"
    assessment_type: Optional[str] = None
    assessment_type_detail: Optional[str] = None
    # "expert_scored" | "auto_assessed" | "peer_evaluated" | "self_reported" | "observed"
    # CRITICAL: This is the primary Skill vs Achievement signal
    assessment_evaluator: Optional[str] = None
    assessment_pass_threshold: Optional[str] = None
    # "online" | "in_person" | "blended"
    assessment_modality: Optional[str] = None
    # "AND" | "OR" | "mixed"
    criteria_logic: Optional[str] = None
    # "recognition" | "compliance" | "prerequisite_gate"
    badge_purpose: str = "recognition"
    downstream_workflow: Optional[str] = None
    mandatory_for: Optional[str] = None
    prerequisite_badges: List[str] = Field(default_factory=list)

    # -------------------------------------------------------------------------
    # Section 5 — Evidence
    # -------------------------------------------------------------------------

    # "yes" | "no" | "unknown"
    evidence_required: str = "unknown"
    # "platform_tracked" | "scored_assessment" | "project_output" | "portfolio" |
    # "self_reported" | "observed" | "expert_rubric" | "attendance_record" | "none"
    evidence_type: Optional[str] = None
    evidence_description: Optional[str] = None
    # CRITICAL: Confirms Skill vs Achievement distinction
    expert_evaluation_required: bool = False

    # -------------------------------------------------------------------------
    # Section 6 — Pathway and Positioning
    # -------------------------------------------------------------------------

    canvas_course_code: Optional[str] = None
    canvas_pathway_code: Optional[str] = None
    canvas_sequence_number: Optional[int] = None
    canvas_pathway_length: Optional[int] = None
    # True if sequence==0 OR achievementType=="Micro Credential"
    is_capstone: bool = False
    pathway_name: Optional[str] = None
    # "1st of 3" | "End of Pathway" | "Standalone" | etc.
    pathway_position: Optional[str] = None
    # "flat_sequential" | "tiered_milestone" | "parallel" | "in_person_cohort"
    pathway_model: Optional[str] = None
    has_prerequisite_badges: bool = False
    related_badges: List[str] = Field(default_factory=list)
    progression_implied: bool = False

    # -------------------------------------------------------------------------
    # Section 7 — Skill and Competency Signals
    # -------------------------------------------------------------------------

    # "remembering" | "understanding" | "applying" | "analyzing" | "evaluating" | "creating"
    bloom_level: Optional[str] = None
    # "High" | "Medium" | "Low"
    bloom_confidence: Optional[str] = None
    bloom_verbs_detected: List[str] = Field(default_factory=list)
    ksa_dimensions: List[str] = Field(default_factory=list)
    real_world_context: bool = False
    multi_context_evidence: bool = False
    leadership_evidence: bool = False

    # -------------------------------------------------------------------------
    # Section 8 — Alignments
    # -------------------------------------------------------------------------

    # [{name, code, framework, description}]
    skill_alignments: List[Dict[str, Any]] = Field(default_factory=list)
    alignment_count: int = 0
    alignment_frameworks: List[str] = Field(default_factory=list)
    # True if any alignment has empty targetFramework
    institutional_framework_reference: bool = False
    njit_core_competency: Optional[str] = None

    # -------------------------------------------------------------------------
    # Section 9 — NLP Extracted Signals
    # -------------------------------------------------------------------------

    audience_signal: Optional[str] = None
    context_signal: Optional[str] = None
    # "Low" | "Medium" | "High"
    rigor_signal: Optional[str] = None
    evidence_signal: Optional[str] = None
    self_declared_level: Optional[str] = None
    level_phrase_matched: Optional[str] = None
    # "keyword_rule" | "regex_pattern" | "spacy_verb" | "llm_extraction" | "structured_field"
    level_signal_source: Optional[str] = None
    audience_signal_source: Optional[str] = None
    # True if critical signals still missing after all NLP passes
    needs_followup_questions: bool = False
    missing_signals: List[str] = Field(default_factory=list)
    confidence_notes: Optional[str] = None

    # -------------------------------------------------------------------------
    # Section 10 — Classification Output
    # Filled by rule engine — not by ingestion or NLP
    # -------------------------------------------------------------------------

    category_result: Optional[str] = None
    type_result: Optional[str] = None
    level_result: Optional[str] = None
    # "souvenir" | "achievement" | "skill" | "competency"
    level_branch_used: Optional[str] = None
    # "High" | "Medium" | "Low"
    classification_confidence: str = "Low"
    triggered_rules: List[str] = Field(default_factory=list)
    explanation_text: str = ""
    archetype: Optional[str] = None

    # -------------------------------------------------------------------------
    # Section 11 — Human Review
    # Filled by reviewer via POST /review — never by the engine
    # -------------------------------------------------------------------------

    # "pending" | "accepted" | "overridden"
    reviewer_status: str = "pending"
    reviewer_id: Optional[str] = None
    reviewer_override_reason: Optional[str] = None
    override_category: Optional[str] = None
    override_type: Optional[str] = None
    override_level: Optional[str] = None
    final_locked_decision: Optional[str] = None
    reviewed_at: Optional[str] = None

    model_config = {"extra": "forbid"}
