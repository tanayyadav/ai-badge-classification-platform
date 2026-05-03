"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

ClassificationResult — the structured output of the rule engine.

Matches the API contract defined in docs/architecture.md.
This is a Pydantic model used for API responses only.
The full BadgeFactSheet is the authoritative internal record.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ClassificationSummary(BaseModel):
    """The three-stage taxonomy result with confidence."""
    category: Optional[str] = None
    type: Optional[str] = None
    level: Optional[str] = None
    # "High" | "Medium" | "Low"
    confidence: str = "Low"
    # "souvenir" | "achievement" | "skill" | "competency"
    level_branch_used: Optional[str] = None


class SignalEntry(BaseModel):
    """A single extracted signal with its value and source."""
    value: Any = None
    # "criteria_url" | "keyword_rule" | "regex_pattern" | "spacy_verb" |
    # "llm_extraction" | "structured_field"
    source: Optional[str] = None
    confidence: Optional[str] = None


class GovernanceSummary(BaseModel):
    """Governance log reference embedded in every classification response."""
    log_id: str
    classified_at: str
    # "pending" | "accepted" | "overridden"
    reviewer_status: str = "pending"


class ClassificationResult(BaseModel):
    """
    Full classification response returned by POST /classify.

    Mirrors the JSON structure in docs/architecture.md.
    """

    badge_id: str
    badge_title: str
    issuer: Optional[str] = None

    classification: ClassificationSummary

    rules_triggered: List[str] = []

    # Key signals used — keyed by signal name, value is a SignalEntry
    signals_used: Dict[str, SignalEntry] = {}

    explanation: str = ""

    follow_up_needed: bool = False
    missing_signals: List[str] = []
    review_recommended: bool = False

    governance: GovernanceSummary
