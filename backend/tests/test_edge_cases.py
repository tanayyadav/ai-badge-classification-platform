"""
test_edge_cases.py

Edge case tests — Upgrade 3 Categories 1, 2, 3, and 4.

Category 1: NLP accuracy (EC17–EC20) — exercised via POST /ingest + /classify.
Category 2: Input validation (EC01–EC03) — exercised via POST /ingest.
Category 3: Review workflow validation (EC26, EC29, EC30) — exercised via POST /review.
Category 4: Pathway edge cases (EC24) — exercised via POST /ingest.

EC01  Whitespace-only field detection
EC02  Criteria identical to description
EC03  Minimum content warning (warning-only, does not block)
EC17  Word-boundary matching for level phrases (no substring false positives)
EC18  Negated level phrase detection (negated phrase skipped)
EC19  Conflicting level phrases flagged in confidence_notes
EC20  Negated Bloom verb excluded from bloom_level extraction
EC24  Implied series detection from badge title
EC26  Identical override silently becomes acceptance
EC29  Minimum override reason length (≥ 20 characters)
EC30  Invalid taxonomy type+level combination rejected
"""

import json
import os
import sys
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
    try:
        os.unlink(_db_path)
    except OSError:
        pass


def _ingest(client: TestClient, payload: dict) -> dict:
    """POST /ingest with form input_type. Returns the BFS dict."""
    resp = client.post("/ingest", json={"input_type": "form", "payload": payload})
    assert resp.status_code == 200, f"/ingest returned {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# EC01 — Whitespace-only field detection
# ---------------------------------------------------------------------------

class TestEC01_WhitespaceFields:

    def test_ec01_whitespace_title_treated_as_null(self, client):
        """badge_title = '   ' must be set to None and flagged as missing."""
        bfs = _ingest(client, {
            "badge_title": "   ",
            "badge_description": "A badge that recognizes completion of a comprehensive workshop on leadership skills.",
            "issuer": "OSIL",
            "earning_criteria_text": "Attend the full-day workshop and complete the reflection activity.",
        })
        assert bfs["badge_title"] is None
        assert "badge_title" in bfs["missing_signals"]
        assert bfs["needs_followup_questions"] is True

    def test_ec01_whitespace_description_treated_as_null(self, client):
        """badge_description = '\\n\\n' must be set to None and flagged as missing."""
        bfs = _ingest(client, {
            "badge_title": "Leadership Workshop",
            "badge_description": "\n\n",
            "issuer": "OSIL",
            "earning_criteria_text": "Attend the full-day workshop and complete the reflection activity.",
        })
        assert bfs["badge_description"] is None
        assert "badge_description" in bfs["missing_signals"]

    def test_ec01_whitespace_criteria_treated_as_null(self, client):
        """earning_criteria_text = '  \\t  ' must be set to None and flagged as missing."""
        bfs = _ingest(client, {
            "badge_title": "Leadership Workshop",
            "badge_description": "A badge that recognizes completion of a comprehensive workshop on leadership skills.",
            "issuer": "OSIL",
            "earning_criteria_text": "  \t  ",
        })
        assert bfs["earning_criteria_text"] is None
        assert "earning_criteria_text" in bfs["missing_signals"]


# ---------------------------------------------------------------------------
# EC02 — Criteria identical to description
# ---------------------------------------------------------------------------

class TestEC02_CriteriaIdenticalToDescription:

    _SHARED_TEXT = (
        "This badge is awarded to NJIT students who attended the annual "
        "leadership workshop and completed all required activities."
    )

    def test_ec02_criteria_identical_to_description(self, client):
        """When earning_criteria_text == badge_description the system must flag it."""
        bfs = _ingest(client, {
            "badge_title": "Leadership Workshop",
            "badge_description": self._SHARED_TEXT,
            "issuer": "OSIL",
            "earning_criteria_text": self._SHARED_TEXT,
        })
        assert "earning_criteria_meaningful_content" in bfs["missing_signals"]
        assert bfs["needs_followup_questions"] is True
        assert "criteria_identical_to_description" in (bfs["confidence_notes"] or "")


# ---------------------------------------------------------------------------
# EC03 — Minimum content warning (warning-only)
# ---------------------------------------------------------------------------

class TestEC03_MinimumContentWarnings:

    def test_ec03_short_description_adds_warning_not_missing_signal(self, client):
        """A short description adds a confidence_notes warning but NOT a missing_signal."""
        bfs = _ingest(client, {
            "badge_title": "Quick Badge",
            "badge_description": "Short desc",          # < 50 chars
            "issuer": "OSIL",
            "earning_criteria_text": "Attend the full-day workshop and submit the reflection form.",
        })
        assert "description_too_short" in (bfs["confidence_notes"] or "")
        assert "badge_description" not in bfs["missing_signals"]

    def test_ec03_short_criteria_adds_warning_not_missing_signal(self, client):
        """A short criteria adds a confidence_notes warning but NOT a missing_signal."""
        bfs = _ingest(client, {
            "badge_title": "Quick Badge",
            "badge_description": "A badge that recognizes completion of a comprehensive workshop on leadership.",
            "issuer": "OSIL",
            "earning_criteria_text": "Do task",         # < 30 chars
        })
        assert "criteria_too_short" in (bfs["confidence_notes"] or "")
        assert "earning_criteria_text" not in bfs["missing_signals"]


# ---------------------------------------------------------------------------
# Helpers shared by EC26 / EC29 / EC30 tests
# ---------------------------------------------------------------------------

# A minimal OSIL attendance badge — classifies as Co-Curricular / Souvenir / Souvenir.
_SOUVENIR_FORM = {
    "badge_title": "Leadership Workshop",
    "badge_description": (
        "A badge recognizing NJIT students who completed the annual "
        "OSIL leadership workshop."
    ),
    "issuer": "OSIL",
    "earning_criteria_text": "Attend the full-day workshop and submit the reflection activity.",
}


def _classify_badge(client) -> dict:
    """
    Classify a simple badge and return the full ClassificationResult dict.
    Ingest + classify in one call.
    """
    ingest_resp = client.post(
        "/ingest", json={"input_type": "form", "payload": _SOUVENIR_FORM}
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    bfs = ingest_resp.json()

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200, classify_resp.text
    return classify_resp.json()


def _review(client, log_id: str, **kwargs) -> object:
    """POST /review and return the raw Response object."""
    return client.post("/review", json={"log_id": log_id, **kwargs})


# ---------------------------------------------------------------------------
# EC29 — Minimum override reason length
# ---------------------------------------------------------------------------

class TestEC29_MinimumOverrideReason:

    def test_ec29_override_reason_too_short(self, client):
        """override_reason shorter than 20 chars must return 400."""
        result = _classify_badge(client)
        log_id = result["governance"]["log_id"]

        resp = _review(
            client,
            log_id,
            reviewer_status="overridden",
            reviewer_id="tester",
            override_reason="Wrong",          # 5 chars — too short
            override_category="Academic",
        )
        assert resp.status_code == 400
        assert "20 characters" in resp.json()["detail"]

    def test_ec29_override_reason_exactly_20_chars(self, client):
        """override_reason of exactly 20 chars must be accepted (boundary value)."""
        result = _classify_badge(client)
        log_id = result["governance"]["log_id"]

        resp = _review(
            client,
            log_id,
            reviewer_status="overridden",
            reviewer_id="tester",
            override_reason="A" * 20,         # exactly 20 chars — must pass
            override_category="Academic",     # different from recommended Co-Curricular
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# EC30 — Invalid taxonomy combination validation
# ---------------------------------------------------------------------------

class TestEC30_InvalidTaxonomyCombination:

    def test_ec30_invalid_taxonomy_combination(self, client):
        """Skill type + Foundational level is an invalid combination — must return 400."""
        result = _classify_badge(client)
        log_id = result["governance"]["log_id"]

        resp = _review(
            client,
            log_id,
            reviewer_status="overridden",
            reviewer_id="tester",
            override_reason="Testing invalid combination here",   # ≥ 20 chars
            override_type="Skill",
            override_level="Foundational",   # invalid for Skill
        )
        assert resp.status_code == 400
        assert "Invalid taxonomy combination" in resp.json()["detail"]

    def test_ec30_valid_taxonomy_combination(self, client):
        """Skill type + Application level is valid — must return 200."""
        result = _classify_badge(client)
        log_id = result["governance"]["log_id"]

        resp = _review(
            client,
            log_id,
            reviewer_status="overridden",
            reviewer_id="tester",
            override_reason="Confirmed skill badge application level",  # ≥ 20 chars
            override_type="Skill",
            override_level="Application",    # valid for Skill
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# EC26 — Identical override detection
# ---------------------------------------------------------------------------

class TestEC26_IdenticalOverride:

    def test_ec26_identical_override_treated_as_acceptance(self, client):
        """
        Submitting override values that match the system recommendation
        must silently resolve to reviewer_status == 'accepted'.
        """
        result = _classify_badge(client)
        log_id = result["governance"]["log_id"]
        rec = result["classification"]

        resp = _review(
            client,
            log_id,
            reviewer_status="overridden",
            reviewer_id="tester",
            override_reason="Confirmed correct classification",   # ≥ 20 chars
            override_category=rec["category"],   # matches recommended
            override_type=rec["type"],           # matches recommended
            override_level=rec["level"],         # matches recommended
        )
        assert resp.status_code == 200
        assert resp.json()["reviewer_status"] == "accepted"


# ---------------------------------------------------------------------------
# Helpers shared by EC17 / EC18 / EC19 / EC20
# ---------------------------------------------------------------------------

def _ingest_classify(client: TestClient, payload: dict) -> tuple[dict, dict]:
    """
    POST /ingest then POST /classify.
    Returns (bfs_dict, classification_result_dict).
    """
    ingest_resp = client.post("/ingest", json={"input_type": "form", "payload": payload})
    assert ingest_resp.status_code == 200, ingest_resp.text
    bfs = ingest_resp.json()

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200, classify_resp.text
    return bfs, classify_resp.json()


def _get_normalized_facts(client: TestClient, log_id: str) -> dict:
    """GET /logs/{log_id} and return the parsed normalized_facts BFS dict."""
    log_resp = client.get(f"/logs/{log_id}")
    assert log_resp.status_code == 200, log_resp.text
    return json.loads(log_resp.json()["normalized_facts"])


# ---------------------------------------------------------------------------
# EC17 — Word-boundary matching for level phrases
# ---------------------------------------------------------------------------

class TestEC17_WordBoundaryMatching:

    def test_ec17_substring_does_not_match(self, client):
        """
        'precapstone' (one word) must NOT trigger the 'capstone' level phrase.
        With pure substring matching this would incorrectly return Terminal.
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Workshop Badge",
            "badge_description": (
                "This precapstone course prepares students for advanced study."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Attend all required workshop sessions.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        assert facts.get("self_declared_level") != "Terminal", (
            "'precapstone' must not trigger Terminal via substring match"
        )

    def test_ec17_whole_word_capstone_matches(self, client):
        """
        'capstone' as a standalone word must still trigger Terminal level.
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Capstone Badge",
            "badge_description": (
                "This capstone experience represents the culmination of the program."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Complete the capstone project and submit deliverables.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        assert facts.get("self_declared_level") == "Terminal"


# ---------------------------------------------------------------------------
# EC18 — Negated level phrase detection
# ---------------------------------------------------------------------------

class TestEC18_NegatedLevelPhrase:

    def test_ec18_negated_capstone_not_matched(self, client):
        """
        'not a capstone' — 'capstone' is negated and must not set level via
        phrase_dictionary.  Text is chosen to avoid matching pattern_rules.py
        Terminal regex (which requires a second word: course/module/badge etc.).
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Participation Award",
            "badge_description": (
                "This is not a capstone. It recognizes attendance only."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Attend the workshop.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        assert facts.get("self_declared_level") != "Terminal", (
            "Negated 'capstone' must not trigger Terminal level"
        )

    def test_ec18_positive_capstone_matched(self, client):
        """
        'capstone' without negation must still set level = Terminal.
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Program Badge",
            "badge_description": (
                "This badge marks the capstone achievement of the leadership series."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Complete all required activities.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        assert facts.get("self_declared_level") == "Terminal"


# ---------------------------------------------------------------------------
# EC19 — Conflicting level phrases
# ---------------------------------------------------------------------------

class TestEC19_ConflictingLevelPhrases:

    def test_ec19_conflict_flagged_in_confidence_notes(self, client):
        """
        Text with both 'introductory' (→ Foundational) and 'capstone'
        (→ Terminal) must produce a CONFLICT note in confidence_notes.
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Leadership Badge",
            "badge_description": (
                "An introductory overview that culminates in a capstone presentation."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Attend all sessions and complete the capstone.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        notes = facts.get("confidence_notes") or ""
        assert "CONFLICT" in notes, (
            f"Expected CONFLICT in confidence_notes; got: {notes!r}"
        )

    def test_ec19_no_conflict_for_consistent_signals(self, client):
        """
        Text with only Foundational phrases must NOT produce a CONFLICT note.
        NLP extraction happens in /classify, so we check normalized_facts.
        """
        _, result = _ingest_classify(client, {
            "badge_title": "Intro Badge",
            "badge_description": (
                "An introductory workshop designed for entry-level participants."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": "Attend the full workshop session.",
        })
        facts = _get_normalized_facts(client, result["governance"]["log_id"])
        notes = facts.get("confidence_notes") or ""
        assert "CONFLICT" not in notes, (
            f"Unexpected CONFLICT in confidence_notes: {notes!r}"
        )


# ---------------------------------------------------------------------------
# EC20 — Negated Bloom verb exclusion
# ---------------------------------------------------------------------------

class TestEC20_NegatedBloomVerb:

    def test_ec20_negated_verb_excluded_from_bloom(self, client):
        """
        'do not demonstrate' — the negated verb must not contribute to
        bloom_verbs_detected in the classified BFS.
        """
        payload = {
            "badge_title": "Workshop Badge",
            "badge_description": (
                "Participants do not demonstrate advanced technical skills in this session."
            ),
            "issuer": "LDI",
            "earning_criteria_text": "Attend all mandatory sessions.",
        }
        _, result = _ingest_classify(client, payload)
        log_id = result["governance"]["log_id"]
        facts = _get_normalized_facts(client, log_id)

        bloom_verbs = facts.get("bloom_verbs_detected") or []
        assert "demonstrate" not in bloom_verbs, (
            f"Negated 'demonstrate' must not appear in bloom_verbs_detected; got {bloom_verbs}"
        )

    def test_ec20_positive_verb_included_in_bloom(self, client):
        """
        'demonstrate' (not negated) must appear in bloom_verbs_detected.
        """
        payload = {
            "badge_title": "Skills Badge",
            "badge_description": (
                "Participants demonstrate proficiency in core professional techniques."
            ),
            "issuer": "LDI",
            "earning_criteria_text": "Attend all mandatory sessions.",
        }
        _, result = _ingest_classify(client, payload)
        log_id = result["governance"]["log_id"]
        facts = _get_normalized_facts(client, log_id)

        bloom_verbs = facts.get("bloom_verbs_detected") or []
        assert "demonstrate" in bloom_verbs, (
            f"Non-negated 'demonstrate' must appear in bloom_verbs_detected; got {bloom_verbs}"
        )


# ---------------------------------------------------------------------------
# EC24 — Implied series detection from badge title
# ---------------------------------------------------------------------------

class TestEC24_ImpliedSeriesDetection:

    def test_ec24_title_with_level_keyword_sets_progression_implied(self, client):
        """
        A title containing a series keyword ('Introduction to') without any
        formal canvas_course_code or pathway_name must set
        progression_implied = True and add a 'series progression' note.
        """
        bfs = _ingest(client, {
            "badge_title": "Introduction to Data Science",
            "badge_description": (
                "A badge recognizing students who completed the introductory "
                "data science workshop at NJIT."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": (
                "Attend the full-day workshop and submit the reflection form."
            ),
        })
        assert bfs["progression_implied"] is True
        assert "series progression" in (bfs["confidence_notes"] or "")

    def test_ec24_title_without_level_keyword_no_implied(self, client):
        """
        A generic title with no series keyword must leave
        progression_implied = False (its default).
        """
        bfs = _ingest(client, {
            "badge_title": "Data Science Workshop",
            "badge_description": (
                "A badge recognizing students who completed the data science "
                "workshop at NJIT."
            ),
            "issuer": "OSIL",
            "earning_criteria_text": (
                "Attend the full-day workshop and submit the reflection form."
            ),
        })
        assert bfs["progression_implied"] is False
