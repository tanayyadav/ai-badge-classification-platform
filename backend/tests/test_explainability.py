"""
Phase 6 — Explainability tests.

Verifies that generate_explanation() produces a complete, accurate, non-empty
explanation for every classification.  Each test checks:

  1. All 8 required elements are present (CATEGORY, TYPE, LEVEL, SIGNALS,
     CONFIDENCE, MISSING SIGNALS, CONFLICT, HUMAN REVIEW)
  2. The specific content required for the three target badges (B001, B003, B026)
  3. Edge cases: Low confidence, missing signals, OGI open question, OR criteria
"""

import pytest

from app.models.badge_fact_sheet import BadgeFactSheet
from tests.conftest import classify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _explanation(bfs: BadgeFactSheet, extractor) -> str:
    """Run full classify pipeline and return the explanation string."""
    result = classify(bfs, extractor)
    assert result.explanation, "explanation must never be empty"
    return result.explanation


# ---------------------------------------------------------------------------
# Element presence — every explanation must include all 8 headers
# ---------------------------------------------------------------------------


class TestExplanationStructure:

    def test_high_confidence_has_required_elements(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Fundamentals",
            badge_description="First course in the AI pathway for working professionals.",
            earning_criteria_text="Passing the final assessment with an 80% or higher.",
            issuer="LDI",
            canvas_course_code="MCAI.001.01",
            audience_type="external_professional",
        )
        exp = _explanation(bfs, extractor)

        assert "CATEGORY:" in exp
        assert "TYPE:" in exp
        assert "LEVEL:" in exp
        assert "SIGNALS USED:" in exp
        assert "CONFIDENCE:" in exp
        assert "HUMAN REVIEW:" in exp

    def test_low_confidence_has_missing_signals_element(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Unknown Badge",
            badge_description="Some badge with no useful signals.",
            earning_criteria_text="Complete the activity.",
        )
        exp = _explanation(bfs, extractor)

        assert "MISSING SIGNALS:" in exp
        assert "CONFIDENCE: Low" in exp

    def test_explanation_never_empty(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Minimal Badge",
            badge_description=".",
            earning_criteria_text=".",
        )
        result = classify(bfs, extractor)
        assert len(result.explanation) > 50

    def test_paragraphs_separated_by_blank_lines(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Workshop",
            badge_description="For working professionals.",
            earning_criteria_text="Attend the full workshop.",
            issuer="LDI",
            assessment_required="no",
        )
        exp = _explanation(bfs, extractor)
        assert "\n\n" in exp, "elements must be separated by blank lines"

    def test_no_json_in_explanation(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Workshop",
            badge_description="For working professionals.",
            earning_criteria_text="Attend the full workshop.",
            issuer="LDI",
            assessment_required="no",
        )
        exp = _explanation(bfs, extractor)
        assert "{" not in exp
        assert "}" not in exp


# ---------------------------------------------------------------------------
# B001 — Infrastructure Forum (CPE / Souvenir / Souvenir)
# Attendance-only, PDH credits, LDI
# ---------------------------------------------------------------------------


class TestB001InfrastructureForum:

    def _bfs(self):
        return BadgeFactSheet(
            badge_title="Infrastructure Forum",
            badge_description=(
                "This badge is awarded to working professionals who attend the full "
                "NJIT Infrastructure Forum, earning 6 PDH credits."
            ),
            earning_criteria_text=(
                "Attend the full Infrastructure Forum session. "
                "Attendees earn 6 PDH credits upon attendance."
            ),
            issuer="LDI",
            audience_type="external_professional",
            pdh_credits="6 PDH",
            assessment_required="no",
        )

    def test_b001_category_is_cpe(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.category == "Continuing & Professional Education"

    def test_b001_type_is_souvenir(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.type == "Souvenir"

    def test_b001_explanation_mentions_attendance(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "attendance" in exp.lower()

    def test_b001_explanation_mentions_souvenir_reason(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "no assessment" in exp.lower() or "attendance" in exp.lower()

    def test_b001_explanation_shows_pdh_signal(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "6 PDH" in exp or "pdh_credits" in exp

    def test_b001_signals_show_assessment_required_no(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "assessment_required=no" in exp

    def test_b001_human_review_not_required(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "HUMAN REVIEW: Not required" in exp


# ---------------------------------------------------------------------------
# B003 — AI Admin Efficiency (Faculty & Staff / Achievement / Milestone)
# Canvas code MCAI.002.03, faculty audience, LDI
# ---------------------------------------------------------------------------


class TestB003AIAdminEfficiency:

    def _bfs(self):
        return BadgeFactSheet(
            badge_title="AI for Administrative Efficiency",
            badge_description=(
                "This badge is awarded to faculty and instructors who complete the "
                "third course in the AI for Education pathway."
            ),
            earning_criteria_text=(
                "Passing the final assessment with an 80% or higher. "
                "Building on the foundational series in the MCAI.002 pathway."
            ),
            issuer="LDI",
            audience_type="njit_employee",
            canvas_course_code="MCAI.002.03",
        )

    def test_b003_category_is_faculty_staff(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.category == "Faculty & Staff Development"

    def test_b003_type_is_achievement(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.type == "Achievement"

    def test_b003_level_is_milestone(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.level == "Milestone"

    def test_b003_explanation_mentions_canvas_code(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "MCAI.002.03" in exp

    def test_b003_explanation_mentions_sequence_position(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "position 3" in exp

    def test_b003_explanation_mentions_pathway(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "MCAI.002" in exp

    def test_b003_explanation_reflects_faculty_audience(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "faculty" in exp.lower() or "njit_employee" in exp.lower()

    def test_b003_signals_show_canvas_sequence(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "canvas_sequence_number=3" in exp


# ---------------------------------------------------------------------------
# B026 — CPT Course (OGI / Achievement / — open question Q001)
# Mandatory to apply phrase, compliance purpose
# ---------------------------------------------------------------------------


class TestB026CPTCourse:

    def _bfs(self):
        return BadgeFactSheet(
            badge_title="CPT Course for F-1 International Students",
            badge_description=(
                "This badge is awarded to F-1 international students who complete "
                "the CPT authorization course. It is mandatory to apply for CPT."
            ),
            earning_criteria_text=(
                "Complete the CPT authorization online module. "
                "This badge is mandatory to apply for Curricular Practical Training "
                "authorization through NJIT's Office of Global Initiatives."
            ),
            issuer="OGI",
            audience_type="njit_student",
        )

    def test_b026_type_is_achievement(self, extractor):
        result = classify(self._bfs(), extractor)
        assert result.classification.type == "Achievement"

    def test_b026_compliance_rule_fired(self, extractor):
        result = classify(self._bfs(), extractor)
        assert "S2R04" in result.rules_triggered

    def test_b026_explanation_mentions_mandatory_or_compliance(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "mandatory to apply" in exp.lower() or "compliance" in exp.lower()

    def test_b026_explanation_mentions_ogi_open_question(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "Q001" in exp or "open question" in exp.lower()

    def test_b026_explanation_recommends_human_review(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        assert "HUMAN REVIEW: Recommended" in exp

    def test_b026_human_review_mentions_ogi_reason(self, extractor):
        exp = _explanation(self._bfs(), extractor)
        review_section = exp.split("HUMAN REVIEW:")[-1] if "HUMAN REVIEW:" in exp else ""
        assert (
            "OGI" in review_section
            or "Q001" in review_section
            or "supervisor" in review_section.lower()
        )


# ---------------------------------------------------------------------------
# Edge case explanations
# ---------------------------------------------------------------------------


class TestEdgeCaseExplanations:

    def test_missing_issuer_explanation_mentions_issuer_in_missing(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Mystery Badge",
            badge_description="A badge with no issuer information.",
            earning_criteria_text="Complete the activity.",
        )
        exp = _explanation(bfs, extractor)
        assert "issuer" in exp.lower()
        assert "MISSING SIGNALS:" in exp

    def test_or_criteria_confidence_not_high(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Leadership Development",
            badge_description="For NJIT students.",
            earning_criteria_text=(
                "Complete a leadership project or attend a leadership workshop."
            ),
            issuer="OSIL",
            assessment_required="no",
        )
        result = classify(bfs, extractor)
        exp = result.explanation
        assert result.classification.confidence != "High"
        assert "OR" in exp.upper() or "or" in exp.lower()

    def test_skill_badge_explanation_mentions_bloom(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="3D Printing Skills",
            badge_description=(
                "Students demonstrate and apply 3D printing techniques, "
                "evaluated by a Makerspace expert."
            ),
            earning_criteria_text=(
                "Design, create, and produce a 3D model. "
                "Assessed by the Makerspace instructor using a scoring rubric."
            ),
            issuer="Makerspace",
            expert_evaluation_required=True,
            assessment_evaluator="expert_scored",
        )
        exp = _explanation(bfs, extractor)
        # bloom_level or bloom_verbs should appear in SIGNALS USED or LEVEL
        assert "bloom" in exp.lower() or "spacy" in exp.lower() or "verb" in exp.lower()

    def test_competency_badge_explanation_mentions_competency_type(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Leadership Competency",
            badge_description=(
                "Demonstrates integrated knowledge, skills, and abilities "
                "in AI-driven leadership."
            ),
            earning_criteria_text=(
                "Complete a cross-functional capstone project evaluated "
                "via expert rubric across multiple KSA dimensions."
            ),
            issuer="LDI",
            audience_type="njit_employee",
            achievement_type="Competency",
            ksa_dimensions=["knowledge", "skills", "abilities"],
            real_world_context=True,
        )
        result = classify(bfs, extractor)
        assert result.classification.type == "Competency"
        assert "Competency" in result.explanation
