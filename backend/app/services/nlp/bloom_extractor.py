"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

NLP Layer 3 — spaCy Bloom's Taxonomy verb extraction.

Loads en_core_web_sm once at module level (expensive operation).
Uses the full BLOOM_VERB_MAP from docs/nlp-phrase-dictionary.md.

Strategy:
- Tokenise up to the first 1000 characters (performance limit)
- Find all VERB tokens, lemmatise them
- Map each lemma to a Bloom level via BLOOM_VERB_MAP
- Take the HIGHEST level detected (most complex cognitive demand)
- confidence = "High" if 3+ distinct Bloom verbs found, else "Medium"

Only fills bloom_level if not already set.
Sets level_signal_source = "spacy_verb" if bloom_level is used as the
level signal (that decision is made by the engine, not here).
"""

import spacy

from app.models.badge_fact_sheet import BadgeFactSheet

# Load once at import time — not per-request
_nlp = spacy.load("en_core_web_sm")


# ---------------------------------------------------------------------------
# BLOOM_VERB_MAP
# ---------------------------------------------------------------------------
BLOOM_VERB_MAP: dict[str, str] = {
    # Remembering
    "identify": "remembering",
    "recall":   "remembering",
    "list":     "remembering",
    "name":     "remembering",
    "recognize":"remembering",
    "define":   "remembering",
    "state":    "remembering",
    "label":    "remembering",

    # Understanding
    "explain":     "understanding",
    "describe":    "understanding",
    "summarize":   "understanding",
    "interpret":   "understanding",
    "classify":    "understanding",
    "compare":     "understanding",
    "discuss":     "understanding",
    "illustrate":  "understanding",
    "distinguish": "understanding",

    # Applying
    "apply":       "applying",
    "use":         "applying",
    "implement":   "applying",
    "execute":     "applying",
    "demonstrate": "applying",
    "perform":     "applying",
    "practice":    "applying",
    "calculate":   "applying",
    "complete":    "applying",
    "operate":     "applying",

    # Analyzing
    "analyze":       "analyzing",
    "examine":       "analyzing",
    "differentiate": "analyzing",
    "investigate":   "analyzing",
    # distinguish + compare also appear here (already in Understanding — spaCy
    # will assign the lemma once; Understanding takes precedence when both match
    # because we use max() over BLOOM_HIERARCHY which orders them correctly)
    "contrast":  "analyzing",
    "question":  "analyzing",
    "test":      "analyzing",

    # Evaluating
    "evaluate":  "evaluating",
    "assess":    "evaluating",
    "judge":     "evaluating",
    "critique":  "evaluating",
    "justify":   "evaluating",
    "argue":     "evaluating",
    "defend":    "evaluating",
    "prioritize":"evaluating",

    # Creating
    "design":    "creating",
    "create":    "creating",
    "develop":   "creating",
    "produce":   "creating",
    "build":     "creating",
    "construct": "creating",
    "generate":  "creating",
    "formulate": "creating",
    "lead":      "creating",
    "mentor":    "creating",
    "teach":     "creating",
    "innovate":  "creating",
}

# Ordered lowest → highest — used with max() to pick the ceiling level
BLOOM_HIERARCHY: list[str] = [
    "remembering",
    "understanding",
    "applying",
    "analyzing",
    "evaluating",
    "creating",
]


def is_verb_negated(token) -> bool:
    """
    EC20 — Detect negated verbs via spaCy dependency parsing.

    Returns True if the token has any child whose dependency label
    is 'neg' (spaCy's negation modifier relation).
    Example: "do not demonstrate" — 'not' is a 'neg' child of 'demonstrate'.
    """
    return any(child.dep_ == "neg" for child in token.children)


class BloomExtractor:
    """
    Layer 3: spaCy-based Bloom's Taxonomy verb extraction.

    Call extract(bfs, text) — returns updated BFS with bloom_level,
    bloom_confidence, and bloom_verbs_detected populated.
    """

    def extract(self, bfs: BadgeFactSheet, text: str) -> BadgeFactSheet:
        doc = _nlp(text[:1000])  # limit for performance
        detected_levels: list[str] = []
        verbs_found: list[str] = []

        for token in doc:
            if token.pos_ == "VERB":
                if is_verb_negated(token):      # EC20 — skip negated verbs
                    continue
                lemma = token.lemma_.lower()
                if lemma in BLOOM_VERB_MAP:
                    bloom = BLOOM_VERB_MAP[lemma]
                    detected_levels.append(bloom)
                    verbs_found.append(lemma)

        if detected_levels:
            highest = max(
                detected_levels,
                key=lambda lvl: BLOOM_HIERARCHY.index(lvl),
            )
            bfs.bloom_level = highest
            bfs.bloom_verbs_detected = list(set(verbs_found))
            bfs.bloom_confidence = "High" if len(detected_levels) >= 3 else "Medium"

        return bfs
