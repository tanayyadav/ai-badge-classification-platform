"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

OBv3 JSON parser.

Parses an Open Badges v3 JSON object into a BadgeFactSheet.

IMPORTANT: All NJIT badges are OBv3 only.
- issuer is NEVER present in OBv3 JSON — always left as None for issuer_resolver
- tags are NEVER present in OBv3 JSON — always empty list
- alignments field is plural ("alignments") in OBv3

Fields extracted (BFS Section references):
  Section 1: structured_source_type, obv_version, obv_fields_present, criteria_id_url
  Section 2: badge_title, badge_description, achievement_type
  Section 4: earning_criteria_text
  Section 8: skill_alignments, alignment_count, alignment_frameworks,
             institutional_framework_reference, njit_core_competency
"""

import json
from typing import Any

from app.models.badge_fact_sheet import BadgeFactSheet
from app.utils.obv_version_detector import detect_obv_version


def parse_obv3(json_data: dict, raw_input_text: str = "") -> BadgeFactSheet:
    """
    Parse an OBv3 JSON dict into a BadgeFactSheet.

    Args:
        json_data:       Parsed JSON dict (caller must have already loaded it).
        raw_input_text:  The original raw string — preserved verbatim in BFS.

    Returns:
        A partially-filled BadgeFactSheet (Sections 1, 2, 4, 8).
        Issuer resolution, NLP extraction, and classification happen downstream.

    Raises:
        ValueError: if the JSON is not valid OBv3.
    """
    # Validate format — raises ValueError for OBv2 or unknown
    version = detect_obv_version(json_data)

    bfs = BadgeFactSheet()
    bfs.structured_source_type = "obv3_json"
    bfs.obv_version = version
    bfs.raw_input_text = raw_input_text or json.dumps(json_data)

    # ------------------------------------------------------------------
    # Track which top-level fields are present (Section 1)
    # ------------------------------------------------------------------
    bfs.obv_fields_present = list(json_data.keys())

    # ------------------------------------------------------------------
    # Section 2 — Core Identity
    # ------------------------------------------------------------------
    bfs.badge_title = json_data.get("name", "").strip()
    bfs.badge_description = json_data.get("description", "").strip()

    # achievementType resolution — two-step priority:
    #   1. "achievementType" field (string or list) — highest priority
    #   2. "type" array fallback — used when achievementType is absent
    #
    # type array rules:
    #   ["Achievement"]                 → "Achievement"
    #   ["Achievement", "Competency"]   → "Competency"  (non-Achievement value wins)
    #   ["Achievement", "Micro Credential"] → "Micro Credential"
    raw_at = json_data.get("achievementType", None)

    if raw_at is not None:
        # Explicit achievementType field — normalise list to first string
        if isinstance(raw_at, list):
            raw_at = raw_at[0] if raw_at else None
        bfs.achievement_type = raw_at
    else:
        # Fall back to "type" array
        type_array = json_data.get("type", [])
        if isinstance(type_array, str):
            type_array = [type_array]
        # Filter out the base "Achievement" marker to find the specific type
        specific = [t for t in type_array if t != "Achievement"]
        if specific:
            bfs.achievement_type = specific[0]
        elif "Achievement" in type_array:
            bfs.achievement_type = "Achievement"
        else:
            bfs.achievement_type = None

    # issuer — NEVER in OBv3; left as None for issuer_resolver
    bfs.issuer = None
    bfs.issuer_url = None

    # tags — NEVER in OBv3
    bfs.tags = []

    # ------------------------------------------------------------------
    # Section 4 — Earning Criteria (criteria object)
    # ------------------------------------------------------------------
    criteria = json_data.get("criteria", {})
    if isinstance(criteria, dict):
        bfs.criteria_id_url = criteria.get("id") or criteria.get("@id") or None
        bfs.earning_criteria_text = (criteria.get("narrative") or "").strip()
    elif isinstance(criteria, str):
        # Rare — criteria may be a plain URL string
        bfs.criteria_id_url = criteria
        bfs.earning_criteria_text = ""

    # ------------------------------------------------------------------
    # Section 8 — Alignments (OBv3 uses plural "alignments")
    # ------------------------------------------------------------------
    raw_alignments: list[Any] = json_data.get("alignments", [])
    parsed_alignments = []
    frameworks: list[str] = []
    njit_competency = None
    has_empty_framework = False

    for a in raw_alignments:
        if not isinstance(a, dict):
            continue

        framework = a.get("targetFramework") or a.get("framework") or ""
        name = a.get("targetName") or a.get("name") or ""
        code = a.get("targetCode") or a.get("code") or ""
        description = a.get("targetDescription") or a.get("description") or ""

        parsed_alignments.append({
            "name": name,
            "code": code,
            "framework": framework,
            "description": description,
        })

        if framework:
            if framework not in frameworks:
                frameworks.append(framework)
        else:
            # Empty targetFramework signals an NJIT institutional reference
            has_empty_framework = True

        # Capture NJIT core competency reference
        if "competency" in name.lower() and njit_competency is None:
            njit_competency = name

    bfs.skill_alignments = parsed_alignments
    bfs.alignment_count = len(parsed_alignments)
    bfs.alignment_frameworks = frameworks
    bfs.institutional_framework_reference = has_empty_framework
    bfs.njit_core_competency = njit_competency

    # ------------------------------------------------------------------
    # created_on — OBv3 may have "image.caption" or top-level date fields
    # ------------------------------------------------------------------
    bfs.created_on = json_data.get("issueDate") or json_data.get("issuedOn") or None

    return bfs


def parse_obv3_string(raw_text: str) -> BadgeFactSheet:
    """
    Convenience wrapper — accepts raw JSON string, parses and returns BFS.
    """
    try:
        json_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    return parse_obv3(json_data, raw_input_text=raw_text)
