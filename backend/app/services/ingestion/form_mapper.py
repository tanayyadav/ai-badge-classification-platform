"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Form mapper — maps proposal form fields directly into a BadgeFactSheet.

The form is the second input mode (Tab 1 in the frontend).
Unlike JSON parsing, the form fields map 1:1 to BFS fields
so no format detection or alignment parsing is needed.

All fields are optional at ingestion time — missing_signals
will be populated later by the normalizer's gap detector.
"""

import json
from typing import Any, Dict

from app.models.badge_fact_sheet import BadgeFactSheet


def map_form_to_bfs(form_data: Dict[str, Any]) -> BadgeFactSheet:
    """
    Map a proposal form payload dict into a BadgeFactSheet.

    The caller is responsible for passing validated field names.
    Unknown keys are ignored (BFS has extra="forbid" so we only
    pass known fields explicitly).

    Args:
        form_data: Dict of form field names and values from the API.

    Returns:
        A partially-filled BadgeFactSheet ready for issuer resolution
        and NLP extraction.
    """
    bfs = BadgeFactSheet()
    bfs.structured_source_type = "form"
    bfs.obv_version = None
    bfs.raw_input_text = json.dumps(form_data)
    bfs.obv_fields_present = []

    # ------------------------------------------------------------------
    # Section 2 — Core Identity
    # ------------------------------------------------------------------
    bfs.badge_title = _str(form_data, "badge_title")
    bfs.badge_description = _str(form_data, "badge_description")
    bfs.issuer = _str(form_data, "issuer") or None
    bfs.achievement_type = _str(form_data, "achievement_type") or None
    bfs.external_partner = _str(form_data, "external_partner") or None

    # ------------------------------------------------------------------
    # Section 3 — Audience and Context
    # ------------------------------------------------------------------
    bfs.intended_audience = _str(form_data, "intended_audience") or None
    bfs.audience_type = _str(form_data, "audience_type") or None
    bfs.institutional_context = _str(form_data, "institutional_context") or None
    bfs.audience_restriction = _str(form_data, "audience_restriction") or None
    bfs.is_credit_bearing = bool(form_data.get("is_credit_bearing", False))
    bfs.pdh_credits = _str(form_data, "pdh_credits") or None
    bfs.credit_type = _str(form_data, "credit_type") or None

    # ------------------------------------------------------------------
    # Section 4 — Earning Criteria
    # ------------------------------------------------------------------
    bfs.earning_criteria_text = _str(form_data, "earning_criteria_text")
    bfs.assessment_required = _str(form_data, "assessment_required") or "unknown"
    bfs.assessment_type = _str(form_data, "assessment_type") or None
    bfs.assessment_type_detail = _str(form_data, "assessment_type_detail") or None
    bfs.assessment_evaluator = _str(form_data, "assessment_evaluator") or None
    bfs.assessment_pass_threshold = _str(form_data, "assessment_pass_threshold") or None
    bfs.assessment_modality = _str(form_data, "assessment_modality") or None
    bfs.badge_purpose = _str(form_data, "badge_purpose") or "recognition"
    bfs.downstream_workflow = _str(form_data, "downstream_workflow") or None
    bfs.mandatory_for = _str(form_data, "mandatory_for") or None

    prereqs = form_data.get("prerequisite_badges", [])
    bfs.prerequisite_badges = prereqs if isinstance(prereqs, list) else []
    bfs.has_prerequisite_badges = len(bfs.prerequisite_badges) > 0

    # ------------------------------------------------------------------
    # Section 5 — Evidence
    # ------------------------------------------------------------------
    bfs.evidence_required = _str(form_data, "evidence_required") or "unknown"
    bfs.evidence_type = _str(form_data, "evidence_type") or None
    bfs.evidence_description = _str(form_data, "evidence_description") or None
    bfs.expert_evaluation_required = bool(
        form_data.get("expert_evaluation_required", False)
    )

    # ------------------------------------------------------------------
    # Section 6 — Pathway and Positioning
    # ------------------------------------------------------------------
    bfs.canvas_course_code = _str(form_data, "canvas_course_code") or None
    bfs.pathway_name = _str(form_data, "pathway_name") or None

    # canvas_pathway_length — needed for S3A07 (seq 3 in pathway of 3 or 4)
    cpl = form_data.get("canvas_pathway_length")
    if cpl is not None:
        try:
            bfs.canvas_pathway_length = int(cpl)
        except (TypeError, ValueError):
            pass

    # pathway_position — needed for S3A13 (standalone attendance badge)
    bfs.pathway_position = _str(form_data, "pathway_position") or None

    # canvas_sequence_number — direct position override without a full course code
    csn = form_data.get("canvas_sequence_number")
    if csn is not None:
        try:
            bfs.canvas_sequence_number = int(csn)
        except (TypeError, ValueError):
            pass

    # ------------------------------------------------------------------
    # Section 7 — Skill and Competency Signals
    # ------------------------------------------------------------------
    bfs.real_world_context = bool(form_data.get("real_world_context", False))
    bfs.multi_context_evidence = bool(form_data.get("multi_context_evidence", False))
    bfs.leadership_evidence = bool(form_data.get("leadership_evidence", False))

    ksa = form_data.get("ksa_dimensions", [])
    bfs.ksa_dimensions = ksa if isinstance(ksa, list) else []

    return bfs


def map_free_text_to_bfs(raw_text) -> BadgeFactSheet:
    """
    Wrap a plain-text description into a minimal BFS.

    All signals will come from NLP extraction. The full text is
    stored in both earning_criteria_text and raw_input_text so
    the NLP layer has maximum surface area to work with.

    A lightweight keyword pass resolves issuer when the submitter
    mentions a known NJIT office by name or abbreviation — avoids
    a mandatory follow-up question for straightforward free-text
    submissions.

    Handles double-wrapping: the normalizer receives a dict payload
    like {"text": "..."} from the frontend and json.dumps it before
    calling this function. Both the dict form and the JSON-stringified
    form are unwrapped to extract the actual text value.
    """
    # Unwrap case 1: called directly with a dict {"text": "..."}
    if isinstance(raw_text, dict):
        raw_text = raw_text.get("text", "") or raw_text.get("free_text", str(raw_text))

    # Unwrap case 2: normalizer passed json.dumps({"text": "..."})
    if isinstance(raw_text, str):
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                extracted = parsed.get("text", "") or parsed.get("free_text", "")
                if extracted:
                    raw_text = extracted
        except (json.JSONDecodeError, TypeError):
            pass  # Not a JSON wrapper — use raw_text as-is

    raw_text = str(raw_text).strip()

    bfs = BadgeFactSheet()
    bfs.structured_source_type = "free_text"
    bfs.obv_version = None
    bfs.raw_input_text = raw_text
    bfs.obv_fields_present = []

    # For free text, treat the whole blob as both description and criteria
    bfs.badge_description = raw_text
    bfs.earning_criteria_text = raw_text

    # Layer 0 — issuer keyword detection.
    # Checked before URL-based resolver so explicit mentions take precedence.
    # Order matters: longer / more specific strings first to avoid false matches.
    # Space-padded abbreviations (e.g. " ldi ") miss start/end of text and
    # punctuation — use word-boundary helper _word_in() instead.
    _lower = raw_text.lower()

    def _word_in(abbr: str) -> bool:
        """True if abbr appears as a whole word (not substring of another word)."""
        import re as _re
        return bool(_re.search(r"(?<![a-z])" + _re.escape(abbr) + r"(?![a-z])", _lower))

    _ISSUER_KEYWORDS: list[tuple[str, list[str]]] = [
        # OSIL — longer/more-specific strings first
        ("OSIL", [
            "center for student entrepreneurship",
            "student entrepreneurship center",
            "office of student involvement",
            "student involvement and leadership",
            "student involvement office",
            "entrepreneurship program",
            "entrepreneurship center",
            "student leadership",
            "student involvement",
        ]),
        # LDI — covers full name, initiative variant, and program-type keywords
        ("LDI", [
            "learning and development initiative",
            "learning and development institute",
            "learning and development office",
            "learning and development",
            "continuing education office",
            "continuing education",
            "workforce development",
            "non-credit",
        ]),
        # Makerspace
        ("Makerspace", [
            "njit makerspace",
            "maker space",
            "makerspace",
        ]),
        # NCE — longer first
        ("NCE", [
            "newark college of engineering",
            "college of engineering",
        ]),
        # OGI — longer first
        ("OGI", [
            "office of global initiatives",
            "global initiatives",
            "international student",
        ]),
    ]

    # Short abbreviations matched as whole words only (word-boundary safe).
    _ABBR_ISSUERS: list[tuple[str, str]] = [
        ("osil", "OSIL"),
        ("ldi",  "LDI"),
        ("nce",  "NCE"),
        ("ogi",  "OGI"),
    ]

    detected_issuer: str | None = None

    # 1. Phrase match (longer phrases already ordered first per issuer).
    for issuer_name, keywords in _ISSUER_KEYWORDS:
        if any(kw in _lower for kw in keywords):
            detected_issuer = issuer_name
            break

    # 2. Abbreviation word-boundary match (only if phrase match found nothing).
    if detected_issuer is None:
        for abbr, issuer_name in _ABBR_ISSUERS:
            if _word_in(abbr):
                detected_issuer = issuer_name
                break

    # 3. Multi-word abbreviation "CSE NJIT" — checked as plain substring
    #    (already specific enough; word-boundary not needed for a two-word phrase).
    if detected_issuer is None and ("cse njit" in _lower or "njit cse" in _lower):
        detected_issuer = "OSIL"

    if detected_issuer:
        bfs.issuer = detected_issuer
        bfs.governing_office = detected_issuer

        # Issuer-specific audience defaults.
        if detected_issuer == "LDI":
            # Use self-referential phrases only — "an instructor watched me"
            # should NOT mark the badge earner as njit_employee.
            # Only phrases where the EARNER describes their own role trigger this.
            _EMPLOYEE_SELF_REF = (
                "i am a faculty", "i am an instructor", "i am a staff",
                "as a faculty", "as an instructor", "as a staff",
                "for faculty", "for staff", "for instructors",
            )
            if any(p in _lower for p in _EMPLOYEE_SELF_REF):
                bfs.audience_type = "njit_employee"
            elif any(kw in _lower for kw in ("professional", "workforce", "industry")):
                bfs.audience_type = "external_professional"
            # else: leave None — NLP will try to infer from context

        elif detected_issuer in ("Makerspace", "OSIL", "NCE", "OGI"):
            # These issuers serve NJIT students; lock in now so NLP audience
            # phrases (e.g. "instructor" as evaluator) don't override.
            bfs.audience_type = "njit_student"

    return bfs


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _str(data: Dict[str, Any], key: str) -> str:
    """Return a stripped string value or empty string if missing/None."""
    val = data.get(key, "")
    return str(val).strip() if val is not None else ""
