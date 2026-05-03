"""
Phase 9 — Real Badge Tests.

Tests all 8 badges in test_manifest.json through the full pipeline:
  POST /ingest (form input) → POST /classify → verify category, type, level, confidence

Uses an in-memory SQLite DB so no test pollution.
"""

import json
import os
import pytest
from pathlib import Path

# Force in-memory DB before app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.governance_log import Base
from database import get_db


# ---------------------------------------------------------------------------
# In-memory DB setup
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

_CLIENT = TestClient(app)

# ---------------------------------------------------------------------------
# Load manifest and badge data from sample_data/
# ---------------------------------------------------------------------------

_SAMPLE_DATA = Path(__file__).parent.parent.parent / "sample_data"
_MANIFEST = json.loads((_SAMPLE_DATA / "test_manifest.json").read_text())


def _load_badge(badge_id: str) -> dict:
    """Load the form JSON for a badge from sample_data/real_badges/."""
    entry = _MANIFEST[badge_id]
    return json.loads((_SAMPLE_DATA / entry["file"]).read_text())


def _run_badge(badge_id: str) -> dict:
    """
    Run the full pipeline for a badge:
      1. POST /ingest with form data
      2. POST /classify with the returned BFS
    Returns the ClassificationResult dict.
    """
    form_data = _load_badge(badge_id)
    # Strip metadata keys that don't belong in the form payload
    payload = {k: v for k, v in form_data.items() if not k.startswith("_") and not k.startswith("expected_")}

    ingest_resp = _CLIENT.post("/ingest", json={"input_type": "form", "payload": payload})
    assert ingest_resp.status_code == 200, f"Ingest failed for {badge_id}: {ingest_resp.text}"

    bfs = ingest_resp.json()
    classify_resp = _CLIENT.post("/classify", json=bfs)
    assert classify_resp.status_code == 200, f"Classify failed for {badge_id}: {classify_resp.text}"

    return classify_resp.json()


# ---------------------------------------------------------------------------
# B001 — OSIL Souvenir
# ---------------------------------------------------------------------------

class TestB001:
    """OSIL event souvenir — no assessment, Co-Curricular | Souvenir | Souvenir."""

    def test_category(self):
        r = _run_badge("B001")
        assert r["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self):
        r = _run_badge("B001")
        assert r["classification"]["type"] == "Souvenir"

    def test_level(self):
        r = _run_badge("B001")
        assert r["classification"]["level"] == "Souvenir"

    def test_confidence(self):
        r = _run_badge("B001")
        assert r["classification"]["confidence"] == "High"

    def test_rules(self):
        r = _run_badge("B001")
        assert "S1R04" in r["rules_triggered"]
        assert "S2R05" in r["rules_triggered"]
        assert "S3S01" in r["rules_triggered"]

    def test_explanation_present(self):
        r = _run_badge("B001")
        assert r["explanation"] != ""
        assert len(r["explanation"]) > 50


# ---------------------------------------------------------------------------
# B003 — AI Admin Efficiency (MCAI.002.03, LDI faculty)
# ---------------------------------------------------------------------------

class TestB003:
    """LDI MCAI.002.03 — Faculty Dev | Achievement | Milestone."""

    def test_category(self):
        r = _run_badge("B003")
        assert r["classification"]["category"] == "Faculty & Staff Development"

    def test_type(self):
        r = _run_badge("B003")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B003")
        assert r["classification"]["level"] == "Milestone"

    def test_confidence(self):
        r = _run_badge("B003")
        assert r["classification"]["confidence"] == "High"

    def test_canvas_rule_S3A07(self):
        r = _run_badge("B003")
        assert "S3A07" in r["rules_triggered"]

    def test_canvas_signal_in_signals(self):
        r = _run_badge("B003")
        assert "canvas_sequence_number" in r["signals_used"]
        assert r["signals_used"]["canvas_sequence_number"]["value"] == 3


# ---------------------------------------------------------------------------
# B004 — AI for Educators Foundational (MCAI.002.01)
# ---------------------------------------------------------------------------

class TestB004:
    """LDI MCAI.002.01 — Faculty Dev | Achievement | Foundational."""

    def test_category(self):
        r = _run_badge("B004")
        assert r["classification"]["category"] == "Faculty & Staff Development"

    def test_type(self):
        r = _run_badge("B004")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B004")
        assert r["classification"]["level"] == "Foundational"

    def test_confidence(self):
        r = _run_badge("B004")
        assert r["classification"]["confidence"] == "High"

    def test_canvas_S3A05(self):
        r = _run_badge("B004")
        assert "S3A05" in r["rules_triggered"]


# ---------------------------------------------------------------------------
# B005 — LDI Micro Credential (CPE Terminal)
# ---------------------------------------------------------------------------

class TestB005:
    """LDI Micro Credential — CPE | Achievement | Terminal."""

    def test_category(self):
        r = _run_badge("B005")
        assert r["classification"]["category"] == "Continuing & Professional Education"

    def test_type(self):
        r = _run_badge("B005")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B005")
        assert r["classification"]["level"] == "Terminal"

    def test_confidence(self):
        r = _run_badge("B005")
        assert r["classification"]["confidence"] == "High"

    def test_S3A01_micro_credential(self):
        r = _run_badge("B005")
        assert "S3A01" in r["rules_triggered"]
        assert "S2R01" in r["rules_triggered"]


# ---------------------------------------------------------------------------
# B018 — OSIL Capstone
# ---------------------------------------------------------------------------

class TestB018:
    """OSIL Capstone — Co-Curricular | Achievement | Terminal."""

    def test_category(self):
        r = _run_badge("B018")
        assert r["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self):
        r = _run_badge("B018")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B018")
        assert r["classification"]["level"] == "Terminal"

    def test_confidence(self):
        r = _run_badge("B018")
        assert r["classification"]["confidence"] == "High"

    def test_terminal_rule(self):
        r = _run_badge("B018")
        # S3A03 fires (has_prerequisite_badges=True AND "capstone" in title)
        # S3A04 would also match but S3A03 is checked first
        rules = r["rules_triggered"]
        assert "S3A03" in rules or "S3A04" in rules


# ---------------------------------------------------------------------------
# B019 — OSIL Foundational
# ---------------------------------------------------------------------------

class TestB019:
    """OSIL Leadership Foundations — Co-Curricular | Achievement | Foundational."""

    def test_category(self):
        r = _run_badge("B019")
        assert r["classification"]["category"] == "Co-Curricular and Extra-Curricular"

    def test_type(self):
        r = _run_badge("B019")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B019")
        assert r["classification"]["level"] == "Foundational"

    def test_confidence(self):
        r = _run_badge("B019")
        assert r["classification"]["confidence"] == "High"

    def test_level_signal_foundational(self):
        r = _run_badge("B019")
        # Should fire S3A10 (NLP phrase → Foundational) or S3A05 (no canvas code)
        rules = r["rules_triggered"]
        assert "S3A10" in rules or "S3A05" in rules


# ---------------------------------------------------------------------------
# B022 — Makerspace Skill Application
# ---------------------------------------------------------------------------

class TestB022:
    """Makerspace expert-scored practical — Academic | Skill | Application."""

    def test_category(self):
        r = _run_badge("B022")
        assert r["classification"]["category"] == "Academic"

    def test_type(self):
        r = _run_badge("B022")
        assert r["classification"]["type"] == "Skill"

    def test_level(self):
        r = _run_badge("B022")
        assert r["classification"]["level"] == "Application"

    def test_confidence(self):
        r = _run_badge("B022")
        assert r["classification"]["confidence"] == "High"

    def test_S3SK02_application(self):
        r = _run_badge("B022")
        assert "S3SK02" in r["rules_triggered"]

    def test_bloom_in_signals(self):
        r = _run_badge("B022")
        # bloom_level should be present in signals_used
        assert "bloom_level" in r["signals_used"]


# ---------------------------------------------------------------------------
# B026 — OGI CPT Compliance
# ---------------------------------------------------------------------------

class TestB026:
    """OGI CPT compliance — category=None | Achievement | Foundational | Low confidence."""

    def test_category_is_none(self):
        r = _run_badge("B026")
        assert r["classification"]["category"] is None

    def test_type(self):
        r = _run_badge("B026")
        assert r["classification"]["type"] == "Achievement"

    def test_level(self):
        r = _run_badge("B026")
        assert r["classification"]["level"] == "Foundational"

    def test_confidence_low(self):
        r = _run_badge("B026")
        assert r["classification"]["confidence"] == "Low"

    def test_review_recommended(self):
        r = _run_badge("B026")
        assert r["review_recommended"] is True

    def test_S1R07_fired(self):
        r = _run_badge("B026")
        assert "S1R07" in r["rules_triggered"]

    def test_S2R04_compliance(self):
        r = _run_badge("B026")
        assert "S2R04" in r["rules_triggered"]

    def test_explanation_has_compliance_reference(self):
        r = _run_badge("B026")
        exp = r["explanation"].lower()
        assert "compliance" in exp or "mandatory" in exp
