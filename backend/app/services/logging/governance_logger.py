"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Governance Logger — four functions for creating and updating governance logs.

Owns all DB interactions for the governance_logs table.
Routes call these functions; the classification engine remains DB-free.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.badge_fact_sheet import BadgeFactSheet
from app.models.classification_result import ClassificationResult
from app.models.governance_log import GovernanceLog

# Section 9 NLP signal fields stored in extracted_signals column
_NLP_SIGNAL_KEYS = {
    "audience_signal", "context_signal", "rigor_signal", "evidence_signal",
    "self_declared_level", "level_phrase_matched", "level_signal_source",
    "audience_signal_source", "needs_followup_questions", "missing_signals",
    "confidence_notes", "bloom_level", "bloom_confidence", "bloom_verbs_detected",
}


def create_log(
    bfs: BadgeFactSheet,
    result: ClassificationResult,
    db: Session,
    *,
    submitter_email: str | None = None,
    reviewer_email: str | None = None,
    review_token: str | None = None,
    review_token_expires_at: str | None = None,
    notification_sent_at: str | None = None,
) -> GovernanceLog:
    """
    Insert a new governance log record for a completed classification.

    What gets stored and why (auditable governance principle — every decision must be auditable):
      - raw_input: original verbatim text preserved so the log is self-contained
        and an auditor can re-classify from scratch if rules change
      - normalized_facts: full BFS serialized as JSON string; stores the complete
        post-NLP state including all extracted signals and confidence notes
      - extracted_signals: Section 9 NLP fields only, as a JSON string; provides
        a quick-access snapshot of what the NLP pipeline found without deserializing
        the entire BFS
      - triggered_rules: JSON array of rule IDs (e.g. ["S1R01", "S2R09", "S3A05"]);
        enables rule-level audit queries across the log table
      - recommended_category/type/level: the engine's output before human review;
        stored separately from final_* so overrides are traceable
      - final_category/type/level: seeded from recommended values on creation;
        updated by update_log_review() when a reviewer accepts or overrides
      - reviewer_status: "pending_review" when reviewer_email provided (email
        notification pathway), else "pending"
    """
    bfs_dict = bfs.model_dump()
    extracted = {k: bfs_dict[k] for k in _NLP_SIGNAL_KEYS if k in bfs_dict}

    reviewer_status = "pending_review" if reviewer_email else "pending"

    log = GovernanceLog(
        badge_id=bfs.badge_id,
        badge_title=bfs.badge_title,
        issuer=bfs.issuer,
        raw_input=bfs.raw_input_text,
        input_type=bfs.structured_source_type,
        normalized_facts=json.dumps(bfs_dict, default=str),
        extracted_signals=json.dumps(extracted, default=str),
        recommended_category=result.classification.category,
        recommended_type=result.classification.type,
        recommended_level=result.classification.level,
        confidence=result.classification.confidence,
        triggered_rules=json.dumps(result.rules_triggered),
        explanation_text=result.explanation or "",
        reviewer_status=reviewer_status,
        # Email routing fields
        submitter_email=submitter_email,
        reviewer_email=reviewer_email,
        review_token=review_token,
        review_token_expires_at=review_token_expires_at,
        notification_sent_at=notification_sent_at,
        # Seed final decision with recommendation — updated on review
        final_category=result.classification.category,
        final_type=result.classification.type,
        final_level=result.classification.level,
    )

    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_log_review(
    log_id: str,
    reviewer_status: str,
    reviewer_id: str,
    override_reason: str | None,
    override_category: str | None,
    override_type: str | None,
    override_level: str | None,
    db: Session,
) -> GovernanceLog:
    """
    Apply a reviewer decision to an existing governance log record.

    Partial override logic — reviewers may correct any subset of the three
    classification stages without affecting the others:
      override_category provided → final_category = override_category
      override_category is None  → final_category = recommended_category (unchanged)
      (same logic applies independently for override_type and override_level)

    This means a reviewer can correct only the level without touching category
    or type, and the log accurately records which stages were human-corrected
    vs accepted as recommended.

    Status values:
      accepted  → final_* set from recommended_*; override_* fields cleared
                  to avoid stale data from any previous partial edit
      overridden → override_* fields stored for audit; final_* computed via
                   partial override logic above; override_reason required

    After either status, final_locked_decision is built as a single string
    "{category} | {type} | {level}" and reviewed_at is set to UTC now.
    decision_notification_sent_at is recorded, and console notifications are
    printed (replace with real email delivery in production).
    """
    log = get_log(log_id, db)

    log.reviewer_status = reviewer_status
    log.reviewer_id = reviewer_id
    log.override_reason = override_reason
    log.reviewed_at = datetime.now(timezone.utc).isoformat()

    if reviewer_status == "accepted":
        log.final_category = log.recommended_category
        log.final_type = log.recommended_type
        log.final_level = log.recommended_level
        # Clear any stale override fields
        log.override_category = None
        log.override_type = None
        log.override_level = None

    elif reviewer_status == "overridden":
        log.override_category = override_category
        log.override_type = override_type
        log.override_level = override_level
        # Use override where provided, fall back to recommended for unchanged stages
        log.final_category = override_category if override_category is not None else log.recommended_category
        log.final_type = override_type if override_type is not None else log.recommended_type
        log.final_level = override_level if override_level is not None else log.recommended_level

    # Build human-readable locked decision summary
    category_str = log.final_category or "Unknown"
    type_str = log.final_type or "Unknown"
    level_str = log.final_level or "Unknown"
    log.final_locked_decision = f"{category_str} | {type_str} | {level_str}"

    # Record decision notification timestamp
    log.decision_notification_sent_at = datetime.now(timezone.utc).isoformat()

    db.commit()
    db.refresh(log)

    # Console notifications (replace with real email in production)
    print(
        f"\n[DECISION NOTIFY] Badge '{log.badge_title}' reviewed by "
        f"'{reviewer_id}': {reviewer_status}"
    )
    if log.submitter_email:
        print(
            f"  [EMAIL → submitter] {log.submitter_email} — "
            f"your badge '{log.badge_title}' was {reviewer_status}. "
            f"Final: {log.final_locked_decision}"
        )
    if log.reviewer_email:
        print(
            f"  [EMAIL → reviewer]  {log.reviewer_email} — "
            f"review recorded for '{log.badge_title}' ({reviewer_status})."
        )

    return log


def get_log(log_id: str, db: Session) -> GovernanceLog:
    """Return a single GovernanceLog by ID, or raise HTTP 404."""
    log = db.get(GovernanceLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail=f"Log not found: {log_id}")
    return log


def get_all_logs(limit: int, offset: int, db: Session) -> dict:
    """
    Return a paginated list of GovernanceLogs ordered by created_at descending.

    Returns a dict with keys: total, offset, limit, records.
    """
    total = db.query(func.count(GovernanceLog.id)).scalar()
    records = (
        db.query(GovernanceLog)
        .order_by(GovernanceLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "records": records,
    }

# Tanay's Change:

def find_matching_override(bfs: BadgeFactSheet, db: Session) -> Optional[GovernanceLog]:
    """
    Finds a previous reviewer override for the same/similar badge input.

    This does NOT change the classifier engine.
    It only checks past reviewer decisions before final output is returned.
    """

    current_title = (bfs.badge_title or "").strip().lower()
    current_issuer = (bfs.issuer or "").strip().lower()
    current_criteria = (bfs.earning_criteria_text or "").strip().lower()

    if not current_title:
        return None

    overridden_logs = (
        db.query(GovernanceLog)
        .filter(GovernanceLog.reviewer_status == "overridden")
        .order_by(GovernanceLog.reviewed_at.desc())
        .all()
    )

    for log in overridden_logs:
        try:
            facts = json.loads(log.normalized_facts or "{}")
        except Exception:
            facts = {}

        old_title = (facts.get("badge_title") or log.badge_title or "").strip().lower()
        old_issuer = (facts.get("issuer") or log.issuer or "").strip().lower()
        old_criteria = (facts.get("earning_criteria_text") or "").strip().lower()

        title_matches = old_title == current_title
        issuer_matches = old_issuer == current_issuer if current_issuer else True
        criteria_matches = old_criteria == current_criteria if current_criteria else True

        if title_matches and issuer_matches and criteria_matches:
            return log

    return None
