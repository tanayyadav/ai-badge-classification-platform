"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Classification engine — orchestrates Stage 1 → Stage 2 → Stage 3.

Entry point: run_classification(bfs) → ClassificationResult

After running all three stages the engine:
  1. Writes results back to the BFS (Section 10 fields)
  2. Calculates overall confidence (docs/taxonomy-rules.md)
  3. Builds and returns a ClassificationResult

Governance log creation is handled by the calling route, not here,
so the engine remains free of database dependencies.
"""

import re
from datetime import datetime, timezone
from uuid import uuid4

from app.models.badge_fact_sheet import BadgeFactSheet
from app.models.classification_result import (
    ClassificationResult,
    ClassificationSummary,
    GovernanceSummary,
    SignalEntry,
)
from app.services.classification.stage1 import classify_stage1
from app.services.classification.stage2 import classify_stage2
from app.services.classification.stage3 import classify_stage3
from app.services.explainability.explainer import generate_explanation

# Confidence score map
_CONF_SCORE = {"High": 3, "Medium": 2, "Low": 1}

# Words in badge titles that strongly imply a level
_TITLE_LEVEL_RE = re.compile(
    r"\b(foundational?|foundation|introductory|beginner|entry.level"
    r"|intermediate|milestone|capstone|terminal|mastery|awareness"
    r"|application|exemplary|demonstrated|integrated)\b",
    re.IGNORECASE,
)

_TITLE_TO_LEVEL = {
    "foundation": "Foundational",
    "foundational": "Foundational",
    "introductory": "Foundational",
    "beginner": "Foundational",
    "entry-level": "Foundational",
    "entry level": "Foundational",
    "intermediate": "Milestone",
    "milestone": "Milestone",
    "capstone": "Terminal",
    "terminal": "Terminal",
    "mastery": "Mastery",
    "awareness": "Awareness",
    "application": "Application",
    "exemplary": "Exemplary",
    "demonstrated": "Demonstrated",
    "integrated": "Integrated",
}


def run_classification(bfs: BadgeFactSheet) -> ClassificationResult:
    """
    Orchestrate all three classification stages and return a ClassificationResult.

    Stage execution order:
      Stage 1 — classify_stage1(bfs): determines badge Category from issuer +
                audience signals (S1R01–S1R08); returns {category, confidence,
                rules_triggered}
      Stage 2 — classify_stage2(bfs): determines badge Type from earning
                criteria and assessment signals (S2R01–S2R11); first match wins;
                returns {type, confidence, rules_triggered, flag?}
      Stage 3 — classify_stage3(bfs, type): determines badge Level by branching
                on Stage 2 type; four independent branches: souvenir (S3S01),
                achievement (S3A01–S3A14), skill (S3SK01–S3SK05),
                competency (S3C01–S3C05)

    Post-stage processing:
      - Collects all triggered rule IDs from all three stages
      - Writes results back to bfs (Section 10 fields)
      - Overrides level_signal_source to "structured_field" when a structural
        Stage 3 rule (canvas/capstone) fired, preventing NLP regex signals
        from contaminating confidence
      - Calculates overall confidence via _calculate_confidence()
      - Builds ClassificationResult with signals and governance skeleton
      - Calls generate_explanation() to produce the plain-English explanation

    Governance log creation is handled by the calling route (classification.py),
    not here — the engine is DB-free.

    Mutates bfs.category_result, type_result, level_result,
    level_branch_used, classification_confidence, triggered_rules,
    explanation_text.
    """
    # ------------------------------------------------------------------
    # Stage 1 — Category
    # ------------------------------------------------------------------
    s1 = classify_stage1(bfs)

    # ------------------------------------------------------------------
    # Stage 2 — Type
    # ------------------------------------------------------------------
    s2 = classify_stage2(bfs)

    # Propagate Stage 2 flag to BFS if evaluator is missing
    if s2.get("flag") and "assessment_evaluator" not in bfs.missing_signals:
        bfs.missing_signals.append("assessment_evaluator")
        bfs.needs_followup_questions = True

    # ------------------------------------------------------------------
    # Stage 3 — Level (branches on Stage 2 type result)
    # ------------------------------------------------------------------
    s3 = classify_stage3(bfs, s2["type"])

    # ------------------------------------------------------------------
    # Collect all triggered rule IDs
    # ------------------------------------------------------------------
    all_rules: list[str] = (
        s1.get("rules_triggered", [])
        + s2.get("rules_triggered", [])
        + s3.get("rules_triggered", [])
    )

    # ------------------------------------------------------------------
    # Write results back to BFS Section 10
    # ------------------------------------------------------------------
    bfs.category_result = s1["category"]
    bfs.type_result = s2["type"]
    bfs.level_result = s3["level"]
    bfs.level_branch_used = s3.get("level_branch_used")
    bfs.triggered_rules = all_rules

    # If Stage 3 used a canvas/structural rule, override level_signal_source
    # so NLP regex signals don't contaminate confidence for canvas-decided badges.
    _STRUCTURAL_S3_RULES = {
        "S3S01", "S3A01", "S3A02", "S3A03", "S3A04",
        "S3A05", "S3A06", "S3A07", "S3A08", "S3A09",
    }
    if any(r in s3.get("rules_triggered", []) for r in _STRUCTURAL_S3_RULES):
        bfs.level_signal_source = "structured_field"

    # ------------------------------------------------------------------
    # Overall confidence (docs/taxonomy-rules.md)
    # ------------------------------------------------------------------
    overall_conf = _calculate_confidence(
        s1["confidence"], s2["confidence"], s3["confidence"], bfs
    )
    bfs.classification_confidence = overall_conf

    # ------------------------------------------------------------------
    # Build ClassificationResult
    # ------------------------------------------------------------------
    signals = _build_signals(bfs)
    review_recommended = overall_conf in ("Low", "Medium") or bfs.criteria_logic == "OR"

    result = ClassificationResult(
        badge_id=bfs.badge_id,
        badge_title=bfs.badge_title,
        issuer=bfs.issuer,
        classification=ClassificationSummary(
            category=bfs.category_result,
            type=bfs.type_result,
            level=bfs.level_result,
            confidence=overall_conf,
            level_branch_used=bfs.level_branch_used,
        ),
        rules_triggered=all_rules,
        signals_used=signals,
        explanation="",  # filled below
        follow_up_needed=bfs.needs_followup_questions,
        missing_signals=bfs.missing_signals,
        review_recommended=review_recommended,
        governance=GovernanceSummary(
            log_id="",  # filled by route after governance log is created
            classified_at=datetime.now(timezone.utc).isoformat(),
            reviewer_status="pending",
        ),
    )

    # Phase 6 — generate plain-English explanation now that result is assembled
    explanation = generate_explanation(bfs, result)
    bfs.explanation_text = explanation
    result.explanation = explanation

    return result


# ---------------------------------------------------------------------------
# Confidence calculation — docs/taxonomy-rules.md
# ---------------------------------------------------------------------------

def _calculate_confidence(
    s1_conf: str,
    s2_conf: str,
    s3_conf: str,
    bfs: BadgeFactSheet,
) -> str:
    """
    Compute the overall classification confidence from three stage scores
    and four downgrade conditions.

    Downgrade conditions (applied in priority order):
      1. Missing signals — any unresolved required field → always "Low",
         regardless of what the individual stage scores are.
      2. OR criteria logic — criteria that offer alternative paths cannot be
         verified programmatically → capped at "Medium".
      3. Regex/LLM level signal — a non-phrase level signal source weakens
         Stage 3 confidence from its declared value to "Medium".
      4. Title/description level conflict — when a level keyword in the badge
         title disagrees with the NLP-detected level in the description,
         confidence is capped at "Medium" and a note is recorded.

    If no downgrade condition fires, overall confidence = min(s1, s2, s3).
    """
    # Downgrade 1: missing signals → always Low regardless of other factors
    if bfs.needs_followup_questions:
        return "Low"

    # Downgrade 3: regex/LLM level signal reduces Stage 3 confidence
    effective_s3 = s3_conf
    if bfs.level_signal_source in ("regex_pattern", "llm_extraction"):
        effective_s3 = "Medium"

    # Conflict detection: level keyword in title vs NLP-detected level
    name_level = _extract_level_from_title(bfs.badge_title)
    desc_level = bfs.self_declared_level
    if name_level and desc_level and name_level != desc_level:
        if not bfs.confidence_notes:
            bfs.confidence_notes = (
                f"Level conflict: title suggests '{name_level}' but "
                f"description signals '{desc_level}'. Human review recommended."
            )
        return "Medium"

    # Minimum score across all three stages
    scores = [
        _CONF_SCORE.get(s1_conf, 1),
        _CONF_SCORE.get(s2_conf, 1),
        _CONF_SCORE.get(effective_s3, 1),
    ]
    min_score = min(scores)

    # A stage scoring Low always gives overall Low — OR criteria cannot override
    if min_score == 1:
        return "Low"

    # Downgrade 2: OR criteria — cannot be High when criteria offer alternatives
    if bfs.criteria_logic == "OR":
        return "Medium"

    if min_score >= 3:
        return "High"
    return "Medium"


def _extract_level_from_title(title: str) -> str | None:
    """Extract a level keyword from the badge title if one is present."""
    if not title:
        return None
    m = _TITLE_LEVEL_RE.search(title)
    if not m:
        return None
    return _TITLE_TO_LEVEL.get(m.group(1).lower())


# ---------------------------------------------------------------------------
# Signal summary builder
# ---------------------------------------------------------------------------

def _build_signals(bfs: BadgeFactSheet) -> dict[str, SignalEntry]:
    """Collect the key signals used in classification for the API response."""
    signals: dict[str, SignalEntry] = {}

    if bfs.issuer:
        source = "criteria_url" if bfs.criteria_id_url else "structured_field"
        signals["issuer"] = SignalEntry(value=bfs.issuer, source=source)

    if bfs.audience_type:
        signals["audience_type"] = SignalEntry(
            value=bfs.audience_type, source=bfs.audience_signal_source or "structured_field"
        )

    if bfs.assessment_evaluator:
        signals["assessment_evaluator"] = SignalEntry(
            value=bfs.assessment_evaluator, source="keyword_rule"
        )

    if bfs.assessment_type:
        signals["assessment_type"] = SignalEntry(
            value=bfs.assessment_type, source="keyword_rule"
        )

    if bfs.canvas_sequence_number is not None:
        signals["canvas_sequence_number"] = SignalEntry(
            value=bfs.canvas_sequence_number, source="structured_field"
        )

    if bfs.level_phrase_matched:
        signals["level_phrase"] = SignalEntry(
            value=bfs.level_phrase_matched,
            source=bfs.level_signal_source or "keyword_rule",
        )

    if bfs.bloom_level:
        signals["bloom_level"] = SignalEntry(
            value=bfs.bloom_level,
            source="spacy_verb",
            confidence=bfs.bloom_confidence,
        )

    return signals
