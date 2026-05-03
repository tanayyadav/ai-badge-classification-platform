"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Stage 2 — Badge Type classification.

Determined by: Earning Criteria and Assessment.
Rules S2R01–S2R11 from docs/taxonomy-rules.md.
CRITICAL: Run in listed order. First match wins.

Returns:
    {
        "type":            str | None,
        "confidence":      "High" | "Medium" | "Low",
        "rules_triggered": list[str],
    }
"""

from app.models.badge_fact_sheet import BadgeFactSheet

# assessment_type values that indicate a structured module/course completion
_MODULE_ASSESSMENT_TYPES = {"module_completion", "final_assessment", "knowledge_checks", "pre_post_assessment"}


def classify_stage2(bfs: BadgeFactSheet) -> dict:
    """
    Classify badge type using S2R01–S2R11 (docs/taxonomy-rules.md).

    Rules run in listed order; first match wins.

    The critical Skill vs Achievement distinction hinges on two fields:
      - assessment_evaluator == "expert_scored"  →  human expert grades the work
      - expert_evaluation_required == True        →  confirms human review is mandatory

    When either is True (and assessment_type is not pre_post_assessment), S2R06
    fires and returns Skill. When assessment is required but evaluator is unknown,
    S2R07 fires and returns Achievement/Medium with a flag:
    "Skill possible — confirm assessment_evaluator". This flag propagates to the
    engine, which adds "assessment_evaluator" to bfs.missing_signals.

    Type selection decision path:
      achievement_type == "Micro Credential"       → S2R01 → Achievement (Terminal in S3)
      achievement_type == "Competency"             → S2R02 → Competency
      achievement_type == "Certificate of Comp."   → S2R03 → Achievement (entry)
      badge_purpose == "compliance"                → S2R04 → Achievement
      no assessment / attendance only              → S2R05 → Souvenir
      expert_evaluation_required or expert_scored  → S2R06 → Skill
      ksa_dimensions present OR real-world + OR    → S2R08 → Competency/Medium
      canvas code OR module assessment type        → S2R09 → Achievement
      OSIL + pre_post_assessment                   → S2R10 → Achievement
      assessment required, evaluator unknown       → S2R07 → Achievement/Medium (flag)
      nothing matched                              → S2R11 → None/Low

    Mutates nothing on the BFS — pure function.
    """
    criteria_lower = (bfs.earning_criteria_text or "").lower()

    # ------------------------------------------------------------------
    # S2R01 — Micro Credential → Achievement (Terminal in Stage 3)
    # ------------------------------------------------------------------
    if bfs.achievement_type == "Micro Credential":
        return {
            "type": "Achievement",
            "confidence": "High",
            "rules_triggered": ["S2R01"],
        }

    # ------------------------------------------------------------------
    # S2R02 — Competency achievement type → Competency
    # ------------------------------------------------------------------
    if bfs.achievement_type == "Competency":
        return {
            "type": "Competency",
            "confidence": "High",
            "rules_triggered": ["S2R02"],
        }

    # ------------------------------------------------------------------
    # S2R03 — Certificate of Completion → Achievement (entry level)
    # ------------------------------------------------------------------
    if bfs.achievement_type == "Certificate Of Completion":
        return {
            "type": "Achievement",
            "confidence": "High",
            "rules_triggered": ["S2R03"],
        }

    # ------------------------------------------------------------------
    # S2R04 — Compliance badge → Achievement
    # ------------------------------------------------------------------
    if (
        bfs.badge_purpose == "compliance"
        or "mandatory to apply" in criteria_lower
        or "required to apply" in criteria_lower
    ):
        return {
            "type": "Achievement",
            "confidence": "High",
            "rules_triggered": ["S2R04"],
        }

    # ------------------------------------------------------------------
    # S2R05 — No assessment → Souvenir
    # ------------------------------------------------------------------
    if (
        bfs.assessment_required == "no"
        or bfs.assessment_type == "attendance"
        or (bfs.criteria_id_url and "badgr.com/claim" in bfs.criteria_id_url)
    ):
        return {
            "type": "Souvenir",
            "confidence": "High",
            "rules_triggered": ["S2R05"],
        }

    # ------------------------------------------------------------------
    # S2R06 — Expert evaluation present → Skill
    # Simplified per Phase 5 spec: expert_evaluation_required OR expert_scored
    # ------------------------------------------------------------------
    if (
        (bfs.expert_evaluation_required or bfs.assessment_evaluator == "expert_scored")
        and bfs.assessment_type != "pre_post_assessment"
    ):
        return {
            "type": "Skill",
            "confidence": "High",
            "rules_triggered": ["S2R06"],
        }

    # ------------------------------------------------------------------
    # S2R08 — KSA dimensions present OR real-world OR criteria logic suggests
    # ------------------------------------------------------------------
    if bfs.ksa_dimensions:
        return {
            "type": "Competency",
            "confidence": "Medium",
            "rules_triggered": ["S2R08"],
        }
    if (
        bfs.real_world_context
        and bfs.criteria_logic in ("OR", "mixed")
        and bfs.achievement_type is None
    ):
        return {
            "type": "Competency",
            "confidence": "Medium",
            "rules_triggered": ["S2R08"],
        }

    # ------------------------------------------------------------------
    # S2R06b — Makerspace issuer + hands-on evidence → Skill
    # Makerspace badges with practical/in-person/expert-evaluated criteria
    # are almost always Skill type. This fires before S2R09 so that a
    # practical assessment_type does not fall through to Achievement.
    # ------------------------------------------------------------------
    if bfs.issuer == "Makerspace" and (
        bfs.assessment_type == "practical"
        or bfs.expert_evaluation_required
        or "in-person" in (bfs.earning_criteria_text or "").lower()
        or "in person" in (bfs.earning_criteria_text or "").lower()
    ):
        return {
            "type": "Skill",
            "confidence": "High",
            "rules_triggered": ["S2R06b"],
        }

    # ------------------------------------------------------------------
    # S2R09 — Canvas course code OR module-style assessment → Achievement
    # Moved before S2R07: canvas code / structured assessment type gives
    # enough signal to commit to Achievement at High confidence.
    # ------------------------------------------------------------------
    if bfs.canvas_course_code or bfs.assessment_type in _MODULE_ASSESSMENT_TYPES:
        return {
            "type": "Achievement",
            "confidence": "High",
            "rules_triggered": ["S2R09"],
        }

    # ------------------------------------------------------------------
    # S2R10 — OSIL + pre/post assessment → Achievement
    # Moved before S2R07 for same reason: specific enough to be High.
    # ------------------------------------------------------------------
    if bfs.issuer == "OSIL" and bfs.assessment_type == "pre_post_assessment":
        return {
            "type": "Achievement",
            "confidence": "High",
            "rules_triggered": ["S2R10"],
        }

    # ------------------------------------------------------------------
    # S2R07 — Assessment required but evaluator unknown → Achievement/Medium
    # "Skill possible — confirm assessment_evaluator"
    # Only reaches here when no canvas code / structured type matched above.
    # ------------------------------------------------------------------
    if bfs.assessment_required == "yes" and bfs.assessment_evaluator is None:
        return {
            "type": "Achievement",
            "confidence": "Medium",
            "rules_triggered": ["S2R07"],
            "flag": "Skill possible — confirm assessment_evaluator",
        }

    # ------------------------------------------------------------------
    # S2R08b — OR criteria + real-world context → Competency/Medium
    # Catches badges where achievement_type is not explicitly "Competency"
    # but the criteria pattern clearly indicates competency-style evaluation.
    # Placed before S2R11 so it is a positive signal, not a fallback.
    # ------------------------------------------------------------------
    _RW_PHRASES = (
        "internship", "startup", "pitch", "hackathon",
        "competition", "real-world", "launched", "founded",
    )
    if bfs.criteria_logic == "OR" and (
        bfs.real_world_context
        or any(p in criteria_lower for p in _RW_PHRASES)
    ):
        return {
            "type": "Competency",
            "confidence": "Medium",
            "rules_triggered": ["S2R08b"],
            "flag": (
                "OR-based real-world criteria suggests Competency type "
                "— reviewer should confirm"
            ),
        }

    # ------------------------------------------------------------------
    # S2R11d — Issuer-based type defaults when all signal rules failed.
    # Applied immediately before the Unknown fallback so any positive
    # assessment signal above still takes precedence.
    # ------------------------------------------------------------------
    _ISSUER_DEFAULTS: dict[str, tuple[str, str]] = {
        "OSIL":       ("Achievement", "Defaulted based on OSIL issuer pattern"),
        "LDI":        ("Achievement", "Defaulted based on LDI issuer pattern"),
        "OGI":        ("Achievement", "Defaulted based on OGI issuer pattern"),
        "Makerspace": ("Skill",       "Defaulted based on Makerspace issuer pattern"),
    }
    if bfs.issuer in _ISSUER_DEFAULTS:
        _default_type, _default_note = _ISSUER_DEFAULTS[bfs.issuer]
        return {
            "type": _default_type,
            "confidence": "Medium",
            "rules_triggered": ["S2R11d"],
            "flag": _default_note,
        }

    # ------------------------------------------------------------------
    # S2R11 — No rule matched
    # ------------------------------------------------------------------
    return {
        "type": None,
        "confidence": "Low",
        "rules_triggered": ["S2R11"],
    }
