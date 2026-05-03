"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

OBv version detector.

IMPORTANT UPDATE: All NJIT badges are now OBv3 format only.
OBv2 is no longer supported. This module validates that the
input is OBv3 and raises ValueError on anything else.
"""


OBV3_CONTEXT_MARKER = "purl.imsglobal.org/spec/ob/v3p0"
OBV2_CONTEXT_MARKER = "w3id.org/openbadges/v2"


def detect_obv_version(json_data: dict) -> int:
    """
    Return the OBv version number (always 3 for NJIT badges).

    Raises ValueError if:
    - @context is missing
    - @context indicates OBv2 (no longer supported)
    - @context is an unrecognised format
    """
    context = json_data.get("@context", "")

    # @context may be a list (OBv3 allows it) — join to a single string for matching
    if isinstance(context, list):
        context = " ".join(context)

    if OBV3_CONTEXT_MARKER in context:
        return 3

    if OBV2_CONTEXT_MARKER in context:
        raise ValueError(
            "OBv2 badges are no longer supported. "
            "Please convert to OBv3 format before submitting."
        )

    if not context:
        raise ValueError(
            "Missing @context field. Cannot determine badge format. "
            "Expected OBv3 context URL."
        )

    raise ValueError(
        f"Unrecognised @context value: '{context}'. "
        "Expected OBv3 context (purl.imsglobal.org/spec/ob/v3p0/...)."
    )
