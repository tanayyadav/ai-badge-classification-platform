"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

GET /logs         — paginated list of all governance logs
GET /logs/{log_id} — full detail for a single log

Query params for GET /logs:
  limit  : int, default 20, max 100
  offset : int, default 0
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.governance_log import GovernanceLog
from app.services.logging.governance_logger import get_all_logs, get_log
from database import get_db

router = APIRouter()


@router.get("/logs")
def list_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return a paginated list of governance logs, newest first.

    Response shape:
      { total, offset, limit, records: [...] }
    """
    result = get_all_logs(limit=limit, offset=offset, db=db)
    return {
        "total": result["total"],
        "offset": result["offset"],
        "limit": result["limit"],
        "records": [_log_to_dict(log) for log in result["records"]],
    }


@router.get("/logs/{log_id}")
def get_log_detail(
    log_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return full detail for a single governance log. 404 if not found."""
    log = get_log(log_id, db)
    return _log_to_dict(log)


def _log_to_dict(log: GovernanceLog) -> dict:
    """Serialize a GovernanceLog ORM object to a plain dict."""
    return {
        "id": log.id,
        "badge_id": log.badge_id,
        "badge_title": log.badge_title,
        "issuer": log.issuer,
        "input_type": log.input_type,
        "raw_input": log.raw_input,
        "normalized_facts": log.normalized_facts,
        "extracted_signals": log.extracted_signals,
        "recommended_category": log.recommended_category,
        "recommended_type": log.recommended_type,
        "recommended_level": log.recommended_level,
        "confidence": log.confidence,
        "triggered_rules": log.triggered_rules,
        "explanation_text": log.explanation_text,
        "reviewer_status": log.reviewer_status,
        "reviewer_id": log.reviewer_id,
        "override_reason": log.override_reason,
        "override_category": log.override_category,
        "override_type": log.override_type,
        "override_level": log.override_level,
        "final_category": log.final_category,
        "final_type": log.final_type,
        "final_level": log.final_level,
        "final_locked_decision": log.final_locked_decision,
        "created_at": log.created_at,
        "reviewed_at": log.reviewed_at,
    }
