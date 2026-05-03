"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

NLP Layer 4 — LLM extractor stub.

Enabled only when USE_LLM=true environment variable is set.
Returns the BFS unchanged until implemented.

Architecture rules:
- The LLM never makes classification decisions (rule engine only)
- The LLM extracts signals only — all returned signals must be
  marked source="llm_extraction"

Future implementation notes:
  1. Only request fields listed in bfs.missing_signals
  2. Return structured JSON only — no prose
  3. Mark every returned signal with source="llm_extraction"
  4. Configure the LLM provider and model via LLM_API_KEY and
     LLM_MODEL environment variables (provider-agnostic)
"""

from app.models.badge_fact_sheet import BadgeFactSheet


class LLMExtractor:
    """
    Stub — returns bfs unchanged.
    Missing signals will trigger follow-up questions in the UI instead.
    """

    def extract(self, bfs: BadgeFactSheet) -> BadgeFactSheet:
        # Stub — no-op until USE_LLM=true and this is implemented
        return bfs
