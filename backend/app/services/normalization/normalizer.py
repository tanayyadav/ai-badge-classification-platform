"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Normalizer — orchestrates all ingestion into a complete BadgeFactSheet.

Pipeline per input type:
  obv3_json  → parse_obv3()       → resolve_issuer() → parse_canvas_code()
  form       → map_form_to_bfs()  → resolve_issuer() → parse_canvas_code()
  free_text  → map_free_text_to_bfs()                → parse_canvas_code()

The rule engine NEVER touches raw input — it only reads the BFS
produced by this module.

R7: "Classify from Badge Fact Sheet only." — rule engine never reads raw input.
"""

import json
import re
from typing import Any, Dict

from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.ingestion.form_mapper import map_form_to_bfs, map_free_text_to_bfs
from app.services.ingestion.parser import parse_obv3
from app.services.normalization.issuer_resolver import resolve_issuer
from app.utils.canvas_code_parser import parse_canvas_code

# Matches canvas codes like MCAI.002.03 anywhere in a string
_CANVAS_CODE_RE = re.compile(r"\b([A-Z]{2,6}\.\d{3}\.\d{2})\b")

# Valid input types
VALID_INPUT_TYPES = {"obv3_json", "form", "free_text"}


def normalize(input_type: str, payload: Any) -> BadgeFactSheet:
    """
    Main entry point — accepts raw input and returns a fully normalised BFS.

    Pipeline (7 steps, applied in order):
      Step 1 — Parse: route obv3_json → parse_obv3(), form → map_form_to_bfs(),
               free_text → map_free_text_to_bfs()
      Step 2 — Resolve issuer: IR01–IR07 URL-pattern rules populate bfs.issuer
               when not already set by form input
      Step 3 — Canvas code: extract canvas_pathway_code, canvas_sequence_number,
               is_capstone from bfs.canvas_course_code or criteria_id_url
      Step 4 — is_capstone: derive from achievementType == "Micro Credential"
               if not already set by Step 3
      Step 5 — Prerequisite flag: set has_prerequisite_badges = True
               when bfs.prerequisite_badges is non-empty
      Step 6 — Input validation edge cases (EC01–EC03 + EC24):
               whitespace-only fields, duplicate criteria, minimum content,
               implied series from title keywords
      Step 7 — Required field check: populate missing_signals and
               set needs_followup_questions = True for any absent critical field

    The rule engine NEVER receives raw input — it only reads the BFS this
    function returns (BFS-only principle — rule engine never reads raw input).

    Args:
        input_type: One of "obv3_json" | "form" | "free_text"
        payload:    Dict (for obv3_json or form) or str (for free_text)

    Returns:
        BadgeFactSheet ready for NLP extraction and classification.

    Raises:
        ValueError: for unknown input_type or malformed payload.
    """
    if input_type not in VALID_INPUT_TYPES:
        raise ValueError(
            f"Unknown input_type '{input_type}'. "
            f"Must be one of: {sorted(VALID_INPUT_TYPES)}"
        )

    # ------------------------------------------------------------------
    # Step 1 — Parse raw input into a BFS
    # ------------------------------------------------------------------
    if input_type == "obv3_json":
        bfs = _ingest_obv3(payload)

    elif input_type == "form":
        if not isinstance(payload, dict):
            raise ValueError("Form payload must be a JSON object (dict).")
        bfs = map_form_to_bfs(payload)

    else:  # free_text
        raw_text = payload if isinstance(payload, str) else json.dumps(payload)
        bfs = map_free_text_to_bfs(raw_text)

    # ------------------------------------------------------------------
    # Step 2 — Resolve issuer from criteria_id_url (IR01–IR07)
    # Only runs if issuer not already set by form input
    # ------------------------------------------------------------------
    if bfs.issuer is None:
        bfs = resolve_issuer(bfs)

    # ------------------------------------------------------------------
    # Step 3 — Extract canvas course code from criteria_id_url if not
    # already set by the form mapper (e.g. URL ends in MCAI.002.03)
    # ------------------------------------------------------------------
    if not bfs.canvas_course_code and bfs.criteria_id_url:
        match = _CANVAS_CODE_RE.search(bfs.criteria_id_url)
        if match:
            bfs.canvas_course_code = match.group(1)

    # Parse canvas course code if present
    # Fills: canvas_pathway_code, canvas_sequence_number, is_capstone
    if bfs.canvas_course_code:
        canvas_fields = parse_canvas_code(bfs.canvas_course_code)
        if canvas_fields:
            bfs.canvas_pathway_code = canvas_fields.get("canvas_pathway_code")
            bfs.canvas_sequence_number = canvas_fields.get("canvas_sequence_number")
            # is_capstone from canvas code — may already be True from achievementType
            bfs.is_capstone = bfs.is_capstone or canvas_fields.get("is_capstone", False)

    # ------------------------------------------------------------------
    # Step 4 — Derive is_capstone from achievementType if not already set
    # ------------------------------------------------------------------
    if not bfs.is_capstone and bfs.achievement_type == "Micro Credential":
        bfs.is_capstone = True

    # ------------------------------------------------------------------
    # Step 5 — Derive has_prerequisite_badges from prerequisite list
    # ------------------------------------------------------------------
    if bfs.prerequisite_badges:
        bfs.has_prerequisite_badges = True

    # ------------------------------------------------------------------
    # Step 6 — Input validation edge cases (EC01–EC03)
    # ------------------------------------------------------------------
    _sanitize_whitespace_fields(bfs)   # EC01
    _check_duplicate_content(bfs)      # EC02
    _check_minimum_content(bfs)        # EC03

    # ------------------------------------------------------------------
    # Step 6b — Implied series detection from title (EC24)
    # ------------------------------------------------------------------
    _check_implied_series(bfs)         # EC24

    # ------------------------------------------------------------------
    # Step 7 — Validate required fields; add to missing_signals
    # ------------------------------------------------------------------
    _check_required_fields(bfs)

    return bfs


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _ingest_obv3(payload: Any) -> BadgeFactSheet:
    """Accept dict or raw JSON string for OBv3 input."""
    if isinstance(payload, str):
        try:
            json_data = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}") from e
        return parse_obv3(json_data, raw_input_text=payload)

    if isinstance(payload, dict):
        return parse_obv3(payload, raw_input_text=json.dumps(payload))

    raise ValueError("obv3_json payload must be a JSON object or string.")


def _check_required_fields(bfs: BadgeFactSheet) -> None:
    """
    Populate missing_signals for fields the rule engine critically needs.
    Does NOT raise — degrades gracefully when signals are missing (R10 — degrade gracefully).
    """
    if not bfs.badge_title:
        _add_missing(bfs, "badge_title")

    if not bfs.badge_description:
        _add_missing(bfs, "badge_description")

    if not bfs.earning_criteria_text:
        _add_missing(bfs, "earning_criteria_text")

    if bfs.issuer is None and "issuer" not in bfs.missing_signals:
        _add_missing(bfs, "issuer")

    if bfs.missing_signals:
        bfs.needs_followup_questions = True


def _add_missing(bfs: BadgeFactSheet, field: str) -> None:
    if field not in bfs.missing_signals:
        bfs.missing_signals.append(field)


def _sanitize_whitespace_fields(bfs: BadgeFactSheet) -> None:
    """
    EC01 — Whitespace-only field detection.

    For form and obv3_json sources, fields that arrive as empty or
    whitespace-only strings represent explicit blank submissions — treat them
    as absent: set to None and flag as missing.

    The form mapper's _str() helper strips input values before they reach
    this function, so "   " arrives here as "". Both are caught by the
    val.strip() == "" check below.

    For free_text sources, badge_title is never extracted from the text and
    stays at its BFS default of "". Firing EC01 for free_text defaults would
    be incorrect — the field was never submitted, just absent — so we skip
    EC01 for free_text entirely.
    """
    if bfs.structured_source_type == "free_text":
        return

    _WATCHED = ("badge_title", "badge_description", "earning_criteria_text")
    for field in _WATCHED:
        val = getattr(bfs, field, None)
        if val is not None and val.strip() == "":
            setattr(bfs, field, None)
            _add_missing(bfs, field)
            bfs.needs_followup_questions = True


def _check_duplicate_content(bfs: BadgeFactSheet) -> None:
    """
    EC02 — Criteria identical to description.

    When earning_criteria_text and badge_description contain exactly the same
    text, the criteria field provides no additional signal. Flag for follow-up.

    Skipped for free_text input: map_free_text_to_bfs() intentionally stores
    the same raw text in both fields so the NLP layers have maximum surface
    area. Flagging it as missing would incorrectly degrade confidence for
    every free-text submission.
    """
    if not (bfs.earning_criteria_text and bfs.badge_description):
        return
    if bfs.earning_criteria_text.strip() != bfs.badge_description.strip():
        return
    if bfs.structured_source_type == "free_text":
        return
    if "criteria_identical_to_description" not in (bfs.confidence_notes or ""):
        bfs.confidence_notes = (
            (bfs.confidence_notes or "")
            + " | WARN: criteria_identical_to_description"
        ).lstrip(" |").strip()
    _add_missing(bfs, "earning_criteria_meaningful_content")
    bfs.needs_followup_questions = True


def _check_minimum_content(bfs: BadgeFactSheet) -> None:
    """
    EC03 — Minimum content warning.

    Short fields are flagged in confidence_notes only — they do NOT block
    classification or add to missing_signals.
    """
    if bfs.badge_description and len(bfs.badge_description.strip()) < 50:
        bfs.confidence_notes = (
            (bfs.confidence_notes or "") + " | WARN: description_too_short"
        ).lstrip(" |").strip()

    if bfs.earning_criteria_text and len(bfs.earning_criteria_text.strip()) < 30:
        bfs.confidence_notes = (
            (bfs.confidence_notes or "") + " | WARN: criteria_too_short"
        ).lstrip(" |").strip()


# EC24 — keywords that imply a series/progression relationship
_SERIES_KEYWORDS: list[str] = [
    "foundational", "foundation", "intermediate",
    "advanced", "capstone", "introduction to",
    "part 1", "part 2", "part 3",
    "level 1", "level 2", "level 3",
    "course 1", "course 2", "course 3",
]


def _check_implied_series(bfs: BadgeFactSheet) -> None:
    """
    EC24 — Implied series detection from badge title.

    When the title contains a level/position keyword that suggests a
    series progression (e.g. "Introduction to", "Part 2", "Advanced"),
    and no formal pathway has been established (no canvas_course_code
    or pathway_name), set progression_implied = True and add a note.

    This is advisory only — it does not block classification.
    """
    if not bfs.badge_title:
        return
    if bfs.canvas_course_code or bfs.pathway_name:
        return

    title_lower = bfs.badge_title.lower()
    if any(kw in title_lower for kw in _SERIES_KEYWORDS):
        bfs.progression_implied = True
        bfs.confidence_notes = (
            (bfs.confidence_notes or "")
            + " | NOTE: title suggests series progression — "
            "consider adding pathway information for better classification"
        ).lstrip(" |").strip()
