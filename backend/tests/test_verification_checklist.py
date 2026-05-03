"""
test_verification_checklist.py

Full end-to-end pipeline tests: input → POST /ingest → POST /classify → assert.

Each test is self-contained: it builds its own payload, calls both endpoints,
and asserts on the ClassificationResult (and occasionally the ingest BFS).

Tests
-----
T01  B001 Infrastructure Forum (OBv3 JSON)   — IR01c LDI URL fix, Souvenir
T02  Change Management Foundational (form)   — OSIL Achievement Foundational
T03  Makerspace Laser Cutting (form)         — Academic Skill Application
T04  Entrepreneurial Experience (form)       — OSIL Competency Demonstrated
T05  CPT Compliance Badge (form)             — OGI Achievement Foundational
T06  Missing Issuer Edge Case (form)         — graceful degradation
T07  Free Text Leadership Workshop           — Souvenir, OSIL via keyword
T08  OBv2 JSON Rejection                    — 422 error
"""

import os
import sys
import tempfile

# Override DATABASE_URL before importing any module that touches database.py.
# This file is the only backend test that spins up the full FastAPI app.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient — lifespan handler creates DB tables on start."""
    with TestClient(app) as c:
        yield c
    # Clean up temp database file after all tests in this module finish
    try:
        os.unlink(_db_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

def _pipeline(client: TestClient, input_type: str, payload) -> tuple[dict, dict]:
    """
    POST /ingest then POST /classify.

    Returns (bfs_dict, classification_result_dict).
    Fails immediately if either endpoint returns a non-200 status.
    """
    ingest_resp = client.post(
        "/ingest",
        json={"input_type": input_type, "payload": payload},
    )
    assert ingest_resp.status_code == 200, (
        f"/ingest returned {ingest_resp.status_code}: {ingest_resp.text}"
    )
    bfs = ingest_resp.json()

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200, (
        f"/classify returned {classify_resp.status_code}: {classify_resp.text}"
    )
    return bfs, classify_resp.json()


# ===========================================================================
# T01 — B001 Infrastructure Forum (OBv3 JSON)
#
# criteria.id = https://www.njit.edu/development/InfrastructureForum
# Verifies IR01c: "njit.edu/development" → LDI.
# "attended the full-day forum" → Souvenir.
# ===========================================================================

class TestT01_B001_InfrastructureForum:

    PAYLOAD = {
        "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
        "id": "https://api.badgr.io/public/badges/Z-nQnfeyTlmqWpm0WBdqmQ",
        "type": ["Achievement"],
        "criteria": {
            "id": "https://www.njit.edu/development/InfrastructureForum",
            "narrative": (
                "To earn this badge the recipient attended the full-day forum at NJIT."
            ),
        },
        "description": (
            "This badge recognizes individuals who participated in the 2026 NJIT "
            "Infrastructure Forum. This badge represents 6 PDH credits."
        ),
        "name": "2026 Infrastructure Forum",
        "achievementType": "Achievement",
    }

    def test_category(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert result["classification"]["category"] == "Continuing & Professional Education"

    def test_type(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert result["classification"]["type"] == "Souvenir"

    def test_level(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert result["classification"]["level"] == "Souvenir"

    def test_rule_S1R02(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert "S1R02" in result["rules_triggered"]

    def test_rule_S2R05(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert "S2R05" in result["rules_triggered"]

    def test_explanation_present(self, client):
        _, result = _pipeline(client, "obv3_json", self.PAYLOAD)
        assert result["explanation"] != ""


# ===========================================================================
# T02 — Change Management Foundational (form input)
#
# OSIL pre/post-assessment Achievement; "fundamentals of" → Foundational.
# Verifies S2R09 (pre_post_assessment now in _MODULE_ASSESSMENT_TYPES).
# ===========================================================================

class TestT02_ChangeManagementFoundational:

    PAYLOAD = {
        "badge_title": "Change Management — Foundational",
        "badge_description": (
            "Learn the fundamentals of navigating and leading change with a focus on "
            "self-awareness emotional intelligence communication and analytical thinking."
        ),
        "issuer": "OSIL",
        "audience_type": "njit_student",
        "earning_criteria_text": (
            "Students will attend 3 educational workshops and complete the "
            "pre and post assessment."
        ),
        "assessment_required": "yes",
        "assessment_type": "pre_post_assessment",
        "assessment_evaluator": "auto_assessed",
        "expert_evaluation_required": False,
        "evidence_type": "scored_assessment",
        "canvas_sequence_number": 1,
        "pathway_position": "1st",
    }

    def test_category(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["type"] == "Achievement"

    def test_level(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["level"] == "Foundational"

    def test_rule_S1R04(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S1R04" in result["rules_triggered"]


# ===========================================================================
# T03 — Makerspace Laser Cutting Skill Badge (form input)
#
# Expert-evaluated practical skill → Academic Skill Application.
# "demonstrated" + "operating" → Bloom "applying" → S3SK02 → Application.
# Note: criteria uses "verified by" (not "evaluated by") to avoid triggering
# Bloom "evaluating" which would push the level to Mastery.
# ===========================================================================

class TestT03_MakerspaceSkillBadge:

    PAYLOAD = {
        "badge_title": "Laser Cutting Skills",
        "badge_description": (
            "This badge recognizes students who have demonstrated competency in safely "
            "operating CO2 laser cutting equipment in the NJIT Makerspace."
        ),
        "issuer": "Makerspace",
        "audience_type": "njit_student",
        "earning_criteria_text": (
            "Complete all online safety modules and pass the final assessment with "
            "90% or higher. Complete in-person practical assessment verified by "
            "certified Makerspace instructor."
        ),
        "assessment_required": "yes",
        "assessment_type": "practical",
        "assessment_evaluator": "expert_scored",
        "assessment_pass_threshold": "90%",
        "expert_evaluation_required": True,
        "evidence_type": "observed",
    }

    def test_category(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["category"] == "Academic"

    def test_type(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["type"] == "Skill"

    def test_level(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["level"] == "Application"

    def test_rule_S1R05(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S1R05" in result["rules_triggered"]

    def test_rule_S2R06(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S2R06" in result["rules_triggered"]


# ===========================================================================
# T04 — Entrepreneurial Experience (form input)
#
# OSIL Competency with OR criteria → Demonstrated at Medium confidence.
# achievement_type = "Competency" → S2R02; real_world_context → S3C03.
# OR logic in criteria text downgrades confidence to Medium.
# ===========================================================================

class TestT04_EntrepreneurialExperience:

    PAYLOAD = {
        "badge_title": "Entrepreneurial Experience",
        "badge_description": (
            "Recognizes students who have applied entrepreneurial skills through "
            "real-world practice including startup activity public pitching or "
            "competitive entrepreneurial events."
        ),
        "issuer": "OSIL",
        "audience_type": "njit_student",
        "earning_criteria_text": (
            "Launched a startup, delivered a business pitch in front of an audience, "
            "competed in entrepreneurial events such as pitch competitions or hackathons, "
            "or completed a startup internship."
        ),
        "assessment_required": "yes",
        "assessment_evaluator": "expert_scored",
        "expert_evaluation_required": True,
        "real_world_context": True,
        "achievement_type": "Competency",
    }

    def test_category(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["type"] == "Competency"

    def test_level(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["level"] == "Demonstrated"

    def test_confidence_medium(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["confidence"] == "Medium"

    def test_rule_S1R04(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S1R04" in result["rules_triggered"]

    def test_rule_S2R02(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S2R02" in result["rules_triggered"]


# ===========================================================================
# T05 — CPT Application Compliance Badge (form input)
#
# OGI compliance badge: "mandatory to apply" → S2R04 → Achievement.
# canvas_sequence_number = 1 (via canvas_course_code MCHT.001.01) → Foundational.
# badge_purpose is a BFS field — checked from the /ingest response.
# ===========================================================================

class TestT05_ComplianceBadge:

    PAYLOAD = {
        "badge_title": "CPT Application Training",
        "badge_description": (
            "This badge is issued to F-1 international students upon completion "
            "of the CPT training."
        ),
        "issuer": "OGI",
        "audience_type": "njit_student",
        "audience_restriction": "F-1 international students",
        "earning_criteria_text": (
            "Complete all modules and quizzes. Earning this badge is mandatory to "
            "apply for CPT at NJIT. Share badge to Handshake for OGI review."
        ),
        "assessment_required": "yes",
        "assessment_type": "module_completion",
        "assessment_evaluator": "auto_assessed",
        # Explicitly set so badge_purpose is readable from the /ingest response
        "badge_purpose": "compliance",
        # canvas_course_code drives canvas_sequence_number = 1 → S3A05 → Foundational
        "canvas_course_code": "MCHT.001.01",
    }

    def test_badge_purpose_from_ingest(self, client):
        bfs, _ = _pipeline(client, "form", self.PAYLOAD)
        assert bfs["badge_purpose"] == "compliance"

    def test_type(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["type"] == "Achievement"

    def test_level(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["level"] == "Foundational"

    def test_rule_S2R04(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "S2R04" in result["rules_triggered"]


# ===========================================================================
# T06 — Missing Issuer Edge Case (form input)
#
# No issuer provided and no criteria URL → needs_followup = True,
# "issuer" in missing_signals, overall confidence = Low.
# ===========================================================================

class TestT06_MissingIssuer:

    PAYLOAD = {
        "badge_title": "Workshop on Sustainable Design",
        "badge_description": (
            "This badge recognizes participation in a hands-on sustainable design "
            "workshop for participants."
        ),
        "earning_criteria_text": "Attend the full workshop session.",
    }

    def test_needs_followup(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["follow_up_needed"] is True

    def test_issuer_in_missing_signals(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert "issuer" in result["missing_signals"]

    def test_confidence_low(self, client):
        _, result = _pipeline(client, "form", self.PAYLOAD)
        assert result["classification"]["confidence"] == "Low"


# ===========================================================================
# T07 — Free Text Leadership Workshop
#
# "student involvement office" → keyword detection → issuer = OSIL.
# "show up" / "no test or assignment" → attendance → Souvenir.
# Verifies the free-text issuer keyword layer added to map_free_text_to_bfs.
# ===========================================================================

class TestT07_FreeTextLeadershipWorkshop:

    TEXT = (
        "This badge is for NJIT students who attended our annual leadership workshop. "
        "Students had to show up for the full day and participate in group activities. "
        "No test or assignment was required. "
        "This is the first badge in our leadership development series "
        "offered by the student involvement office."
    )

    def test_category(self, client):
        _, result = _pipeline(client, "free_text", {"text": self.TEXT})
        assert result["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self, client):
        _, result = _pipeline(client, "free_text", {"text": self.TEXT})
        assert result["classification"]["type"] == "Souvenir"

    def test_level(self, client):
        _, result = _pipeline(client, "free_text", {"text": self.TEXT})
        assert result["classification"]["level"] == "Souvenir"


# ===========================================================================
# T08 — OBv2 JSON Rejection
#
# OBv2 context triggers ValueError in detect_obv_version →
# ingestion route raises HTTPException(422).
# ===========================================================================

class TestT08_OBv2Rejection:

    PAYLOAD = {
        "@context": "https://w3id.org/openbadges/v2",
        "type": "BadgeClass",
        "name": "Old Badge",
    }

    def test_status_422(self, client):
        resp = client.post(
            "/ingest",
            json={"input_type": "obv3_json", "payload": self.PAYLOAD},
        )
        assert resp.status_code == 422
