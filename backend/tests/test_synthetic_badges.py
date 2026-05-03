"""
Phase 9 — Synthetic Badge Tests.

Tests 8 happy-path badges (HP01-HP08) and 5 edge-case badges (EC01-EC05)
directly through the normalizer + classify helper (no HTTP).

Happy path covers a spread of category / type / level combinations.
Edge cases verify graceful degradation for missing, conflicting, and
ambiguous inputs.
"""

import json
import os
import pytest
from pathlib import Path

from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.normalization.normalizer import normalize
from app.services.nlp.signal_extractor import SignalExtractor
from app.services.classification.engine import run_classification

_SAMPLE_DATA = Path(__file__).parent.parent.parent / "sample_data"
_EXTRACTOR = SignalExtractor(use_llm=False)


def _classify_form(file_path: Path) -> tuple:
    """
    Load a .form.json file, normalize it, run NLP, classify.
    Returns (bfs, result).
    """
    raw = json.loads(file_path.read_text())
    payload = {k: v for k, v in raw.items()
               if not k.startswith("_") and not k.startswith("expected_")}
    bfs = normalize("form", payload)
    bfs = _EXTRACTOR.extract_all(bfs)
    result = run_classification(bfs)
    return bfs, result


# ---------------------------------------------------------------------------
# HP01 — CPE | Souvenir | Souvenir
# ---------------------------------------------------------------------------

class TestHP01_CPE_Souvenir:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP01.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Continuing & Professional Education"

    def test_type(self, result):
        assert result.classification.type == "Souvenir"

    def test_level(self, result):
        assert result.classification.level == "Souvenir"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_rules(self, result):
        assert "S1R02" in result.rules_triggered
        assert "S2R05" in result.rules_triggered
        assert "S3S01" in result.rules_triggered


# ---------------------------------------------------------------------------
# HP02 — CPE | Achievement | Foundational (canvas seq 01)
# ---------------------------------------------------------------------------

class TestHP02_CPE_Achievement_Foundational:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP02.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Continuing & Professional Education"

    def test_type(self, result):
        assert result.classification.type == "Achievement"

    def test_level(self, result):
        assert result.classification.level == "Foundational"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_canvas_rule(self, result):
        assert "S3A05" in result.rules_triggered


# ---------------------------------------------------------------------------
# HP03 — CPE | Achievement | Milestone (canvas seq 02)
# ---------------------------------------------------------------------------

class TestHP03_CPE_Achievement_Milestone:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP03.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Continuing & Professional Education"

    def test_type(self, result):
        assert result.classification.type == "Achievement"

    def test_level(self, result):
        assert result.classification.level == "Milestone"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_canvas_rule(self, result):
        assert "S3A06" in result.rules_triggered


# ---------------------------------------------------------------------------
# HP04 — Faculty Dev | Achievement | Terminal (Micro Credential)
# ---------------------------------------------------------------------------

class TestHP04_FacultyDev_Achievement_Terminal:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP04.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Faculty & Staff Development"

    def test_type(self, result):
        assert result.classification.type == "Achievement"

    def test_level(self, result):
        assert result.classification.level == "Terminal"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_micro_credential_rule(self, result):
        assert "S2R01" in result.rules_triggered
        assert "S3A01" in result.rules_triggered


# ---------------------------------------------------------------------------
# HP05 — Faculty Dev | Souvenir | Souvenir (faculty attendance)
# ---------------------------------------------------------------------------

class TestHP05_FacultyDev_Souvenir:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP05.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Faculty & Staff Development"

    def test_type(self, result):
        assert result.classification.type == "Souvenir"

    def test_level(self, result):
        assert result.classification.level == "Souvenir"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"


# ---------------------------------------------------------------------------
# HP06 — Academic | Skill | Application (Makerspace practical)
# ---------------------------------------------------------------------------

class TestHP06_Academic_Skill_Application:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP06.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Academic"

    def test_type(self, result):
        assert result.classification.type == "Skill"

    def test_level(self, result):
        assert result.classification.level == "Application"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_S3SK02(self, result):
        assert "S3SK02" in result.rules_triggered


# ---------------------------------------------------------------------------
# HP07 — Co-Curricular | Competency | Demonstrated
# ---------------------------------------------------------------------------

class TestHP07_CoCurricular_Competency_Demonstrated:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP07.form.json")

    def test_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category == "Co-Curricular and Extra-Curricular"

    def test_type(self, bfs_result):
        _, r = bfs_result
        assert r.classification.type == "Competency"

    def test_level(self, bfs_result):
        _, r = bfs_result
        assert r.classification.level == "Demonstrated"

    def test_confidence(self, bfs_result):
        _, r = bfs_result
        assert r.classification.confidence == "High"

    def test_S3C03(self, bfs_result):
        _, r = bfs_result
        assert "S3C03" in r.rules_triggered


# ---------------------------------------------------------------------------
# HP08 — Academic | Skill | Mastery (Makerspace mentor)
# ---------------------------------------------------------------------------

class TestHP08_Academic_Skill_Mastery:

    @pytest.fixture(scope="class")
    def result(self):
        _, r = _classify_form(_SAMPLE_DATA / "synthetic_badges/happy_path/HP08.form.json")
        return r

    def test_category(self, result):
        assert result.classification.category == "Academic"

    def test_type(self, result):
        assert result.classification.type == "Skill"

    def test_level(self, result):
        assert result.classification.level == "Mastery"

    def test_confidence(self, result):
        assert result.classification.confidence == "High"

    def test_S3SK01(self, result):
        assert "S3SK01" in result.rules_triggered


# ===========================================================================
# EDGE CASES
# ===========================================================================

# ---------------------------------------------------------------------------
# EC01 — Missing issuer → needs_followup=True, confidence=Low, category=None
# ---------------------------------------------------------------------------

class TestEC01_MissingIssuer:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/edge_cases/EC01.form.json")

    def test_no_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category is None

    def test_confidence_low(self, bfs_result):
        _, r = bfs_result
        assert r.classification.confidence == "Low"

    def test_needs_followup(self, bfs_result):
        bfs, _ = bfs_result
        assert bfs.needs_followup_questions is True

    def test_issuer_in_missing_signals(self, bfs_result):
        bfs, _ = bfs_result
        assert "issuer" in bfs.missing_signals

    def test_S1R08_fired(self, bfs_result):
        _, r = bfs_result
        assert "S1R08" in r.rules_triggered


# ---------------------------------------------------------------------------
# EC02 — Conflicting level signals → confidence=Medium, conflict note
# ---------------------------------------------------------------------------

class TestEC02_ConflictingLevelSignals:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/edge_cases/EC02.form.json")

    def test_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category == "Faculty & Staff Development"

    def test_type(self, bfs_result):
        _, r = bfs_result
        assert r.classification.type == "Achievement"

    def test_confidence_not_high(self, bfs_result):
        # Title says "Foundations" → Foundational; description says "final course" → Terminal
        # or at minimum confidence should not be High due to conflict or OR criteria
        _, r = bfs_result
        assert r.classification.confidence in ("Medium", "Low")

    def test_explanation_present(self, bfs_result):
        _, r = bfs_result
        assert r.explanation != ""

    def test_review_recommended(self, bfs_result):
        _, r = bfs_result
        assert r.review_recommended is True


# ---------------------------------------------------------------------------
# EC03 — Achievement/Skill ambiguity (no assessment_evaluator, expert required)
# ---------------------------------------------------------------------------

class TestEC03_SkillAchievementAmbiguity:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/edge_cases/EC03.form.json")

    def test_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category == "Academic"

    def test_type_is_skill_or_achievement(self, bfs_result):
        _, r = bfs_result
        # expert_evaluation_required=True → should be Skill via S2R06
        # or Achievement with flag via S2R07 — either is acceptable
        assert r.classification.type in ("Skill", "Achievement")

    def test_low_or_medium_confidence(self, bfs_result):
        _, r = bfs_result
        # No assessment_evaluator → should not be High
        assert r.classification.confidence in ("Low", "Medium")

    def test_explanation_present(self, bfs_result):
        _, r = bfs_result
        assert r.explanation != ""


# ---------------------------------------------------------------------------
# EC04 — Compliance badge (badge_purpose=compliance)
# ---------------------------------------------------------------------------

class TestEC04_ComplianceBadge:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/edge_cases/EC04.form.json")

    def test_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category == "Faculty & Staff Development"

    def test_type_achievement(self, bfs_result):
        _, r = bfs_result
        # S2R04 fires before attendance S2R05 because badge_purpose=compliance
        assert r.classification.type == "Achievement"

    def test_S2R04_fired(self, bfs_result):
        _, r = bfs_result
        assert "S2R04" in r.rules_triggered

    def test_explanation_mentions_compliance(self, bfs_result):
        _, r = bfs_result
        assert "compliance" in r.explanation.lower() or "mandatory" in r.explanation.lower()


# ---------------------------------------------------------------------------
# EC05 — OR criteria logic → confidence reduced to Medium
# ---------------------------------------------------------------------------

class TestEC05_ORCriteriaLogic:

    @pytest.fixture(scope="class")
    def bfs_result(self):
        return _classify_form(_SAMPLE_DATA / "synthetic_badges/edge_cases/EC05.form.json")

    def test_category(self, bfs_result):
        _, r = bfs_result
        assert r.classification.category == "Faculty & Staff Development"

    def test_type(self, bfs_result):
        _, r = bfs_result
        assert r.classification.type == "Achievement"

    def test_criteria_logic_or(self, bfs_result):
        bfs, _ = bfs_result
        assert bfs.criteria_logic == "OR"

    def test_confidence_reduced(self, bfs_result):
        _, r = bfs_result
        assert r.classification.confidence == "Medium"

    def test_review_recommended(self, bfs_result):
        _, r = bfs_result
        assert r.review_recommended is True

    def test_explanation_mentions_or(self, bfs_result):
        _, r = bfs_result
        assert "or" in r.explanation.lower()
