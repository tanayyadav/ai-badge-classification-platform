"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Issuer resolver — maps criteria_id_url to an NJIT issuer name.

Rules IR01–IR07 from docs/taxonomy-rules.md.

NOTE: Since OBv2 is no longer supported, IR05 (badgr.io issuer_url)
and IR06 (unmatched OBv2 issuer_url) are not applicable.
Only criteria_id_url-based resolution (IR01–IR04) and the
missing-signal fallback (IR07) are active.

Returns the resolved issuer string or None if unresolvable,
and populates missing_signals / needs_followup_questions on the BFS.
"""

from typing import Optional, Tuple

from app.models.badge_fact_sheet import BadgeFactSheet


# Ordered list of (url_substring, issuer_name, rule_id)
# Checked in order — first match wins
_CRITERIA_URL_RULES: list[Tuple[str, str, str]] = [
    # IR01a — LDI production Canvas domain
    ("ldi.njit.edu", "LDI", "IR01"),
    # IR01b — LDI Canvas catalog domain
    ("njitcl.catalog.instructure.com", "LDI", "IR01"),
    # IR02 — Makerspace
    ("njitmakerspace.com", "Makerspace", "IR02"),
    # IR03 — Newark College of Engineering
    ("engineering.njit.edu", "NCE", "IR03"),
    # IR01c — LDI development / professional programs
    ("njit.edu/development", "LDI", "IR01"),
    # IR04 — Office of Global Initiatives
    ("njit.edu/global", "OGI", "IR04"),
]

# Governing office derived from issuer
_GOVERNING_OFFICE: dict[str, str] = {
    "LDI": "LDI",
    "Makerspace": "Makerspace",
    "NCE": "NCE",
    "OGI": "OGI",
    "OSIL": "OSIL",
}


def resolve_issuer(bfs: BadgeFactSheet) -> BadgeFactSheet:
    """
    Attempt to resolve bfs.issuer from bfs.criteria_id_url.

    Mutates and returns the BFS with:
    - issuer set if resolved
    - governing_office set if resolved
    - missing_signals and needs_followup_questions set if unresolvable
    """
    url = (bfs.criteria_id_url or "").lower()

    if url:
        for substring, issuer_name, rule_id in _CRITERIA_URL_RULES:
            if substring in url:
                bfs.issuer = issuer_name
                bfs.governing_office = _GOVERNING_OFFICE.get(issuer_name)
                return bfs

        # IR06 analogue — URL present but matched nothing
        if "issuer" not in bfs.missing_signals:
            bfs.missing_signals.append("issuer")
        bfs.needs_followup_questions = True
        bfs.confidence_notes = (
            f"criteria_id_url '{bfs.criteria_id_url}' did not match any known "
            "NJIT issuer domain. Human confirmation required."
        )
        return bfs

    # IR07 — no criteria_id_url at all
    if "issuer" not in bfs.missing_signals:
        bfs.missing_signals.append("issuer")
    bfs.needs_followup_questions = True
    bfs.confidence_notes = (
        "No criteria_id_url found. Cannot resolve issuer automatically. "
        "Human confirmation required before Stage 1 classification."
    )
    return bfs


def resolve_issuer_from_url(criteria_id_url: Optional[str]) -> Optional[str]:
    """
    Lightweight helper — returns just the issuer string (or None)
    without needing a full BFS. Useful in tests and scripts.
    """
    if not criteria_id_url:
        return None
    url = criteria_id_url.lower()
    for substring, issuer_name, _ in _CRITERIA_URL_RULES:
        if substring in url:
            return issuer_name
    return None
