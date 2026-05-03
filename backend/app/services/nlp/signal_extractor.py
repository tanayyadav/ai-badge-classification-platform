"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

NLP Signal Extractor — orchestrates all four layers.

Pipeline (docs/nlp-phrase-dictionary.md):
  Layer 1: PhraseExtractor   — exact keyword phrases (highest confidence)
  Layer 2: PatternExtractor  — regex patterns for paraphrased language
  Layer 3: BloomExtractor    — spaCy verb → Bloom level
  Layer 4: LLMExtractor      — stub, enabled via USE_LLM=true

After all layers run, the gap detector populates missing_signals and
sets needs_followup_questions = True when critical fields are still absent.

Critical fields checked (signals the rule engine cannot work without):
  - assessment_evaluator : needed to distinguish Skill vs Achievement (S2R06/S2R07)
  - audience_type        : needed for S1R01 vs S1R02 when issuer == "LDI"
"""

import os

from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.nlp.bloom_extractor import BloomExtractor
from app.services.nlp.llm_extractor import LLMExtractor
from app.services.nlp.pattern_rules import PatternExtractor
from app.services.nlp.phrase_dictionary import PhraseExtractor


class SignalExtractor:
    """
    Orchestrates all 4 NLP layers in order.

    Args:
        use_llm: Override for USE_LLM env var. If None, reads from environment.
    """

    def __init__(self, use_llm: bool | None = None):
        if use_llm is None:
            use_llm = os.getenv("USE_LLM", "false").lower() == "true"
        self.use_llm = use_llm

        self.phrase_extractor = PhraseExtractor()
        self.pattern_extractor = PatternExtractor()
        self.bloom_extractor = BloomExtractor()
        self.llm_extractor = LLMExtractor()

    def extract_all(self, bfs: BadgeFactSheet) -> BadgeFactSheet:
        """
        Run all four NLP layers against the badge text and return an updated BFS.

        Text surface: badge_description + earning_criteria_text concatenated —
        the same surface is passed to every layer so results are consistent.

        Layer execution order (each layer fills only what is still None):
          Layer 1 — PhraseExtractor: exact case-insensitive keyword phrases;
                    highest confidence; produces self_declared_level,
                    assessment_type, audience_type, badge_purpose
          Layer 2 — PatternExtractor: regex patterns for paraphrased language;
                    fills gaps left by Layer 1; marks level_signal_source as
                    "regex_pattern" when it fires
          Layer 3 — BloomExtractor: spaCy dependency-parse verb lemma mapping;
                    populates bloom_level, bloom_verbs_detected, bloom_confidence
          Layer 4 — LLMExtractor: stub; only runs when USE_LLM=true AND
                    _has_critical_missing() is True; marks signals as
                    "llm_extraction"

        After all layers, _check_missing_signals() appends any still-absent
        critical fields to bfs.missing_signals and sets
        needs_followup_questions = True.
        """
        text = f"{bfs.badge_description} {bfs.earning_criteria_text}".strip()

        # Layer 1 — exact phrase matching
        bfs = self.phrase_extractor.extract(bfs, text)

        # Layer 2 — regex patterns
        bfs = self.pattern_extractor.extract(bfs, text)

        # Layer 3 — spaCy Bloom verb extraction
        bfs = self.bloom_extractor.extract(bfs, text)

        # Layer 4 — LLM gap filling (only when enabled and signals are missing)
        if self.use_llm and self._has_critical_missing(bfs):
            bfs = self.llm_extractor.extract(bfs)

        # Final gap assessment — adds to any missing_signals already set
        # by the normalizer (e.g. "issuer", "badge_title")
        self._check_missing_signals(bfs)

        # EC19 title-level conflict — compare badge_title keywords against
        # the level extracted from description/criteria phrases.
        self._check_title_level_conflict(bfs)

        return bfs

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def _has_critical_missing(self, bfs: BadgeFactSheet) -> bool:
        """True if any signal in the critical set is still unresolved."""
        return bool(self._new_missing_signals(bfs))

    def _check_missing_signals(self, bfs: BadgeFactSheet) -> None:
        """
        Populate bfs.missing_signals with any critical fields still absent
        after all NLP layers have run.

        One-way gate: entries are only ever added, never removed — signals
        flagged by the normalizer (e.g. "issuer") survive unchanged, and
        this method adds any additional NLP-layer gaps. The gate cannot be
        reset to clean once needs_followup_questions is True.

        Critical fields checked:
          - issuer            — Stage 1 cannot classify without it (S1R08)
          - assessment_evaluator — determines Skill vs Achievement (S2R06/S2R07);
                                   only flagged when assessment_required == "yes"
          - audience_type     — required when issuer is LDI to choose between
                                Faculty & Staff (S1R01) vs Continuing Ed (S1R02)

        Only adds new entries — does not duplicate signals already recorded
        by the normalizer.
        """
        for field in self._new_missing_signals(bfs):
            if field not in bfs.missing_signals:
                bfs.missing_signals.append(field)

        if bfs.missing_signals:
            bfs.needs_followup_questions = True

    # ------------------------------------------------------------------
    # EC19 title-level conflict detection
    # ------------------------------------------------------------------

    # Keywords in badge_title that hint at a broad level bucket.
    _TITLE_LEVEL_KEYWORDS: dict[str, list[str]] = {
        "high": ["advanced", "mastery", "expert", "senior"],
        "mid":  ["intermediate"],
        "low":  ["foundational", "foundation", "introduction",
                 "introductory", "basic", "beginner"],
    }

    # Maps the self_declared_level (from description/criteria phrases) to the
    # same three-bucket scale so title and description are comparable.
    _DESCRIPTION_LEVEL_MAP: dict[str, str] = {
        "Foundational": "low",
        "Milestone":    "mid",
        "Terminal":     "high",
        "Mastery":      "high",
    }

    def _get_title_level_hint(self, badge_title: str | None) -> str | None:
        """Return "high" / "mid" / "low" bucket for the badge title, or None."""
        if not badge_title:
            return None
        title_lower = badge_title.lower()
        for bucket, keywords in self._TITLE_LEVEL_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return bucket
        return None

    def _check_title_level_conflict(self, bfs: BadgeFactSheet) -> None:
        """
        EC19 extension — title vs description level conflict.

        When the badge title contains a level keyword (e.g. "Advanced")
        and the description/criteria phrases yielded a contradicting level
        (e.g. "Foundational"), record the conflict in confidence_notes.

        The description signal is kept as primary (it has more context);
        only a note is added — no field is overwritten.
        """
        title_hint = self._get_title_level_hint(bfs.badge_title)
        if not title_hint or not bfs.self_declared_level:
            return

        desc_hint = self._DESCRIPTION_LEVEL_MAP.get(bfs.self_declared_level)
        if not desc_hint or title_hint == desc_hint:
            return

        conflict_note = (
            f"CONFLICT: badge title suggests {title_hint} level "
            f"but description phrases suggest "
            f"{bfs.self_declared_level} level. "
            f"Description signal used as primary."
        )
        bfs.confidence_notes = (
            (bfs.confidence_notes or "") + f" | {conflict_note}"
        ).lstrip(" |").strip()

    def _new_missing_signals(self, bfs: BadgeFactSheet) -> list[str]:
        """
        Return critical fields that are still None after NLP extraction.

        Checks only the fields the rule engine cannot fall back on —
        avoiding false positives that would incorrectly degrade confidence.
        """
        missing: list[str] = []

        # issuer — Stage 1 cannot classify without it (IR07 / S1R08)
        if bfs.issuer is None and "issuer" not in bfs.missing_signals:
            missing.append("issuer")

        # assessment_evaluator — needed to distinguish Skill vs Achievement.
        # Only flag as missing if assessment is required and evaluator unknown.
        if (
            bfs.assessment_required == "yes"
            and bfs.assessment_evaluator is None
            and "assessment_evaluator" not in bfs.missing_signals
        ):
            missing.append("assessment_evaluator")

        # audience_type — needed when issuer is LDI to choose between
        # S1R01 (Faculty & Staff) and S1R02 (Continuing Ed).
        if (
            bfs.issuer == "LDI"
            and bfs.audience_type is None
            and "audience_type" not in bfs.missing_signals
        ):
            missing.append("audience_type")

        return missing
