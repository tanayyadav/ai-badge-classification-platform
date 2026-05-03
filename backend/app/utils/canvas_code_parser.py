"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Canvas course code parser.

Parses codes in the format PREFIX.PATHWAY_NUM.SEQUENCE_NUM
e.g. "MCAI.002.03"

Sequence numbers:
  00 → Capstone / Micro Credential (Terminal)
  01 → First course  (Foundational)
  02 → Second course (Milestone)
  03 → Third course  (Milestone)
  04 → Fourth course (Milestone)

Defined in docs/taxonomy-rules.md.
"""

from typing import Optional

# Known subject domain prefixes
_SUBJECT_DOMAINS: dict[str, str] = {
    "MCAI": "AI / Education",
    "MCHC": "Healthcare / Project Management",
}


def parse_canvas_code(code: Optional[str]) -> dict:
    """
    Parse a Canvas course code into its components.

    Returns an empty dict if the code is None, empty, or malformed.

    Example:
        parse_canvas_code("MCAI.002.03")
        → {
            "canvas_course_code":    "MCAI.002.03",
            "canvas_pathway_code":   "MCAI.002",
            "canvas_sequence_number": 3,
            "is_capstone":           False,
            "subject_domain":        "AI / Education",
          }

        parse_canvas_code("MCAI.002.00")
        → { ..., "canvas_sequence_number": 0, "is_capstone": True, ... }
    """
    if not code or "." not in code:
        return {}

    parts = code.strip().split(".")
    if len(parts) != 3:
        return {}

    prefix, pathway_num, sequence_raw = parts

    # Sequence must be a zero-padded integer
    if not sequence_raw.isdigit():
        return {}

    sequence_num = int(sequence_raw)

    return {
        "canvas_course_code": code.strip(),
        "canvas_pathway_code": f"{prefix}.{pathway_num}",
        "canvas_sequence_number": sequence_num,
        "is_capstone": sequence_num == 0,
        "subject_domain": _SUBJECT_DOMAINS.get(prefix, "Unknown"),
    }
