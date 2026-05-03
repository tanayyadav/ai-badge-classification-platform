"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

GovernanceLog — SQLAlchemy model for the governance_logs SQLite table.

Schema defined in docs/governance-logging.md.
Every classification event and every human review decision must be stored here.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    # Badge identity
    # ------------------------------------------------------------------
    badge_id = Column(String, nullable=False)
    badge_title = Column(String, nullable=False)
    issuer = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Input — raw and input type
    # ------------------------------------------------------------------
    raw_input = Column(Text, nullable=False)
    # "obv2_json" | "obv3_json" | "form" | "free_text"
    input_type = Column(String, nullable=False)

    # ------------------------------------------------------------------
    # Normalized facts and signals — stored as JSON strings
    # ------------------------------------------------------------------
    # Full BadgeFactSheet serialized to JSON
    normalized_facts = Column(Text, nullable=False)
    # Section 9 NLP signals serialized to JSON
    extracted_signals = Column(Text, nullable=False)

    # ------------------------------------------------------------------
    # Recommendation from rule engine
    # ------------------------------------------------------------------
    recommended_category = Column(String, nullable=True)
    recommended_type = Column(String, nullable=True)
    recommended_level = Column(String, nullable=True)
    # "High" | "Medium" | "Low"
    confidence = Column(String, nullable=False)
    # JSON array of rule IDs e.g. '["S1R01", "S2R09", "S3A06"]'
    triggered_rules = Column(Text, nullable=False)
    explanation_text = Column(Text, nullable=False)

    # ------------------------------------------------------------------
    # Human review
    # ------------------------------------------------------------------
    # "pending" | "accepted" | "overridden"
    reviewer_status = Column(String, default="pending")
    reviewer_id = Column(String, nullable=True)
    override_reason = Column(Text, nullable=True)
    override_category = Column(String, nullable=True)
    override_type = Column(String, nullable=True)
    override_level = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Final locked decision — set after review
    # ------------------------------------------------------------------
    final_category = Column(String, nullable=True)
    final_type = Column(String, nullable=True)
    final_level = Column(String, nullable=True)
    # Human-readable summary of final decision e.g. "Academic / Skill / Application"
    final_locked_decision = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Two-user workflow — submitter / reviewer email routing
    # ------------------------------------------------------------------
    submitter_email = Column(String, nullable=True)
    reviewer_email = Column(String, nullable=True)

    # Opaque UUID token e-mailed to the reviewer; gates the review page
    review_token = Column(String, nullable=True)
    # ISO timestamp — token expires 30 days after classification
    review_token_expires_at = Column(String, nullable=True)

    # Console notification timestamps (real email would set these)
    notification_sent_at = Column(String, nullable=True)
    decision_notification_sent_at = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = Column(
        String,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    reviewed_at = Column(String, nullable=True)
