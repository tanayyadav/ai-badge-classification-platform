"""
Phase 9 — API Integration Tests.

End-to-end HTTP tests covering the full request/response cycle:
  POST /ingest  →  POST /classify  →  POST /review  →  GET /logs/{id}

Also covers:
  - Input validation (missing required fields, bad payload)
  - GET /health endpoint
  - Pagination on GET /logs
  - OBv3 JSON ingestion path
"""

import json
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.governance_log import Base
from database import get_db


# ---------------------------------------------------------------------------
# In-memory DB
# ---------------------------------------------------------------------------

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)
Base.metadata.create_all(bind=_TEST_ENGINE)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


# ---------------------------------------------------------------------------
# Minimal valid form payloads
# ---------------------------------------------------------------------------

_MINIMAL_SOUVENIR = {
    "badge_title": "Test Event Badge",
    "badge_description": "Awarded for attending the test event.",
    "issuer": "OSIL",
    "earning_criteria_text": "Attend the full event. No test or assessment required.",
    "assessment_required": "no",
    "assessment_type": "attendance",
    "badge_purpose": "recognition",
    "pathway_position": "Standalone",
}

_MINIMAL_ACHIEVEMENT = {
    "badge_title": "AI Foundations",
    "badge_description": "Foundation-level badge for NJIT faculty new to AI. No prior experience required.",
    "issuer": "LDI",
    "intended_audience": "NJIT faculty",
    "audience_type": "faculty",
    "earning_criteria_text": "Passing knowledge checks with an 80% or higher score.",
    "assessment_required": "yes",
    "assessment_type": "knowledge_checks",
    "assessment_evaluator": "auto_assessed",
    "canvas_course_code": "MCAI.001.01",
    "badge_purpose": "recognition",
}

_MINIMAL_SKILL = {
    "badge_title": "Welding Application",
    "badge_description": "Students demonstrate their welding skills through expert assessment.",
    "issuer": "Makerspace",
    "intended_audience": "NJIT students",
    "audience_type": "njit_student",
    "earning_criteria_text": "Expert-scored practical evaluation. Instructor assesses the student's welding technique.",
    "assessment_required": "yes",
    "assessment_type": "practical",
    "assessment_evaluator": "expert_scored",
    "expert_evaluation_required": True,
    "badge_purpose": "recognition",
}


def _full_pipeline(form_payload: dict) -> dict:
    """POST /ingest → POST /classify, return ClassificationResult."""
    r1 = client.post("/ingest", json={"input_type": "form", "payload": form_payload})
    assert r1.status_code == 200
    bfs = r1.json()
    r2 = client.post("/classify", json=bfs)
    assert r2.status_code == 200
    return r2.json()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:

    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_version_present(self):
        r = client.get("/health")
        assert "version" in r.json()


# ---------------------------------------------------------------------------
# POST /ingest validation
# ---------------------------------------------------------------------------

class TestIngestValidation:

    def test_unknown_input_type_returns_422(self):
        r = client.post("/ingest", json={"input_type": "excel", "payload": {}})
        assert r.status_code == 422

    def test_missing_payload_returns_422(self):
        r = client.post("/ingest", json={"input_type": "form"})
        assert r.status_code == 422

    def test_empty_form_returns_bfs(self):
        # Empty form is valid — fills missing_signals
        r = client.post("/ingest", json={"input_type": "form", "payload": {}})
        assert r.status_code == 200
        bfs = r.json()
        assert "badge_id" in bfs
        assert "issuer" in bfs.get("missing_signals", [])

    def test_obv3_json_missing_context_returns_422(self):
        # OBv3 without @context field fails version detection → ValueError → 422
        r = client.post("/ingest", json={
            "input_type": "obv3_json",
            "payload": {"name": "Test", "description": "Test badge"}
        })
        assert r.status_code == 422

    def test_valid_obv3_json_returns_bfs(self):
        obv3 = {
            "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
            "type": ["Achievement"],
            "name": "Test OBv3 Badge",
            "description": "A test badge in OBv3 format.",
            "criteria": {
                "id": "https://njitcl.catalog.instructure.com/badges/test-001",
                "narrative": "Passing knowledge checks with an 80% or higher score."
            },
            "achievementType": "Achievement"
        }
        r = client.post("/ingest", json={"input_type": "obv3_json", "payload": obv3})
        assert r.status_code == 200
        bfs = r.json()
        assert bfs["issuer"] == "LDI"
        assert bfs["structured_source_type"] == "obv3_json"


# ---------------------------------------------------------------------------
# POST /classify validation
# ---------------------------------------------------------------------------

class TestClassifyValidation:

    def test_classify_with_empty_body_returns_200(self):
        # BadgeFactSheet has all-default fields, so {} is valid and gets defaults
        r = client.post("/classify", json={})
        assert r.status_code == 200
        result = r.json()
        assert "classification" in result
        assert "explanation" in result

    def test_classify_souvenir_full_result(self):
        result = _full_pipeline(_MINIMAL_SOUVENIR)
        assert result["classification"]["type"] == "Souvenir"
        assert result["classification"]["level"] == "Souvenir"
        assert result["explanation"] != ""
        assert result["governance"]["reviewer_status"] == "pending"
        assert result["governance"]["log_id"] != ""

    def test_classify_achievement_full_result(self):
        result = _full_pipeline(_MINIMAL_ACHIEVEMENT)
        assert result["classification"]["type"] == "Achievement"
        assert result["classification"]["category"] == "Faculty & Staff Development"
        assert result["rules_triggered"]

    def test_classify_skill_full_result(self):
        result = _full_pipeline(_MINIMAL_SKILL)
        assert result["classification"]["type"] == "Skill"
        assert result["classification"]["category"] == "Academic"


# ---------------------------------------------------------------------------
# Full pipeline: ingest → classify → review → get log
# ---------------------------------------------------------------------------

class TestFullPipelineAccept:

    def test_accept_flow(self):
        # Step 1: classify
        result = _full_pipeline(_MINIMAL_SOUVENIR)
        log_id = result["governance"]["log_id"]
        assert log_id != ""

        # Step 2: accept
        review_payload = {
            "log_id": log_id,
            "reviewer_status": "accepted",
            "reviewer_id": "test_reviewer_1",
        }
        r = client.post("/review", json=review_payload)
        assert r.status_code == 200
        log = r.json()
        assert log["reviewer_status"] == "accepted"
        assert log["final_locked_decision"] is not None

        # Step 3: verify log persisted
        r2 = client.get(f"/logs/{log_id}")
        assert r2.status_code == 200
        assert r2.json()["reviewer_status"] == "accepted"

    def test_override_flow(self):
        # Step 1: classify
        result = _full_pipeline(_MINIMAL_ACHIEVEMENT)
        log_id = result["governance"]["log_id"]

        # Step 2: override
        review_payload = {
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "test_reviewer_2",
            "override_reason": "Badge actually serves external professionals",
            "override_category": "Continuing & Professional Education",
        }
        r = client.post("/review", json=review_payload)
        assert r.status_code == 200
        log = r.json()
        assert log["reviewer_status"] == "overridden"
        assert log["override_reason"] == "Badge actually serves external professionals"
        assert log["final_category"] == "Continuing & Professional Education"


class TestFullPipelineOverrideValidation:

    def test_override_requires_reason(self):
        result = _full_pipeline(_MINIMAL_ACHIEVEMENT)
        log_id = result["governance"]["log_id"]
        r = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "reviewer",
            "override_category": "Academic",
        })
        assert r.status_code == 400
        assert "reason" in r.json()["detail"].lower()

    def test_override_requires_at_least_one_field(self):
        result = _full_pipeline(_MINIMAL_ACHIEVEMENT)
        log_id = result["governance"]["log_id"]
        r = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "reviewer",
            "override_reason": "Some reason but no actual change",
        })
        assert r.status_code == 400

    def test_invalid_status_returns_400(self):
        result = _full_pipeline(_MINIMAL_ACHIEVEMENT)
        log_id = result["governance"]["log_id"]
        r = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "approved",  # invalid
            "reviewer_id": "reviewer",
        })
        assert r.status_code == 400

    def test_invalid_log_id_returns_404(self):
        r = client.post("/review", json={
            "log_id": "00000000-0000-0000-0000-000000000000",
            "reviewer_status": "accepted",
            "reviewer_id": "reviewer",
        })
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /logs pagination
# ---------------------------------------------------------------------------

class TestLogsEndpoint:

    @pytest.fixture(scope="class", autouse=True)
    def create_five_badges(self):
        """Create 5 log entries before these tests run."""
        for i in range(5):
            payload = {**_MINIMAL_SOUVENIR, "badge_title": f"Pagination Test Badge {i}"}
            _full_pipeline(payload)

    def test_get_logs_returns_list(self):
        r = client.get("/logs")
        assert r.status_code == 200
        data = r.json()
        assert "records" in data
        assert "total" in data
        assert isinstance(data["records"], list)

    def test_limit_parameter(self):
        r = client.get("/logs?limit=2")
        assert r.status_code == 200
        data = r.json()
        assert len(data["records"]) <= 2

    def test_offset_parameter(self):
        r1 = client.get("/logs?limit=100&offset=0")
        r2 = client.get("/logs?limit=100&offset=1")
        records1 = r1.json()["records"]
        records2 = r2.json()["records"]
        if len(records1) > 1:
            assert records1[0]["id"] != records2[0]["id"]

    def test_get_log_by_id(self):
        result = _full_pipeline({**_MINIMAL_SOUVENIR, "badge_title": "Get By ID Test"})
        log_id = result["governance"]["log_id"]
        r = client.get(f"/logs/{log_id}")
        assert r.status_code == 200
        log = r.json()
        assert log["id"] == log_id
        assert log["badge_title"] == "Get By ID Test"

    def test_get_log_404_for_unknown_id(self):
        r = client.get("/logs/nonexistent-id-12345")
        assert r.status_code == 404

    def test_limit_too_large_returns_422(self):
        r = client.get("/logs?limit=999")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# OBv3 JSON full pipeline
# ---------------------------------------------------------------------------

class TestOBv3Pipeline:

    def test_ldi_obv3_classifies_correctly(self):
        obv3 = {
            "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
            "type": ["Achievement"],
            "name": "AI Essentials",
            "description": "This foundation-level badge covers AI fundamentals for NJIT faculty. No prior experience with AI is required. This is the first course in the series.",
            "criteria": {
                "id": "https://njitcl.catalog.instructure.com/courses/MCAI.001.01",
                "narrative": "Passing knowledge checks with an 80% or higher score across all modules."
            },
            "achievementType": "Achievement"
        }
        r = client.post("/ingest", json={"input_type": "obv3_json", "payload": obv3})
        assert r.status_code == 200
        bfs = r.json()
        assert bfs["issuer"] == "LDI"

        r2 = client.post("/classify", json=bfs)
        assert r2.status_code == 200
        result = r2.json()
        assert result["classification"]["category"] == "Faculty & Staff Development"
        assert result["classification"]["type"] == "Achievement"
        assert result["explanation"] != ""

    def test_free_text_pipeline(self):
        free_text = (
            "The OSIL Leadership Badge is awarded to NJIT students who attend the full "
            "leadership workshop. This is a souvenir badge with no assessment required. "
            "Simply attend the event to earn this recognition."
        )
        r = client.post("/ingest", json={"input_type": "free_text", "payload": free_text})
        assert r.status_code == 200
        bfs = r.json()

        r2 = client.post("/classify", json=bfs)
        assert r2.status_code == 200
        result = r2.json()
        assert result["explanation"] != ""
        assert result["governance"]["log_id"] != ""
