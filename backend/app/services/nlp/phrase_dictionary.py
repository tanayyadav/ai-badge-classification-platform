"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

NLP Layer 1 — Exact phrase matching.

All phrases are case-insensitive exact substring matches.
Dictionaries are from docs/nlp-phrase-dictionary.md — do not modify without
updating docs/nlp-phrase-dictionary.md.

PhraseExtractor applies all dictionaries to a BFS and returns
the updated BFS with signal fields populated.

Matching rules:
- Phrases are sorted longest-first so the most specific phrase wins.
  ("foundation-level badge" beats "foundation-level")
- For LEVEL_PHRASES: word-boundary matching (EC17); negation-aware (EC18);
  all matches collected to detect conflicts (EC19); first non-negated
  match (longest) wins.
- For ASSESSMENT_PHRASES: multiple matches allowed (type + threshold).
- For AUDIENCE_PHRASES: first match wins.
- For PURPOSE_PHRASES: multiple matches allowed (purpose + workflow).
"""

import re

from app.models.badge_fact_sheet import BadgeFactSheet

# ---------------------------------------------------------------------------
# EC18 — Negation words checked before a matched level phrase
# ---------------------------------------------------------------------------
NEGATION_WORDS: frozenset[str] = frozenset([
    "not", "no", "never", "without", "non",
    "doesn't", "don't", "isn't", "aren't", "wasn't", "weren't",
    "cannot", "can't", "couldn't", "won't", "wouldn't",
])


def phrase_matches(phrase: str, text: str) -> "re.Match[str] | None":
    """
    EC17 — Word-boundary-aware matching for level phrases.

    Returns the first Match object if `phrase` appears in `text` as a
    whole-word sequence (\\b anchors on both ends), else None.
    Always case-insensitive.
    """
    pattern = r'\b' + re.escape(phrase) + r'\b'
    return re.search(pattern, text, re.IGNORECASE)


def is_negated(text: str, match_start: int, window: int = 10) -> bool:
    """
    EC18 — Negation detection.

    Inspects the `window` words immediately before `match_start` in `text`.
    Returns True if any negation word is found in that window.
    Punctuation attached to words is stripped before comparison.
    """
    prefix = text[:match_start]
    words = prefix.split()
    recent = words[-window:]
    return any(w.strip(".,;:!?\"'()") in NEGATION_WORDS for w in recent)


# ---------------------------------------------------------------------------
# Past-context blocking — prevents level phrases from firing when the phrase
# appears as a description of a prerequisite or already-completed activity
# rather than as a declaration of the badge's own level.
#
# Example blocked:
#   "students who have already completed the introductory series"
#   → "introductory" is a past-completed thing, not this badge's level.
# ---------------------------------------------------------------------------
PAST_CONTEXT_WORDS: list[str] = [
    "completed", "finishing", "finished", "already",
    "done with", "having finished", "after completing",
    "having completed",
    # "who have/has" alone is too broad — "who have never done" is a beginner
    # audience description, not a past-completion context. Use specific forms.
    "who have already", "who have completed", "who have finished",
    "who has already", "who has completed", "who has finished",
]


def is_past_context(text: str, match_start: int, window: int = 8) -> bool:
    """
    Past-context detection.

    Inspects the `window` words immediately before `match_start` in `text`.
    Returns True if any past-context phrase appears in that window, indicating
    the level phrase describes a completed prerequisite rather than this badge.
    Multi-word phrases are checked against the joined window string so that
    "who have" and "after completing" are detected correctly.
    """
    words_before = text[:match_start].split()
    recent_words = [w.lower().strip(".,;:!?\"'()") for w in words_before[-window:]]
    joined = " ".join(recent_words)
    return any(past in joined for past in PAST_CONTEXT_WORDS)


# ---------------------------------------------------------------------------
# LEVEL_PHRASES
# Tuple: (level_value, confidence)
# ---------------------------------------------------------------------------
LEVEL_PHRASES: dict[str, tuple[str, str]] = {
    # Foundational
    "foundation-level badge":            ("Foundational", "High"),
    "this foundation-level":             ("Foundational", "High"),
    "foundation-level":                  ("Foundational", "High"),
    "foundation level":                  ("Foundational", "High"),
    "foundational understanding":        ("Foundational", "High"),
    "foundational knowledge":            ("Foundational", "High"),
    "lays the groundwork":               ("Foundational", "High"),
    "build essential":                   ("Foundational", "High"),
    "equips emerging leaders":           ("Foundational", "High"),
    "readiness to begin":                ("Foundational", "High"),
    "introduction to":                   ("Foundational", "Medium"),
    "introductory":                      ("Foundational", "High"),
    "beginner":                          ("Foundational", "High"),
    "entry-level":                       ("Foundational", "High"),
    "entry level":                       ("Foundational", "High"),
    "no prior experience":               ("Foundational", "High"),
    "no experience required":            ("Foundational", "High"),
    "getting started":                   ("Foundational", "Medium"),
    "first step":                        ("Foundational", "Medium"),
    "fundamentals of":                   ("Foundational", "High"),
    "basics of":                         ("Foundational", "Medium"),
    "first in":                          ("Foundational", "Medium"),
    "first course":                      ("Foundational", "High"),
    # Conversational / plain-language Foundational phrases
    "never done this before":            ("Foundational", "High"),
    "beginning of the journey":          ("Foundational", "Medium"),
    "starting their journey":            ("Foundational", "Medium"),
    "starting point":                    ("Foundational", "Medium"),
    "entry point":                       ("Foundational", "Medium"),
    "getting started with":              ("Foundational", "Medium"),
    "just beginning to":                 ("Foundational", "Medium"),
    "just starting":                     ("Foundational", "Medium"),
    "new to this":                       ("Foundational", "Medium"),
    "first time":                        ("Foundational", "Medium"),

    # Milestone
    "building on foundational concepts": ("Milestone", "High"),
    "building on the foundational series": ("Milestone", "High"),
    "building on foundational":          ("Milestone", "High"),
    "expanding on the foundational series": ("Milestone", "High"),
    "expanding on the foundational":     ("Milestone", "High"),
    "intermediate-level":                ("Milestone", "High"),
    "intermediate credential":           ("Milestone", "High"),
    "intermediate level":                ("Milestone", "High"),
    "deepens skills":                    ("Milestone", "High"),
    "deepens understanding":             ("Milestone", "High"),
    "advances skills":                   ("Milestone", "High"),
    "builds upon":                       ("Milestone", "High"),
    "prior knowledge required":          ("Milestone", "High"),
    "second course":                     ("Milestone", "High"),
    "second in":                         ("Milestone", "High"),
    "continues from":                    ("Milestone", "High"),
    # Plain-language Milestone phrases
    "more advanced than the first":      ("Milestone", "High"),
    "second part":                       ("Milestone", "High"),
    "building on what":                  ("Milestone", "Medium"),
    "continuing from":                   ("Milestone", "Medium"),
    "following up on":                   ("Milestone", "Medium"),
    "taking it further":                 ("Milestone", "Medium"),
    "next step":                         ("Milestone", "Medium"),

    # Terminal
    "after completing the foundational and intermediate": ("Terminal", "High"),
    "comprehensive foundational understanding across all": ("Terminal", "High"),
    "comprehensive achievement":         ("Terminal", "High"),
    "demonstrates comprehensive":        ("Terminal", "High"),
    "demonstrates mastery":              ("Terminal", "High"),
    "completion of all":                 ("Terminal", "High"),
    "upon completing all":               ("Terminal", "High"),
    "culminating the":                   ("Terminal", "High"),
    "completes the series":              ("Terminal", "High"),
    "final course":                      ("Terminal", "High"),
    "capstone":                          ("Terminal", "High"),
    # Plain-language Terminal phrases
    "everything comes together":         ("Terminal", "High"),
    "putting it all together":           ("Terminal", "High"),
    "completing the program":            ("Terminal", "High"),
    "finishing the series":              ("Terminal", "High"),
    "end of the program":                ("Terminal", "High"),
    "last course":                       ("Terminal", "High"),
    "final step":                        ("Terminal", "Medium"),
    "the last thing needed":             ("Terminal", "Medium"),
}

# Pre-sorted: longest phrase first so the most specific match wins
_LEVEL_PHRASES_SORTED: list[tuple[str, str, str]] = sorted(
    ((phrase, level, conf) for phrase, (level, conf) in LEVEL_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# ASSESSMENT_PHRASES
# Tuple: (type_key, threshold_or_None, confidence)
#
# type_key values and how they're used:
#   "final_assessment" | "knowledge_checks" | "pre_post_assessment" |
#   "project_presentation" | "attendance" | "module_completion" | "practical"
#     → sets assessment_type
#   "expert_scored"
#     → sets assessment_evaluator
#   "compliance"
#     → sets badge_purpose (handled also by PURPOSE_PHRASES)
#   "downstream_workflow"
#     → signals a downstream workflow exists (handled also by PURPOSE_PHRASES)
# ---------------------------------------------------------------------------
ASSESSMENT_PHRASES: dict[str, tuple[str, str | None, str]] = {
    # ---- Final assessment — original strict phrases ----
    "passing the final assessment with an 80% or higher": ("final_assessment", "80%", "High"),
    "passing the final assessment with an 90% or higher": ("final_assessment", "90%", "High"),

    # ---- Final assessment — flexible "pass the/a final X with Y%" variants ----
    # Longer phrases first so the most specific match wins in sorted order.
    "pass the final assessment with 80%":  ("final_assessment", "80%", "High"),
    "pass the final assessment with 90%":  ("final_assessment", "90%", "High"),
    "pass a final assessment with 80%":    ("final_assessment", "80%", "High"),
    "pass a final assessment with 90%":    ("final_assessment", "90%", "High"),
    "pass the final quiz with 80%":        ("final_assessment", "80%", "High"),
    "pass the final exam with 80%":        ("final_assessment", "80%", "High"),

    # ---- Score + explicit percentage ----
    "80% or higher to earn":               ("final_assessment", "80%", "High"),
    "80% or better":                       ("final_assessment", "80%", "High"),
    "90% or higher to earn":               ("final_assessment", "90%", "High"),
    "90% or better":                       ("final_assessment", "90%", "High"),
    "score 80% or higher":                 ("final_assessment", "80%", "High"),
    "score 90% or higher":                 ("final_assessment", "90%", "High"),
    "score of 80":                         ("final_assessment", "80%", "High"),
    "score of 90":                         ("final_assessment", "90%", "High"),

    # Short bare-percentage phrases — lower specificity, useful as fallback.
    # Longer phrases above will win when both appear in the same text.
    "90% or higher":                       ("final_assessment", "90%", "High"),
    "80% or higher":                       ("final_assessment", "80%", "High"),

    # ---- Knowledge checks ----
    "passing knowledge checks with an 80% or higher":    ("knowledge_checks", "80%", "High"),
    "passing knowledge checks with a 80% or higher":     ("knowledge_checks", "80%", "High"),

    # ---- Pre/post assessments ----
    "pre- and post-assessment":  ("pre_post_assessment", None, "High"),
    "pre and post assessment":   ("pre_post_assessment", None, "High"),

    # ---- Project / presentation ----
    "capstone project and present": ("project_presentation", None, "High"),

    # ---- Attendance ----
    "attend all sessions":        ("attendance", None, "High"),
    "attend the full":            ("attendance", None, "High"),
    "attended the full":          ("attendance", None, "High"),
    "full attendance":            ("attendance", None, "High"),

    # ---- Compliance / downstream ----
    "mandatory to apply":         ("compliance", None, "High"),
    "required to apply":          ("compliance", None, "High"),
    "share their digital badge to": ("downstream_workflow", None, "High"),

    # ---- Module / practical ----
    "module quizzes":             ("module_completion", None, "Medium"),
    "in person practical":        ("practical", None, "High"),
    "in-person practical":        ("practical", None, "High"),

    # ---- Expert scored ----
    "expert-verified":            ("expert_scored", None, "High"),
    "graded by instructor":       ("expert_scored", None, "High"),
    "reviewed by mentor":         ("expert_scored", None, "High"),
    "evaluated by":               ("expert_scored", None, "Medium"),
    "assessed by":                ("expert_scored", None, "Medium"),
}

_ASSESSMENT_PHRASES_SORTED: list[tuple[str, str, str | None, str]] = sorted(
    ((phrase, type_key, threshold, conf)
     for phrase, (type_key, threshold, conf) in ASSESSMENT_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)

# Valid assessment_type values (not special-case signals)
_ASSESSMENT_TYPE_VALUES = {
    "final_assessment", "knowledge_checks", "pre_post_assessment",
    "project_presentation", "attendance", "module_completion", "practical",
}


# ---------------------------------------------------------------------------
# AUDIENCE_PHRASES
# Tuple: (audience_type, audience_signal_detail, confidence)
# ---------------------------------------------------------------------------
AUDIENCE_PHRASES: dict[str, tuple[str, str | None, str]] = {
    "faculty and instructors":    ("njit_employee", "faculty", "High"),
    "healthcare professional":    ("external_professional", "healthcare", "High"),
    "f-1 international students": ("njit_student", "international", "High"),
    "f-1 students":               ("njit_student", "international", "High"),
    "working professionals":      ("external_professional", "professional", "High"),
    "international students":     ("njit_student", "international", "High"),
    "njit employees":             ("njit_employee", "staff", "High"),
    "njit students":              ("njit_student", "student", "High"),
    "njit staff":                 ("njit_employee", "staff", "High"),
    "in partnership with":        ("external_partner", None, "High"),
    "workforce":                  ("external_professional", "professional", "Medium"),
    "industry":                   ("external_professional", "professional", "Medium"),
    "clinical":                   ("external_professional", "healthcare", "Medium"),
    "instructor":                 ("njit_employee", "faculty", "Medium"),
    "educator":                   ("njit_employee", "faculty", "Medium"),
    "faculty":                    ("njit_employee", "faculty", "Medium"),
    "students":                   ("njit_student", "student", "Low"),
}

_AUDIENCE_PHRASES_SORTED: list[tuple[str, str, str | None, str]] = sorted(
    ((phrase, aud_type, detail, conf)
     for phrase, (aud_type, detail, conf) in AUDIENCE_PHRASES.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# PURPOSE_PHRASES
# Maps phrase → badge_purpose value or "downstream_workflow" sentinel
# ---------------------------------------------------------------------------
PURPOSE_PHRASES: dict[str, str] = {
    "mandatory to apply":          "compliance",
    "required to apply":           "compliance",
    "prerequisite for":            "prerequisite_gate",
    "required before":             "prerequisite_gate",
    "share their digital badge to": "downstream_workflow",
    "share your badge to":         "downstream_workflow",
}

_PURPOSE_PHRASES_SORTED: list[tuple[str, str]] = sorted(
    PURPOSE_PHRASES.items(),
    key=lambda x: len(x[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# PhraseExtractor — applies all four dictionaries to a BFS
# ---------------------------------------------------------------------------

class PhraseExtractor:
    """
    Layer 1: case-insensitive exact phrase matching.

    Operates on the concatenation of badge_description and
    earning_criteria_text — the same text surface used by all NLP layers.
    """

    def extract(self, bfs: BadgeFactSheet, text: str) -> BadgeFactSheet:
        lower = text.lower()

        bfs = self._extract_level(bfs, lower)
        bfs = self._extract_assessment(bfs, lower, text)
        bfs = self._extract_audience(bfs, lower)
        bfs = self._extract_purpose(bfs, lower, text)

        return bfs

    # ------------------------------------------------------------------
    # Level signals
    # ------------------------------------------------------------------

    def _extract_level(self, bfs: BadgeFactSheet, lower: str) -> BadgeFactSheet:
        """
        EC17: Word-boundary matching (phrase_matches) instead of substring.
        EC18: Skip negated phrase matches (is_negated).
        EC19: Collect all non-negated matches; detect conflicting levels and
              record them in confidence_notes; first (longest/highest-priority)
              match still wins.
        """
        if bfs.self_declared_level is not None:
            # Already set by a structured field — don't overwrite
            return bfs

        all_matches: list[tuple[str, str, str]] = []  # (level, phrase, conf)

        for phrase, level, conf in _LEVEL_PHRASES_SORTED:
            m = phrase_matches(phrase, lower)   # EC17 — word boundary
            if m is None:
                continue
            if is_negated(lower, m.start()):    # EC18 — skip negated
                continue
            if is_past_context(lower, m.start()):  # skip past-completion context
                continue
            all_matches.append((level, phrase, conf))

        if not all_matches:
            return bfs

        # EC19 — detect conflicting level signals
        seen_levels: list[str] = []
        for lvl, _, _ in all_matches:
            if lvl not in seen_levels:
                seen_levels.append(lvl)
        if len(seen_levels) > 1:
            conflict_note = (
                f"CONFLICT: multiple level signals detected: {', '.join(seen_levels)}"
            )
            bfs.confidence_notes = (
                (bfs.confidence_notes or "") + f" | {conflict_note}"
            ).lstrip(" |").strip()

        # Use the highest-priority match (longest phrase wins — list is sorted)
        best_level, best_phrase, _ = all_matches[0]
        bfs.self_declared_level = best_level
        bfs.level_phrase_matched = best_phrase
        bfs.level_signal_source = "keyword_rule"

        return bfs

    # ------------------------------------------------------------------
    # Assessment signals
    # ------------------------------------------------------------------

    def _extract_assessment(
        self, bfs: BadgeFactSheet, lower: str, original: str
    ) -> BadgeFactSheet:
        """Multiple matches allowed — sets type, threshold, evaluator."""
        for phrase, type_key, threshold, _ in _ASSESSMENT_PHRASES_SORTED:
            if phrase.lower() not in lower:
                continue

            if type_key in _ASSESSMENT_TYPE_VALUES:
                if bfs.assessment_type is None:
                    bfs.assessment_type = type_key
                    bfs.assessment_required = "yes" if type_key != "attendance" else "no"
                if threshold and bfs.assessment_pass_threshold is None:
                    bfs.assessment_pass_threshold = threshold

            elif type_key == "expert_scored":
                if bfs.assessment_evaluator is None:
                    bfs.assessment_evaluator = "expert_scored"

            # compliance and downstream_workflow are handled by _extract_purpose

        return bfs

    # ------------------------------------------------------------------
    # Audience signals
    # ------------------------------------------------------------------

    def _extract_audience(self, bfs: BadgeFactSheet, lower: str) -> BadgeFactSheet:
        """First match wins — longest phrase has priority."""
        if bfs.audience_type is not None:
            return bfs

        for phrase, aud_type, detail, conf in _AUDIENCE_PHRASES_SORTED:
            if phrase.lower() in lower:
                bfs.audience_type = aud_type
                bfs.audience_signal = detail or phrase
                bfs.audience_signal_source = "keyword_rule"
                return bfs

        return bfs

    # ------------------------------------------------------------------
    # Purpose / downstream workflow signals
    # ------------------------------------------------------------------

    def _extract_purpose(
        self, bfs: BadgeFactSheet, lower: str, original: str
    ) -> BadgeFactSheet:
        for phrase, purpose_value in _PURPOSE_PHRASES_SORTED:
            if phrase.lower() not in lower:
                continue

            if purpose_value in ("compliance", "prerequisite_gate"):
                bfs.badge_purpose = purpose_value

            elif purpose_value == "downstream_workflow":
                # Capture text that follows the trigger phrase as the workflow description
                idx = lower.find(phrase.lower())
                if idx != -1:
                    after = original[idx + len(phrase):].strip().rstrip(".")
                    bfs.downstream_workflow = after[:120] if after else "detected"

        return bfs
