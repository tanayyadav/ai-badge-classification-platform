"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Reviewer-specific routes — authentication, dashboard queue, and token-based review access.

Routes:
  POST /reviewer/auth              — password login, returns access token
  GET  /reviewer/queue             — protected: pending + recently reviewed logs + stats
  GET  /reviewer/review/{token}    — validate a review_token, return log data for review
"""

import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.governance_log import GovernanceLog
from database import get_db

router = APIRouter(prefix="/reviewer")

# ---------------------------------------------------------------------------
# In-memory token store — cleared on server restart (acceptable for prototype)
# ---------------------------------------------------------------------------
_active_tokens: set[str] = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_auth(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency — extracts and validates the reviewer Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Reviewer authentication required.")
    token = authorization[len("Bearer "):]
    if token not in _active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired reviewer token.")
    return token


def _log_to_queue_item(log: GovernanceLog) -> dict:
    return {
        "id": log.id,
        "badge_title": log.badge_title,
        "issuer": log.issuer,
        "input_type": log.input_type,
        "recommended_category": log.recommended_category,
        "recommended_type": log.recommended_type,
        "recommended_level": log.recommended_level,
        "confidence": log.confidence,
        "reviewer_status": log.reviewer_status,
        "submitter_email": log.submitter_email,
        "reviewer_email": log.reviewer_email,
        "review_token": log.review_token,
        "created_at": log.created_at,
        "reviewed_at": log.reviewed_at,
    }


# ---------------------------------------------------------------------------
# POST /reviewer/auth
# ---------------------------------------------------------------------------

class AuthRequest(BaseModel):
    password: str


@router.post("/auth")
def reviewer_auth(req: AuthRequest) -> dict:
    """
    Authenticate as a reviewer using the shared REVIEWER_PASSWORD.

    Returns an in-memory access token that authorizes all reviewer endpoints.
    The token is valid until the server restarts.
    """
    expected = os.getenv("REVIEWER_PASSWORD", "")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Reviewer password not configured on server.",
        )
    if req.password != expected:
        raise HTTPException(status_code=401, detail="Incorrect reviewer password.")

    token = str(uuid4())
    _active_tokens.add(token)
    return {"access_token": token}


# ---------------------------------------------------------------------------
# GET /reviewer/queue
# ---------------------------------------------------------------------------

@router.get("/queue")
def reviewer_queue(
    db: Session = Depends(get_db),
    _token: str = Depends(_require_auth),
) -> dict:
    """
    Return the reviewer dashboard data:
      - stats: total, pending_review, accepted, overridden
      - pending: logs with reviewer_status in ("pending", "pending_review")
      - recently_reviewed: last 20 accepted/overridden, ordered by reviewed_at desc
    """
    all_logs = db.query(GovernanceLog).all()

    stats = {
        "total": len(all_logs),
        "pending_review": sum(
            1 for l in all_logs if l.reviewer_status in ("pending", "pending_review")
        ),
        "accepted": sum(1 for l in all_logs if l.reviewer_status == "accepted"),
        "overridden": sum(1 for l in all_logs if l.reviewer_status == "overridden"),
    }

    pending = [
        _log_to_queue_item(l)
        for l in all_logs
        if l.reviewer_status in ("pending", "pending_review")
    ]
    pending.sort(key=lambda x: x["created_at"] or "", reverse=True)

    reviewed = [
        _log_to_queue_item(l)
        for l in all_logs
        if l.reviewer_status in ("accepted", "overridden")
    ]
    reviewed.sort(key=lambda x: x["reviewed_at"] or "", reverse=True)

    return {
        "stats": stats,
        "pending": pending,
        "recently_reviewed": reviewed[:20],
    }


# ---------------------------------------------------------------------------
# GET /reviewer/review/{token}
# ---------------------------------------------------------------------------

@router.get("/review/{token}")
def get_review_by_token(
    token: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Validate a review_token and return the full log data for the reviewer UI.

    Error responses:
      404 — token not found
      410 — token expired
      409 — already reviewed
    """
    import json

    log: Optional[GovernanceLog] = (
        db.query(GovernanceLog)
        .filter(GovernanceLog.review_token == token)
        .first()
    )

    if log is None:
        raise HTTPException(status_code=404, detail="Review token not found.")

    # Check expiry
    if log.review_token_expires_at:
        try:
            expires = datetime.fromisoformat(log.review_token_expires_at)
            if datetime.now(timezone.utc) > expires:
                raise HTTPException(
                    status_code=410,
                    detail="This review link has expired. Contact the submitter for a new link.",
                )
        except ValueError:
            pass  # Malformed date — let it through

    # Already reviewed
    if log.reviewer_status in ("accepted", "overridden"):
        raise HTTPException(
            status_code=409,
            detail=f"This badge has already been reviewed ({log.reviewer_status}).",
        )

    # Parse normalized_facts to reconstruct BFS-like signal data
    bfs_dict: dict = {}
    try:
        bfs_dict = json.loads(log.normalized_facts or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "log_id": log.id,
        "badge_title": log.badge_title,
        "issuer": log.issuer,
        "input_type": log.input_type,
        "submitter_email": log.submitter_email,
        "reviewer_email": log.reviewer_email,
        "review_token": log.review_token,
        "recommended_category": log.recommended_category,
        "recommended_type": log.recommended_type,
        "recommended_level": log.recommended_level,
        "confidence": log.confidence,
        "triggered_rules": json.loads(log.triggered_rules or "[]"),
        "explanation_text": log.explanation_text,
        "reviewer_status": log.reviewer_status,
        "created_at": log.created_at,
        "bfs": bfs_dict,
        "missing_signals": bfs_dict.get("missing_signals", []),
    }
