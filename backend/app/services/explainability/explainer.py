"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Explainability Layer — generate_explanation(bfs, result) -> str

Every classification produces a plain-English explanation covering 8 mandatory
elements (docs/taxonomy-rules.md):

  1. CATEGORY — issuer, how detected, S1 rule IDs
  2. TYPE     — reason, assessment type/evaluator, S2 rule IDs
  3. LEVEL    — branch, canvas position OR phrase OR Bloom, S3 rule IDs
  4. SIGNALS  — every non-None signal with its value and source
  5. CONFIDENCE — overall level and why
  6. MISSING SIGNALS — only if missing_signals is not empty
  7. CONFLICT — only if a level conflict was detected
  8. HUMAN REVIEW — always present; states either recommendation or no-action

Format rules:
  - Plain text paragraphs separated by one blank line
  - No JSON, no markdown headers, no bullet points
  - Must be readable by a non-technical reviewer
  - Low confidence → more detail, not less
  - Always generated regardless of confidence level
"""

from app.models.badge_fact_sheet import BadgeFactSheet
from app.models.classification_result import ClassificationResult


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_explanation(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    """
    Build and return the complete plain-English explanation for a classification.

    The explanation covers 8 mandatory elements (docs/taxonomy-rules.md):
      1. CATEGORY   — issuer name, how it was detected, Stage 1 rule IDs fired;
                      OGI open-question Q001 note appended when issuer == "OGI"
      2. TYPE       — rule-specific reason from _S2_REASONS, assessment type and
                      evaluator detected, Stage 2 rule IDs fired
      3. LEVEL      — branch used, canvas position or NLP phrase or Bloom verbs,
                      prerequisite/competency evidence notes, Stage 3 rule IDs fired
      4. SIGNALS    — every non-None BFS signal listed with value and source label;
                      skips boolean False and empty list fields to reduce noise
      5. CONFIDENCE — overall level and every reason that applies (missing signals,
                      OR criteria, regex signal source, title/description conflict)
      6. MISSING SIGNALS (conditional) — listed only when bfs.missing_signals
                      is non-empty; instructs reviewer to provide them
      7. CONFLICT   (conditional) — rendered only when "conflict" appears in
                      bfs.confidence_notes
      8. HUMAN REVIEW — always present; states recommendation or no-action;
                      Low/Medium confidence, OR criteria, unresolved type/level,
                      and OGI issuer all trigger a "Recommended" verdict

    Format: plain-text paragraphs separated by one blank line.
    No markdown headers, no bullet points, no JSON — must be readable by a
    non-technical reviewer. Low confidence → more detail, not less.

    Called by the engine after all three stages run and the ClassificationResult
    has been assembled (so result.rules_triggered is fully populated).
    """
    paragraphs: list[str] = []

    paragraphs.append(_element1_category(bfs, result))
    paragraphs.append(_element2_type(bfs, result))
    paragraphs.append(_element3_level(bfs, result))
    paragraphs.append(_element4_signals(bfs))
    paragraphs.append(_element5_confidence(bfs, result))

    missing_para = _element6_missing_signals(bfs)
    if missing_para:
        paragraphs.append(missing_para)

    conflict_para = _element7_conflict(bfs)
    if conflict_para:
        paragraphs.append(conflict_para)

    paragraphs.append(_element8_review(bfs, result))

    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Element 1 — CATEGORY
# ---------------------------------------------------------------------------


def _element1_category(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    category = result.classification.category or "Unknown (open question — see MISSING SIGNALS)"
    s1_rules = [r for r in result.rules_triggered if r.startswith("S1") or r.startswith("IR")]

    if bfs.issuer:
        issuer_name = bfs.issuer
        detection_source = _issuer_detection_source(bfs)
        issuer_clause = f"issuer is {issuer_name} (detected from {detection_source})"
    else:
        issuer_clause = "issuer could not be determined from any available field"

    governing = bfs.governing_office
    governing_clause = (
        f" The governing office for this issuer is {governing}."
        if governing
        else ""
    )

    # Special handling for OGI open question Q001
    ogi_note = ""
    if bfs.issuer == "OGI":
        ogi_note = (
            " NOTE: OGI compliance and gate badges do not yet have an officially assigned "
            "Stage 1 category in the NJIT taxonomy. This is open question Q001 — "
            "supervisor confirmation required before accepting this classification."
        )

    rule_str = ", ".join(s1_rules) if s1_rules else "none"

    return (
        f"CATEGORY: Classified as '{category}' because the {issuer_clause}."
        f"{governing_clause}"
        f"{ogi_note} "
        f"Rule fired: {rule_str}."
    )


# ---------------------------------------------------------------------------
# Element 2 — TYPE
# ---------------------------------------------------------------------------

# Human-readable reasons keyed by the S2 rule that fired
_S2_REASONS = {
    "S2R01": (
        "the achievementType field is explicitly set to 'Micro Credential', "
        "which maps to Achievement (the level will be Terminal in Stage 3)"
    ),
    "S2R02": (
        "the achievementType field is explicitly set to 'Competency', "
        "which maps directly to the Competency type"
    ),
    "S2R03": (
        "the achievementType field is 'Certificate Of Completion', "
        "which maps to Achievement (entry-level)"
    ),
    "S2R04": (
        "the badge serves a compliance or gate purpose — earning criteria "
        "contain a mandatory-to-apply or required-to-apply phrase, "
        "or badge_purpose is set to 'compliance'"
    ),
    "S2R05": (
        "no assessment is required — earning criteria indicate attendance "
        "or participation only, with no scored or evaluated component"
    ),
    "S2R06": (
        "expert evaluation is required — the assessment must be scored or "
        "reviewed by a human expert, which distinguishes Skill from Achievement"
    ),
    "S2R07": (
        "an assessment is required but the evaluator type could not be "
        "determined — Skill is possible if an expert scores the work, "
        "but Achievement is the safer default pending confirmation"
    ),
    "S2R08": (
        "KSA dimensions (Knowledge, Skills, Abilities) were detected, or "
        "real-world context was present with OR-based criteria logic, "
        "indicating integrated competency demonstration"
    ),
    "S2R09": (
        "a canvas course code is present or the assessment type is a "
        "structured module-completion style (module_completion, "
        "final_assessment, or knowledge_checks), which is characteristic "
        "of Achievement badges"
    ),
    "S2R10": (
        "issuer is OSIL and the assessment uses a pre- and post-assessment "
        "format, which is an OSIL-specific Achievement pattern"
    ),
    "S2R11": (
        "no type rule could be matched — the earning criteria do not contain "
        "enough signal to determine type programmatically"
    ),
}


def _element2_type(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    badge_type = result.classification.type or "Unknown"
    s2_rules = [r for r in result.rules_triggered if r.startswith("S2")]

    reason = "no matching rule fired"
    if s2_rules:
        # Use the first S2 rule's reason
        reason = _S2_REASONS.get(s2_rules[0], f"rule {s2_rules[0]} matched")

    assessment_str = bfs.assessment_type or "not detected"
    evaluator_str = bfs.assessment_evaluator or "unknown"

    rule_str = ", ".join(s2_rules) if s2_rules else "none"

    return (
        f"TYPE: Classified as '{badge_type}' because {reason}. "
        f"Assessment type detected: {assessment_str}. "
        f"Evaluator: {evaluator_str}. "
        f"Rule fired: {rule_str}."
    )


# ---------------------------------------------------------------------------
# Element 3 — LEVEL
# ---------------------------------------------------------------------------


def _element3_level(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    level = result.classification.level or "Unknown"
    branch = result.classification.level_branch_used or "unknown"
    s3_rules = [r for r in result.rules_triggered if r.startswith("S3")]

    detail_parts: list[str] = []

    # Canvas code position
    if bfs.canvas_sequence_number is not None:
        pathway = bfs.pathway_name or bfs.canvas_pathway_code or "the pathway"
        detail_parts.append(
            f"Canvas code {bfs.canvas_course_code} places this badge at position "
            f"{bfs.canvas_sequence_number} in the {pathway} pathway."
        )

    # Capstone flag
    if bfs.is_capstone and bfs.canvas_sequence_number is None:
        detail_parts.append(
            "The badge is flagged as a capstone (is_capstone is True)."
        )

    # NLP phrase match
    if bfs.level_phrase_matched:
        source_label = _source_label(bfs.level_signal_source)
        detail_parts.append(
            f"Phrase detected: '{bfs.level_phrase_matched}' "
            f"(source: {source_label})."
        )

    # Bloom level
    if bfs.bloom_level:
        verbs = ", ".join(bfs.bloom_verbs_detected) if bfs.bloom_verbs_detected else "detected verbs"
        detail_parts.append(
            f"Bloom level detected: {bfs.bloom_level} from verbs: {verbs}."
        )

    # Prerequisite badges
    if bfs.has_prerequisite_badges and not detail_parts:
        detail_parts.append(
            "The badge requires prior badges as prerequisites, placing it above Foundational."
        )

    # Competency-specific signals
    if branch == "competency":
        if bfs.leadership_evidence:
            detail_parts.append("Leadership or mentoring evidence was detected.")
        if bfs.multi_context_evidence:
            detail_parts.append("Evidence spanning multiple contexts or domains was detected.")
        if bfs.real_world_context:
            detail_parts.append("Real-world (non-simulated) context was confirmed.")

    detail_str = " ".join(detail_parts) if detail_parts else "No specific level phrase or signal was detected."
    rule_str = ", ".join(s3_rules) if s3_rules else "none"

    return (
        f"LEVEL: Classified as '{level}' using the {branch} branch. "
        f"{detail_str} "
        f"Rule fired: {rule_str}."
    )


# ---------------------------------------------------------------------------
# Element 4 — SIGNALS USED
# ---------------------------------------------------------------------------

# Ordered list of BFS fields to report as signals, with display labels
_SIGNAL_FIELDS: list[tuple[str, str]] = [
    ("issuer",                   "issuer"),
    ("governing_office",         "governing_office"),
    ("audience_type",            "audience_type"),
    ("pdh_credits",              "pdh_credits"),
    ("achievement_type",         "achievement_type"),
    ("badge_purpose",            "badge_purpose"),
    ("assessment_required",      "assessment_required"),
    ("assessment_type",          "assessment_type"),
    ("assessment_evaluator",     "assessment_evaluator"),
    ("assessment_pass_threshold","assessment_pass_threshold"),
    ("expert_evaluation_required","expert_evaluation_required"),
    ("canvas_course_code",       "canvas_course_code"),
    ("canvas_sequence_number",   "canvas_sequence_number"),
    ("canvas_pathway_length",    "canvas_pathway_length"),
    ("is_capstone",              "is_capstone"),
    ("has_prerequisite_badges",  "has_prerequisite_badges"),
    ("ksa_dimensions",           "ksa_dimensions"),
    ("real_world_context",       "real_world_context"),
    ("multi_context_evidence",   "multi_context_evidence"),
    ("leadership_evidence",      "leadership_evidence"),
    ("self_declared_level",      "self_declared_level"),
    ("level_phrase_matched",     "level_phrase_matched"),
    ("bloom_level",              "bloom_level"),
    ("bloom_verbs_detected",     "bloom_verbs_detected"),
    ("criteria_logic",           "criteria_logic"),
    ("downstream_workflow",      "downstream_workflow"),
]

# Which BFS field determines the signal's source for display
_SIGNAL_SOURCE_MAP: dict[str, str] = {
    "issuer": "criteria_url_or_field",
    "audience_type": "audience_signal_source",
    "self_declared_level": "level_signal_source",
    "level_phrase_matched": "level_signal_source",
    "bloom_level": "spacy_verb",
    "bloom_verbs_detected": "spacy_verb",
}

# Fields that are always present and only worth reporting if meaningfully set
_SKIP_IF_FALSY = {
    "is_capstone", "has_prerequisite_badges", "expert_evaluation_required",
    "real_world_context", "multi_context_evidence", "leadership_evidence",
}
_SKIP_IF_EMPTY_LIST = {"ksa_dimensions", "bloom_verbs_detected"}


def _element4_signals(bfs: BadgeFactSheet) -> str:
    lines: list[str] = ["SIGNALS USED:"]

    bfs_dict = bfs.model_dump()

    for field_name, display_name in _SIGNAL_FIELDS:
        value = bfs_dict.get(field_name)

        # Skip None / empty
        if value is None:
            continue
        if field_name in _SKIP_IF_FALSY and not value:
            continue
        if field_name in _SKIP_IF_EMPTY_LIST and not value:
            continue

        # Format value
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value) if value else "(empty)"
        elif isinstance(value, bool):
            value_str = str(value)
        else:
            value_str = str(value)

        # Determine source label
        source = _signal_source_for_field(field_name, bfs)
        source_str = f" ({source})" if source else ""

        # Extra detail for phrase match
        extra = ""
        if field_name == "level_phrase_matched" and bfs.level_phrase_matched:
            extra = f" — phrase: {bfs.level_phrase_matched}"
        elif field_name == "self_declared_level" and bfs.level_phrase_matched:
            extra = f" — phrase: {bfs.level_phrase_matched}"

        lines.append(f"  {display_name}={value_str}{source_str}{extra}")

    if len(lines) == 1:
        lines.append("  (no signals detected — classification based on defaults only)")

    return "\n".join(lines)


def _signal_source_for_field(field_name: str, bfs: BadgeFactSheet) -> str:
    """Return a human-readable source label for a given BFS field."""
    if field_name == "issuer":
        if bfs.criteria_id_url:
            return "criteria URL domain"
        return "structured field"
    if field_name == "audience_type":
        return _source_label(bfs.audience_signal_source or "structured_field")
    if field_name in ("self_declared_level", "level_phrase_matched"):
        return _source_label(bfs.level_signal_source)
    if field_name in ("bloom_level", "bloom_verbs_detected"):
        return "spaCy verb analysis"
    if field_name in (
        "achievement_type", "assessment_required", "assessment_evaluator",
        "assessment_pass_threshold", "expert_evaluation_required",
        "canvas_course_code", "canvas_sequence_number", "canvas_pathway_length",
        "is_capstone", "has_prerequisite_badges", "ksa_dimensions",
        "real_world_context", "multi_context_evidence", "leadership_evidence",
        "governing_office", "pdh_credits",
    ):
        return "structured field"
    if field_name in ("assessment_type", "badge_purpose", "downstream_workflow", "criteria_logic"):
        return "keyword rule"
    return ""


# ---------------------------------------------------------------------------
# Element 5 — CONFIDENCE
# ---------------------------------------------------------------------------


def _element5_confidence(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    confidence = result.classification.confidence

    reasons: list[str] = []

    if bfs.needs_followup_questions:
        reasons.append("one or more critical signals are missing (follow-up questions required)")

    if bfs.criteria_logic == "OR":
        reasons.append(
            "the earning criteria use OR logic — the system cannot verify which "
            "qualifying path was actually completed"
        )

    if bfs.level_signal_source in ("regex_pattern", "llm_extraction"):
        reasons.append(
            f"the level signal came from a {_source_label(bfs.level_signal_source)} "
            f"rather than an exact phrase match"
        )

    if bfs.confidence_notes and "conflict" in bfs.confidence_notes.lower():
        reasons.append("a level conflict was detected between the badge title and description")

    if not reasons:
        if confidence == "High":
            reasons.append(
                "all three stages resolved with High confidence using unambiguous signals"
            )
        else:
            reasons.append("at least one stage resolved at a lower confidence level")

    reason_str = "; ".join(reasons)
    return f"CONFIDENCE: {confidence}. Reason: {reason_str}."


# ---------------------------------------------------------------------------
# Element 6 — MISSING SIGNALS
# ---------------------------------------------------------------------------


def _element6_missing_signals(bfs: BadgeFactSheet) -> str:
    if not bfs.missing_signals:
        return ""

    missing_list = ", ".join(bfs.missing_signals)
    return (
        f"MISSING SIGNALS: {missing_list}. "
        f"These fields could not be extracted and may affect accuracy. "
        f"Use the follow-up question interface or override form to provide them."
    )


# ---------------------------------------------------------------------------
# Element 7 — CONFLICT
# ---------------------------------------------------------------------------


def _element7_conflict(bfs: BadgeFactSheet) -> str:
    if not bfs.confidence_notes:
        return ""
    if "conflict" not in bfs.confidence_notes.lower():
        return ""

    return f"CONFLICT DETECTED: {bfs.confidence_notes}"


# ---------------------------------------------------------------------------
# Element 8 — HUMAN REVIEW
# ---------------------------------------------------------------------------


def _element8_review(bfs: BadgeFactSheet, result: ClassificationResult) -> str:
    review_reasons: list[str] = []

    if result.classification.confidence in ("Low", "Medium"):
        review_reasons.append(
            f"classification confidence is {result.classification.confidence}"
        )

    if bfs.criteria_logic == "OR":
        review_reasons.append(
            "OR-based criteria cannot be programmatically verified"
        )

    if bfs.needs_followup_questions:
        review_reasons.append("follow-up questions are needed to resolve missing signals")

    if bfs.issuer == "OGI":
        review_reasons.append(
            "OGI badges have no official Stage 1 category in the taxonomy "
            "(open question Q001 — confirm with supervisor)"
        )

    if result.classification.type is None:
        review_reasons.append("badge type could not be determined")

    if result.classification.level is None:
        review_reasons.append("badge level could not be determined")

    if review_reasons:
        reason_str = "; ".join(review_reasons)
        return f"HUMAN REVIEW: Recommended — {reason_str}."
    else:
        return (
            "HUMAN REVIEW: Not required — classification confidence is High "
            "with no unresolved flags."
        )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _issuer_detection_source(bfs: BadgeFactSheet) -> str:
    if bfs.criteria_id_url:
        return "criteria URL domain"
    if bfs.issuer_url:
        return "platform context (issuer URL)"
    return "form input"


def _source_label(source: str | None) -> str:
    labels = {
        "structured_field": "structured field",
        "criteria_url": "criteria URL domain",
        "keyword_rule": "keyword phrase match",
        "regex_pattern": "regex pattern match",
        "spacy_verb": "spaCy verb analysis",
        "llm_extraction": "LLM extraction",
    }
    return labels.get(source or "", source or "unknown source")
