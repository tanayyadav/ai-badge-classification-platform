"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

Stage 3 — Badge Level classification.

Determined by: Evidence, Bloom Level, and Pathway Position.
CRITICAL: Level options depend entirely on Stage 2 Type result.
Rules S3S01, S3A01–S3A14, S3SK01–S3SK05, S3C01–S3C05 from docs/taxonomy-rules.md.

Branches:
  Souvenir    → single level "Souvenir"          (S3S01)
  Achievement → Foundational | Milestone | Terminal  (S3A01-S3A14)
  Skill       → Awareness | Application | Mastery    (S3SK01-S3SK05)
  Competency  → Demonstrated | Integrated | Exemplary (S3C01-S3C05)

Returns:
    {
        "level":             str | None,
        "confidence":        "High" | "Medium" | "Low",
        "rules_triggered":   list[str],
        "level_branch_used": "souvenir" | "achievement" | "skill" | "competency",
    }
"""

from app.models.badge_fact_sheet import BadgeFactSheet

# Confidence based on signal source
def _level_conf(bfs: BadgeFactSheet) -> str:
    """High for keyword_rule / structured_field, Medium for regex/llm."""
    if bfs.level_signal_source in ("regex_pattern", "llm_extraction"):
        return "Medium"
    return "High"


def _phrase_contains(bfs: BadgeFactSheet, *keywords: str) -> bool:
    """True if level_phrase_matched contains any of the given keywords."""
    phrase = (bfs.level_phrase_matched or "").lower()
    return any(kw.lower() in phrase for kw in keywords)


def classify_stage3(bfs: BadgeFactSheet, type_result: str) -> dict:
    """
    Classify badge level by branching on the Stage 2 type result.

    CRITICAL: Level vocabularies are type-specific and must not be mixed
    (see docs/taxonomy-rules.md). Each branch is fully independent.

    Branch A — Souvenir (type_result == "Souvenir"):
      Single level "Souvenir". Always High confidence. No sub-rules needed.
      Rule: S3S01

    Branch B — Achievement (type_result == "Achievement"):
      Levels: Foundational | Milestone | Terminal
      Priority: structured canvas signals first (S3A01–S3A09), then NLP phrases
      (S3A10–S3A12), then attendance-standalone default (S3A13), else None (S3A14).
      Canvas sequence_number is the strongest signal: 0→Terminal, 1→Foundational,
      2+→Milestone. is_capstone and achievement_type=="Micro Credential" → Terminal.

    Branch C — Skill (type_result == "Skill"):
      Levels: Awareness | Application | Mastery
      Driven by Bloom's taxonomy level from BloomExtractor (Layer 3).
      High Bloom (evaluating/creating) → Mastery (S3SK01)
      Mid  Bloom (applying/analyzing)  → Application (S3SK02)
      Low  Bloom (remembering/understanding) → Awareness (S3SK03)
      Expert scored but no Bloom signal → None/Medium + missing_signals (S3SK04)

    Branch D — Competency (type_result == "Competency"):
      Levels: Demonstrated | Integrated | Exemplary
      Driven by evidence breadth and leadership signals.
      leadership_evidence or exemplary phrases → Exemplary (S3C01)
      multi_context_evidence or integrated phrases → Integrated (S3C02)
      real_world_context (single, no leadership) → Demonstrated (S3C03)
      OR criteria + real-world → Demonstrated/Medium (S3C04)

    Args:
        bfs:         Fully normalised + NLP-extracted BadgeFactSheet.
        type_result: Stage 2 output — "Souvenir" | "Achievement" |
                     "Skill" | "Competency" | None.
    """
    if type_result == "Souvenir":
        return _branch_souvenir()

    if type_result == "Achievement":
        return _branch_achievement(bfs)

    if type_result == "Skill":
        return _branch_skill(bfs)

    if type_result == "Competency":
        return _branch_competency(bfs)

    # type_result is None — cannot branch
    return {
        "level": None,
        "confidence": "Low",
        "rules_triggered": [],
        "level_branch_used": None,
    }


# ---------------------------------------------------------------------------
# Branch A — Souvenir (S3S01)
# ---------------------------------------------------------------------------

def _branch_souvenir() -> dict:
    return {
        "level": "Souvenir",
        "confidence": "High",
        "rules_triggered": ["S3S01"],
        "level_branch_used": "souvenir",
    }


# ---------------------------------------------------------------------------
# Branch B — Achievement (S3A01–S3A14)
# ---------------------------------------------------------------------------

def _branch_achievement(bfs: BadgeFactSheet) -> dict:
    rules: list[str] = []

    # S3A01 — Micro Credential or is_capstone → Terminal
    if bfs.achievement_type == "Micro Credential" or bfs.is_capstone:
        return _ach("Terminal", "High", ["S3A01"])

    # S3A02 — Canvas sequence 00 → Terminal
    if bfs.canvas_sequence_number == 0:
        return _ach("Terminal", "High", ["S3A02"])

    # S3A03 — Has prereqs AND capstone/culminating title or phrase
    if bfs.has_prerequisite_badges and (
        "capstone" in (bfs.badge_title or "").lower()
        or _phrase_contains(bfs, "culminating", "after completing")
    ):
        return _ach("Terminal", "High", ["S3A03"])

    # S3A04 — OSIL + "Capstone" in title
    if bfs.issuer == "OSIL" and "capstone" in (bfs.badge_title or "").lower():
        return _ach("Terminal", "High", ["S3A04"])

    # S3A05 — Canvas sequence 01 → Foundational
    if bfs.canvas_sequence_number == 1:
        return _ach("Foundational", "High", ["S3A05"])

    # S3A06 — Canvas sequence 02 → Milestone
    if bfs.canvas_sequence_number == 2:
        return _ach("Milestone", "High", ["S3A06"])

    # S3A07 — Canvas sequence 03 in pathway of length 3 or 4 → Milestone
    if bfs.canvas_sequence_number == 3 and bfs.canvas_pathway_length in (3, 4):
        return _ach("Milestone", "High", ["S3A07"])

    # S3A08 — Canvas sequence 04 → Milestone
    if bfs.canvas_sequence_number == 4:
        return _ach("Milestone", "High", ["S3A08"])

    # S3A09 — Has prereqs but no terminal signal → Milestone
    if bfs.has_prerequisite_badges:
        return _ach("Milestone", "High", ["S3A09"])

    # S3A10 — Self-declared Foundational or matched foundational phrase
    if bfs.self_declared_level in ("Foundational", "Foundation"):
        return _ach("Foundational", _level_conf(bfs), ["S3A10"])

    # S3A11 — Self-declared Milestone or matched milestone phrase
    if bfs.self_declared_level == "Milestone":
        return _ach("Milestone", _level_conf(bfs), ["S3A11"])

    # S3A12 — Self-declared Terminal or matched terminal phrase
    if bfs.self_declared_level == "Terminal":
        return _ach("Terminal", _level_conf(bfs), ["S3A12"])

    # S3A13 — Attendance-only standalone badge → Foundational default
    if bfs.assessment_type == "attendance" and bfs.pathway_position == "Standalone":
        return _ach("Foundational", "Medium", ["S3A13"])

    # S3A14 — No rule matched
    return {
        "level": None,
        "confidence": "Low",
        "rules_triggered": ["S3A14"],
        "level_branch_used": "achievement",
    }


def _ach(level: str, conf: str, rules: list[str]) -> dict:
    return {
        "level": level,
        "confidence": conf,
        "rules_triggered": rules,
        "level_branch_used": "achievement",
    }


# ---------------------------------------------------------------------------
# Branch C — Skill (S3SK01–S3SK05)
# ---------------------------------------------------------------------------

_MASTERY_PHRASES = {
    "mastery", "fluency", "independent problem-solving",
    "peer coaching", "mentor", "expert-scored capstone",
}

_APPLICATION_PHRASES = {
    "demonstrate", "apply", "hands-on", "perform",
    "simulation", "evaluated artifact", "live demonstration",
}

_AWARENESS_PHRASES = {
    "basic understanding", "awareness", "identify",
    "knowledge check", "concept map", "oral explanation",
}


def _branch_skill(bfs: BadgeFactSheet) -> dict:

    # S3SK01 — High Bloom OR project presentation w/ expert + mastery phrase
    if bfs.bloom_level in ("evaluating", "creating"):
        return _sk("Mastery", "High", ["S3SK01"])
    if (
        bfs.assessment_type == "project_presentation"
        and bfs.assessment_evaluator == "expert_scored"
        and _phrase_contains(bfs, *_MASTERY_PHRASES)
    ):
        return _sk("Mastery", "High", ["S3SK01"])

    # S3SK02 — Mid Bloom OR practical/portfolio w/ expert + application phrase
    if bfs.bloom_level in ("applying", "analyzing"):
        return _sk("Application", "High", ["S3SK02"])
    if (
        bfs.assessment_type in ("practical", "portfolio", "rubric")
        and bfs.assessment_evaluator == "expert_scored"
        and _phrase_contains(bfs, *_APPLICATION_PHRASES)
    ):
        return _sk("Application", "High", ["S3SK02"])

    # S3SK03 — Low Bloom OR quiz w/ expert + awareness phrase
    if bfs.bloom_level in ("remembering", "understanding"):
        return _sk("Awareness", "High", ["S3SK03"])
    if (
        bfs.assessment_type in ("quiz", "knowledge_checks")
        and bfs.assessment_evaluator == "expert_scored"
        and _phrase_contains(bfs, *_AWARENESS_PHRASES)
    ):
        return _sk("Awareness", "High", ["S3SK03"])

    # S3SK04 — Expert scored but no Bloom signal
    if bfs.assessment_evaluator == "expert_scored" and bfs.bloom_level is None:
        if "bloom_level" not in bfs.missing_signals:
            bfs.missing_signals.append("bloom_level")
        bfs.needs_followup_questions = True
        return {
            "level": None,
            "confidence": "Medium",
            "rules_triggered": ["S3SK04"],
            "level_branch_used": "skill",
        }

    # S3SK05 — No rule matched
    return {
        "level": None,
        "confidence": "Low",
        "rules_triggered": ["S3SK05"],
        "level_branch_used": "skill",
    }


def _sk(level: str, conf: str, rules: list[str]) -> dict:
    return {
        "level": level,
        "confidence": conf,
        "rules_triggered": rules,
        "level_branch_used": "skill",
    }


# ---------------------------------------------------------------------------
# Branch D — Competency (S3C01–S3C05)
# ---------------------------------------------------------------------------

_EXEMPLARY_PHRASES = {
    "mentor", "leads", "drives innovation", "models",
    "strategic leadership", "360 feedback",
    "organizational impact", "innovation to market",
}

_INTEGRATED_PHRASES = {
    "across domains", "across settings", "cross-context",
    "multiple stakeholder", "adaptability and autonomy",
    "multiple contexts", "full-scope",
}


def _branch_competency(bfs: BadgeFactSheet) -> dict:

    # S3C01 — Leadership evidence OR exemplary phrase
    if bfs.leadership_evidence or _phrase_contains(bfs, *_EXEMPLARY_PHRASES):
        return _comp("Exemplary", "High", ["S3C01"])

    # S3C02 — Multi-context evidence OR integrated phrase
    if bfs.multi_context_evidence or _phrase_contains(bfs, *_INTEGRATED_PHRASES):
        return _comp("Integrated", "High", ["S3C02"])

    # S3C03 — Real-world context, single (not multi), no leadership
    if bfs.real_world_context and not bfs.multi_context_evidence and not bfs.leadership_evidence:
        return _comp("Demonstrated", "High", ["S3C03"])

    # S3C04 — OR criteria + real-world → Demonstrated (lower confidence)
    if bfs.criteria_logic == "OR" and bfs.real_world_context:
        return _comp("Demonstrated", "Medium", ["S3C04"])

    # S3C05 — No rule matched
    bfs.needs_followup_questions = True
    return {
        "level": None,
        "confidence": "Low",
        "rules_triggered": ["S3C05"],
        "level_branch_used": "competency",
    }


def _comp(level: str, conf: str, rules: list[str]) -> dict:
    return {
        "level": level,
        "confidence": conf,
        "rules_triggered": rules,
        "level_branch_used": "competency",
    }
