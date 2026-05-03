"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

POST /classify — runs the classification engine on a BadgeFactSheet.

Input:  ClassifyRequest (BadgeFactSheet + optional submitter_email / reviewer_email)
Output: ClassificationResult (with governance.log_id populated)

The route owns governance log creation so the engine stays DB-free.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.badge_fact_sheet import BadgeFactSheet
from app.models.classification_result import ClassificationResult
from app.services.classification.engine import run_classification
from app.services.logging.governance_logger import create_log, find_matching_override
from app.services.nlp.signal_extractor import SignalExtractor
from app.utils.canvas_code_parser import parse_canvas_code
from database import get_db

router = APIRouter()

_signal_extractor = SignalExtractor()


class ClassifyRequest(BadgeFactSheet):
    """
    Extends BadgeFactSheet with optional two-user workflow fields.

    These fields are not part of the classification logic — they are
    used only by the governance logger for notification routing.

    Backward compatible: existing clients that POST a plain BadgeFactSheet
    will simply leave these fields as None.
    """
    submitter_email: Optional[str] = None
    reviewer_email: Optional[str] = None


@router.post("/classify", response_model=ClassificationResult)
def classify_badge(
    req: ClassifyRequest,
    db: Session = Depends(get_db),
) -> ClassificationResult:
    """
    Classify a BadgeFactSheet through all three rule-engine stages.

    Steps:
      1. Run NLP signal extraction (idempotent — skips already-filled fields)
      2. Run classification engine (Stage 1 → 2 → 3)
      3. Generate review token (if reviewer_email provided)
      4. Print console notifications
      5. Create governance log record
      6. Return ClassificationResult with log_id
    """
    # Cast to plain BadgeFactSheet so engine stays ignorant of email fields
    bfs: BadgeFactSheet = req

    try:
        # Step 1a — Parse canvas code if present but not yet parsed
        if bfs.canvas_course_code and bfs.canvas_sequence_number is None:
            parsed = parse_canvas_code(bfs.canvas_course_code)
            if parsed:
                bfs.canvas_pathway_code = parsed.get("canvas_pathway_code")
                bfs.canvas_sequence_number = parsed.get("canvas_sequence_number")
                bfs.is_capstone = bfs.is_capstone or parsed.get("is_capstone", False)

        # Step 1b — NLP extraction (fills any signals not already set)
        bfs = _signal_extractor.extract_all(bfs)
        
# Tanay's Change
        # Step 2 — Classification engine
        result = run_classification(bfs)

        # Step 2b — Override memory layer
        # If reviewer previously overrode the same badge input,
        # use that reviewer-approved output as the final recommendation.
        previous_override = find_matching_override(bfs, db)

        if previous_override:
            result.classification.category = previous_override.final_category
            result.classification.type = previous_override.final_type
            result.classification.level = previous_override.final_level
            result.classification.confidence = "High"

            result.rules_triggered.append("OVERRIDE_MEMORY")

            result.explanation = (
                (result.explanation or "")
                + "\n\n[Override Memory Applied] "
                + "A previous reviewer-approved override was found for this same badge input. "
                + "The system reused the saved final decision: "
                + f"{previous_override.final_category} / "
                + f"{previous_override.final_type} / "
                + f"{previous_override.final_level}."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification error: {e}")

    # Step 3 — Review token (generated when reviewer_email provided)
    review_token: Optional[str] = None
    review_token_expires_at: Optional[str] = None
    notification_sent_at: Optional[str] = None

    if req.reviewer_email:
        review_token = str(uuid4())
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        review_token_expires_at = expires.isoformat()

    # Step 4 — Console notifications (replace with real email in production)
    now_iso = datetime.now(timezone.utc).isoformat()
    title = bfs.badge_title or "Untitled Badge"

    if req.submitter_email or req.reviewer_email:
        notification_sent_at = now_iso
        print(f"\n[CLASSIFICATION NOTIFY] Badge '{title}' classified.")

    if req.submitter_email:
        print(
            f"  [EMAIL → submitter] {req.submitter_email} — "
            f"your badge '{title}' has been classified and is pending review."
        )

    if req.reviewer_email and review_token:
        print(
            f"  [EMAIL → reviewer]  {req.reviewer_email} — "
            f"badge '{title}' is ready for your review. "
            f"Review link: /reviewer/review/{review_token}"
        )

    # Step 5 — Governance log
    log = create_log(
        bfs,
        result,
        db,
        submitter_email=req.submitter_email or None,
        reviewer_email=req.reviewer_email or None,
        review_token=review_token,
        review_token_expires_at=review_token_expires_at,
        notification_sent_at=notification_sent_at,
    )

    # Step 6 — Fill governance metadata now that we have the log
    result.governance.log_id = log.id
    result.governance.reviewer_status = log.reviewer_status

    return result
