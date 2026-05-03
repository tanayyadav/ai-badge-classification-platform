"""
Phase 7 — Governance Logging tests.

Covers:
  - create_log: fields stored, initial reviewer_status, final_* seeded from recommended
  - update_log_review: accept flow, override flow, partial override (one stage only)
  - get_log: success and 404
  - get_all_logs: pagination, ordering by created_at desc
  - Review validation: overridden without reason, overridden with no override fields,
    invalid reviewer_status, invalid log_id
  - Full HTTP flows via TestClient covering Tests 1-4 from the spec

Uses an in-memory SQLite DB (DATABASE_URL=sqlite:///:memory:) so each test
class gets a fresh database with no pollution between test runs.
"""

import json
import os
import pytest

# Force in-memory DB before any app imports resolve DATABASE_URL
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.models.badge_fact_sheet import BadgeFactSheet
from app.models.governance_log import Base, GovernanceLog
from app.services.logging.governance_logger import (
    create_log,
    update_log_review,
    get_log,
    get_all_logs,
)
from app.services.nlp.signal_extractor import SignalExtractor
from app.services.classification.engine import run_classification
from database import get_db


# ---------------------------------------------------------------------------
# In-memory DB fixtures
# ---------------------------------------------------------------------------

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _fresh_db() -> Session:
    """Drop and recreate all tables, return a fresh session."""
    Base.metadata.drop_all(bind=_TEST_ENGINE)
    Base.metadata.create_all(bind=_TEST_ENGINE)
    return _TestSession()


# Override FastAPI's get_db to use in-memory DB
def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

# Re-create tables once for the TestClient tests
Base.metadata.create_all(bind=_TEST_ENGINE)

client = TestClient(app)

# Shared extractor
_extractor = SignalExtractor(use_llm=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bfs_and_result(
    title: str = "Test Badge",
    description: str = "A test badge.",
    criteria: str = "Attend the full workshop.",
    issuer: str = "LDI",
    assessment_required: str = "no",
    audience_type: str = "external_professional",
    **extra,
) -> tuple[BadgeFactSheet, object]:
    bfs = BadgeFactSheet(
        badge_title=title,
        badge_description=description,
        earning_criteria_text=criteria,
        issuer=issuer,
        assessment_required=assessment_required,
        audience_type=audience_type,
        **extra,
    )
    bfs = _extractor.extract_all(bfs)
    result = run_classification(bfs)
    return bfs, result


# ---------------------------------------------------------------------------
# create_log
# ---------------------------------------------------------------------------

class TestCreateLog:

    def test_log_stored_with_correct_fields(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        assert log.id is not None
        assert log.badge_title == "Test Badge"
        assert log.issuer == "LDI"
        assert log.reviewer_status == "pending"
        assert log.reviewed_at is None
        assert log.final_locked_decision is None
        db.close()

    def test_normalized_facts_is_valid_json(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        facts = json.loads(log.normalized_facts)
        assert facts["badge_title"] == "Test Badge"
        assert facts["issuer"] == "LDI"
        db.close()

    def test_extracted_signals_contains_only_section9_fields(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        signals = json.loads(log.extracted_signals)
        # Must contain NLP signal keys
        assert "needs_followup_questions" in signals
        assert "missing_signals" in signals
        # Must NOT contain non-NLP fields
        assert "badge_title" not in signals
        assert "issuer" not in signals
        db.close()

    def test_triggered_rules_is_valid_json_array(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        rules = json.loads(log.triggered_rules)
        assert isinstance(rules, list)
        assert len(rules) > 0
        db.close()

    def test_final_fields_seeded_from_recommended(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        assert log.final_category == log.recommended_category
        assert log.final_type == log.recommended_type
        assert log.final_level == log.recommended_level
        db.close()

    def test_explanation_text_stored(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        assert log.explanation_text
        assert "CATEGORY:" in log.explanation_text
        db.close()


# ---------------------------------------------------------------------------
# update_log_review — accept flow
# ---------------------------------------------------------------------------

class TestAcceptFlow:

    def test_accept_sets_reviewer_status(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id,
            reviewer_status="accepted",
            reviewer_id="reviewer_01",
            override_reason=None,
            override_category=None,
            override_type=None,
            override_level=None,
            db=db,
        )
        assert updated.reviewer_status == "accepted"
        assert updated.reviewer_id == "reviewer_01"
        db.close()

    def test_accept_sets_reviewed_at(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id, reviewer_status="accepted",
            reviewer_id="r", override_reason=None,
            override_category=None, override_type=None, override_level=None, db=db,
        )
        assert updated.reviewed_at is not None
        db.close()

    def test_accept_sets_final_locked_decision(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id, reviewer_status="accepted",
            reviewer_id="r", override_reason=None,
            override_category=None, override_type=None, override_level=None, db=db,
        )
        assert updated.final_locked_decision is not None
        assert " | " in updated.final_locked_decision
        db.close()

    def test_accept_does_not_change_final_values(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)
        rec_cat = log.recommended_category
        rec_type = log.recommended_type
        rec_level = log.recommended_level

        updated = update_log_review(
            log_id=log.id, reviewer_status="accepted",
            reviewer_id="r", override_reason=None,
            override_category=None, override_type=None, override_level=None, db=db,
        )
        assert updated.final_category == rec_cat
        assert updated.final_type == rec_type
        assert updated.final_level == rec_level
        db.close()

    def test_accept_clears_override_fields(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id, reviewer_status="accepted",
            reviewer_id="r", override_reason=None,
            override_category=None, override_type=None, override_level=None, db=db,
        )
        assert updated.override_category is None
        assert updated.override_type is None
        assert updated.override_level is None
        db.close()


# ---------------------------------------------------------------------------
# update_log_review — override flow
# ---------------------------------------------------------------------------

class TestOverrideFlow:

    def test_full_override_stores_all_three_stages(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id,
            reviewer_status="overridden",
            reviewer_id="reviewer_02",
            override_reason="Badge is actually for administrative compliance.",
            override_category="Administrative / Compliance",
            override_type="Achievement",
            override_level="Foundational",
            db=db,
        )
        assert updated.reviewer_status == "overridden"
        assert updated.override_category == "Administrative / Compliance"
        assert updated.override_type == "Achievement"
        assert updated.override_level == "Foundational"
        assert updated.final_category == "Administrative / Compliance"
        assert updated.final_type == "Achievement"
        assert updated.final_level == "Foundational"
        db.close()

    def test_partial_override_keeps_unchanged_stages_as_recommended(self):
        """Override only category — type and level fall back to recommended."""
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)
        rec_type = log.recommended_type
        rec_level = log.recommended_level

        updated = update_log_review(
            log_id=log.id,
            reviewer_status="overridden",
            reviewer_id="r",
            override_reason="Category needs correction.",
            override_category="Administrative / Compliance",
            override_type=None,
            override_level=None,
            db=db,
        )
        assert updated.final_category == "Administrative / Compliance"
        assert updated.final_type == rec_type
        assert updated.final_level == rec_level
        db.close()

    def test_override_locked_decision_format(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id,
            reviewer_status="overridden",
            reviewer_id="r",
            override_reason="Test override.",
            override_category="Admin",
            override_type=None,
            override_level=None,
            db=db,
        )
        assert "Admin" in updated.final_locked_decision
        assert " | " in updated.final_locked_decision
        db.close()

    def test_override_stores_reason(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        updated = update_log_review(
            log_id=log.id,
            reviewer_status="overridden",
            reviewer_id="r",
            override_reason="The category was wrong.",
            override_category="Academic",
            override_type=None,
            override_level=None,
            db=db,
        )
        assert updated.override_reason == "The category was wrong."
        db.close()


# ---------------------------------------------------------------------------
# get_log
# ---------------------------------------------------------------------------

class TestGetLog:

    def test_get_existing_log(self):
        db = _fresh_db()
        bfs, result = _make_bfs_and_result()
        log = create_log(bfs, result, db)

        fetched = get_log(log.id, db)
        assert fetched.id == log.id
        assert fetched.badge_title == "Test Badge"
        db.close()

    def test_get_nonexistent_log_raises_404(self):
        from fastapi import HTTPException
        db = _fresh_db()
        with pytest.raises(HTTPException) as exc_info:
            get_log("nonexistent-id-xyz", db)
        assert exc_info.value.status_code == 404
        db.close()


# ---------------------------------------------------------------------------
# get_all_logs — pagination
# ---------------------------------------------------------------------------

class TestGetAllLogs:

    def _insert_n_logs(self, db: Session, n: int) -> list[GovernanceLog]:
        logs = []
        for i in range(n):
            bfs, result = _make_bfs_and_result(
                title=f"Badge {i+1}",
                description=f"Badge number {i+1}.",
            )
            log = create_log(bfs, result, db)
            logs.append(log)
        return logs

    def test_total_count_is_correct(self):
        db = _fresh_db()
        self._insert_n_logs(db, 5)
        result = get_all_logs(limit=20, offset=0, db=db)
        assert result["total"] == 5
        db.close()

    def test_limit_respected(self):
        db = _fresh_db()
        self._insert_n_logs(db, 5)
        result = get_all_logs(limit=3, offset=0, db=db)
        assert len(result["records"]) == 3
        db.close()

    def test_offset_respected(self):
        db = _fresh_db()
        self._insert_n_logs(db, 5)
        result = get_all_logs(limit=3, offset=3, db=db)
        assert len(result["records"]) == 2
        db.close()

    def test_ordered_newest_first(self):
        db = _fresh_db()
        self._insert_n_logs(db, 3)
        result = get_all_logs(limit=10, offset=0, db=db)
        titles = [r.badge_title for r in result["records"]]
        # created_at is ascending by insert order, so desc means last inserted first
        assert titles[0] == "Badge 3"
        assert titles[-1] == "Badge 1"
        db.close()

    def test_empty_database_returns_zero(self):
        db = _fresh_db()
        result = get_all_logs(limit=20, offset=0, db=db)
        assert result["total"] == 0
        assert result["records"] == []
        db.close()


# ---------------------------------------------------------------------------
# HTTP integration tests — TestClient (Tests 1–4 from spec)
# ---------------------------------------------------------------------------

def _classify_via_http(badge_title: str, description: str, criteria: str,
                        issuer: str = "LDI", assessment_required: str = "no",
                        audience_type: str = "external_professional", **extra) -> dict:
    """POST /classify directly with a BFS payload and return the result."""
    payload = {
        "badge_title": badge_title,
        "badge_description": description,
        "earning_criteria_text": criteria,
        "issuer": issuer,
        "assessment_required": assessment_required,
        "audience_type": audience_type,
        **extra,
    }
    resp = client.post("/classify", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestHTTPAcceptFlow:
    """Test 1 — Full accept flow."""

    def test_accept_flow_end_to_end(self):
        # Classify
        result = _classify_via_http(
            badge_title="Infrastructure Forum",
            description="Badge for working professionals attending the infrastructure forum.",
            criteria="Attend the full Infrastructure Forum session. Attendees earn 6 PDH credits.",
            issuer="LDI",
            assessment_required="no",
            audience_type="external_professional",
        )
        log_id = result["governance"]["log_id"]
        assert log_id

        # Accept
        review_resp = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "accepted",
            "reviewer_id": "test_reviewer",
        })
        assert review_resp.status_code == 200
        reviewed = review_resp.json()
        assert reviewed["reviewer_status"] == "accepted"
        assert reviewed["final_locked_decision"] is not None
        assert reviewed["reviewed_at"] is not None

        # Verify via GET /logs/{log_id}
        get_resp = client.get(f"/logs/{log_id}")
        assert get_resp.status_code == 200
        log_detail = get_resp.json()
        assert log_detail["reviewer_status"] == "accepted"
        assert log_detail["final_locked_decision"] is not None
        assert log_detail["reviewed_at"] is not None


class TestHTTPOverrideFlow:
    """Test 2 — Full override flow (B026 CPT / OGI)."""

    def test_override_flow_end_to_end(self):
        # Classify
        result = _classify_via_http(
            badge_title="CPT Course for F-1 International Students",
            description="F-1 students. Mandatory to apply for CPT.",
            criteria="Complete the CPT module. This badge is mandatory to apply for CPT.",
            issuer="OGI",
            assessment_required="unknown",
            audience_type="njit_student",
        )
        log_id = result["governance"]["log_id"]

        # Override category only
        review_resp = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "test_reviewer",
            "override_reason": "OGI compliance badge — category confirmed as Administrative",
            "override_category": "Administrative / Compliance",
            "override_type": None,
            "override_level": None,
        })
        assert review_resp.status_code == 200
        reviewed = review_resp.json()
        assert reviewed["reviewer_status"] == "overridden"
        assert reviewed["final_category"] == "Administrative / Compliance"
        # Type and level unchanged from recommended
        assert reviewed["final_type"] == reviewed["recommended_type"]
        assert reviewed["final_level"] == reviewed["recommended_level"]
        assert reviewed["override_reason"] is not None

        # Verify via GET /logs/{log_id}
        log_detail = client.get(f"/logs/{log_id}").json()
        assert log_detail["reviewer_status"] == "overridden"
        assert log_detail["final_category"] == "Administrative / Compliance"
        assert log_detail["override_reason"] == "OGI compliance badge — category confirmed as Administrative"


class TestHTTPPagination:
    """Test 3 — Pagination across multiple classified badges."""

    def test_pagination(self):
        # Classify 5 badges
        log_ids = []
        for i in range(5):
            r = _classify_via_http(
                badge_title=f"Pagination Badge {i+1}",
                description=f"Test badge {i+1} for pagination.",
                criteria=f"Attend the full session {i+1}.",
            )
            log_ids.append(r["governance"]["log_id"])

        # First page: 3 records
        page1 = client.get("/logs?limit=3&offset=0").json()
        assert len(page1["records"]) == 3
        assert page1["limit"] == 3
        assert page1["offset"] == 0
        assert page1["total"] >= 5  # may include records from other tests

        # Second page: at least 2 records
        page2 = client.get("/logs?limit=3&offset=3").json()
        assert len(page2["records"]) >= 2

        # Default /logs returns records
        default_page = client.get("/logs").json()
        assert default_page["total"] >= 5
        assert len(default_page["records"]) >= 5


class TestHTTPValidationErrors:
    """Test 4 — Review validation error cases."""

    def _get_valid_log_id(self) -> str:
        r = _classify_via_http(
            badge_title="Validation Test Badge",
            description="For validation testing.",
            criteria="Attend the full event.",
        )
        return r["governance"]["log_id"]

    def test_overridden_without_reason_returns_400(self):
        log_id = self._get_valid_log_id()
        resp = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "r",
            "override_category": "Academic",
            # override_reason missing
        })
        assert resp.status_code == 400
        assert "override_reason" in resp.json()["detail"]

    def test_overridden_with_all_nulls_returns_400(self):
        log_id = self._get_valid_log_id()
        resp = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "overridden",
            "reviewer_id": "r",
            "override_reason": "Something changed",
            "override_category": None,
            "override_type": None,
            "override_level": None,
        })
        assert resp.status_code == 400
        assert "at least one" in resp.json()["detail"].lower()

    def test_invalid_reviewer_status_returns_400(self):
        log_id = self._get_valid_log_id()
        resp = client.post("/review", json={
            "log_id": log_id,
            "reviewer_status": "approved",  # invalid
            "reviewer_id": "r",
        })
        assert resp.status_code == 400

    def test_invalid_log_id_returns_404(self):
        resp = client.post("/review", json={
            "log_id": "does-not-exist-999",
            "reviewer_status": "accepted",
            "reviewer_id": "r",
        })
        assert resp.status_code == 404

    def test_get_nonexistent_log_returns_404(self):
        resp = client.get("/logs/does-not-exist-999")
        assert resp.status_code == 404
