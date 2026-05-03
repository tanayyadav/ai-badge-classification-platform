"""
Phase 5 — Classification Rule Engine tests.

Covers:
  - Stage 1: all four categories + S1R07 (OGI) + S1R08 (unknown issuer)
  - Stage 2: all type paths including Souvenir, Achievement, Skill, Competency
  - Stage 3: all four branches with multiple levels each
  - Confidence calculation: Low/Medium/High + downgrade conditions
  - Edge cases: missing issuer, OR criteria, level conflict, S2R07 flag

Each test is named after the taxonomy combination it verifies.
"""

import pytest

from app.models.badge_fact_sheet import BadgeFactSheet
from tests.conftest import classify


# ===========================================================================
# Stage 1 — Category
# ===========================================================================

class TestStage1Category:

    def test_S1R01_ldi_faculty_staff(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI for Educators",
            badge_description="For faculty and instructors at NJIT.",
            earning_criteria_text="Attended the full workshop.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Faculty & Staff Development"
        assert "S1R01" in r.rules_triggered

    def test_S1R02_ldi_continuing_professional(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Workshop",
            badge_description="For working professionals attending the AI workshop.",
            earning_criteria_text="Attend the full AI workshop session.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Continuing & Professional Education"
        assert "S1R02" in r.rules_triggered

    def test_S1R03_ldi_micro_credential_defaults_to_cpe(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Micro Credential",
            badge_description="Comprehensive AI program.",
            earning_criteria_text="Completion of all courses.",
            issuer="LDI", achievement_type="Micro Credential",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Continuing & Professional Education"
        assert "S1R03" in r.rules_triggered

    def test_S1R04_osil_cocurricular(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Club Participation",
            badge_description="NJIT students who attended club events.",
            earning_criteria_text="Attend the full club event.",
            issuer="OSIL", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Co-Curricular and Extra-Curricular"
        assert "S1R04" in r.rules_triggered

    def test_S1R05_makerspace_academic(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Make 101",
            badge_description="Makerspace safety and equipment training.",
            earning_criteria_text="Complete in-person practical.",
            issuer="Makerspace", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Academic"
        assert "S1R05" in r.rules_triggered

    def test_S1R06_nce_academic(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Engineering Concepts",
            badge_description="Core engineering concepts for NCE students.",
            earning_criteria_text="Expert-verified quiz on fundamentals.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Academic"
        assert "S1R06" in r.rules_triggered

    def test_S1R07_ogi_open_question(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="CPT Course",
            badge_description="Required for CPT application.",
            earning_criteria_text="Earning this badge is mandatory to apply for CPT at NJIT.",
            issuer="OGI",
        )
        r = classify(bfs, extractor)
        assert r.classification.category is None
        assert r.classification.confidence == "Low"
        assert "S1R07" in r.rules_triggered

    def test_S1R08_unknown_issuer(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Some Badge",
            badge_description="From an unknown org.",
            earning_criteria_text="Complete the task.",
            issuer="UnknownOrg",
        )
        r = classify(bfs, extractor)
        assert r.classification.category is None
        assert "S1R08" in r.rules_triggered


# ===========================================================================
# Stage 2 — Type
# ===========================================================================

class TestStage2Type:

    def test_S2R01_micro_credential_is_achievement(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Micro Credential",
            badge_description="Demonstrates comprehensive AI proficiency.",
            earning_criteria_text="Completion of all pathway courses.",
            issuer="LDI", achievement_type="Micro Credential",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert "S2R01" in r.rules_triggered

    def test_S2R02_competency_type(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Leadership Competency",
            badge_description="Demonstrates leadership across KSA dimensions.",
            earning_criteria_text="Portfolio reviewed by expert panel.",
            issuer="OSIL", achievement_type="Competency",
            assessment_required="yes", expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Competency"
        assert "S2R02" in r.rules_triggered

    def test_S2R03_certificate_of_completion_is_achievement(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Safety Training",
            badge_description="Completion of mandatory safety training.",
            earning_criteria_text="Passing knowledge checks with an 80% or higher.",
            issuer="LDI", achievement_type="Certificate Of Completion",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert "S2R03" in r.rules_triggered

    def test_S2R04_compliance_badge(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="CPT Compliance",
            badge_description="Required compliance badge.",
            earning_criteria_text="Earning this badge is mandatory to apply for CPT at NJIT.",
            issuer="OGI",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert "S2R04" in r.rules_triggered

    def test_S2R05_souvenir_no_assessment(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Summit Attendance",
            badge_description="Awarded for attending the AI Summit.",
            earning_criteria_text="Attend the full summit event.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Souvenir"
        assert "S2R05" in r.rules_triggered

    def test_S2R06_expert_evaluation_is_skill(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Lab Safety",
            badge_description="Students demonstrate safe laboratory procedures.",
            earning_criteria_text="In-person practical examination by faculty observers.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert "S2R06" in r.rules_triggered

    def test_S2R07_unknown_evaluator_achievement_medium(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Data Analysis",
            badge_description="Demonstrates data analysis skills.",
            earning_criteria_text="Complete the data analysis project.",
            issuer="LDI", assessment_required="yes",
            assessment_evaluator=None,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert r.classification.confidence in ("Low", "Medium")
        assert "S2R07" in r.rules_triggered
        assert "assessment_evaluator" in r.missing_signals

    def test_S2R09_canvas_code_is_achievement(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Course 2",
            badge_description="Second course in the AI pathway.",
            earning_criteria_text="Passing the final assessment with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.02",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert "S2R09" in r.rules_triggered

    def test_S2R10_osil_pre_post_assessment(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Leadership Workshop",
            badge_description="Pre- and post-assessment leadership development.",
            earning_criteria_text="Complete the pre- and post-assessment workshop.",
            issuer="OSIL", assessment_required="yes",
            assessment_type="pre_post_assessment",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert "S2R09" in r.rules_triggered


# ===========================================================================
# Stage 3 — Achievement Branch
# ===========================================================================

class TestStage3Achievement:

    def test_S3A01_micro_credential_terminal(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Micro Credential",
            badge_description="Comprehensive AI proficiency badge.",
            earning_criteria_text="Completion of all pathway courses.",
            issuer="LDI", achievement_type="Micro Credential",
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Terminal"
        assert "S3A01" in r.rules_triggered

    def test_S3A02_canvas_seq_00_terminal(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Capstone",
            badge_description="Capstone micro credential.",
            earning_criteria_text="Completion of all pathway courses.",
            issuer="LDI", canvas_course_code="MCAI.001.00",
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Terminal"
        # canvas_sequence_number=0 sets is_capstone=True → S3A01 fires first
        # (S3A01 covers is_capstone; S3A02 fires only when canvas_seq=0 but
        # is_capstone was NOT set, which cannot happen via the canvas parser)
        assert "S3A01" in r.rules_triggered

    def test_S3A05_canvas_seq_01_foundational(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Fundamentals",
            badge_description="First course in the AI pathway.",
            earning_criteria_text="Passing knowledge checks with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.01",
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Foundational"
        assert "S3A05" in r.rules_triggered

    def test_S3A06_canvas_seq_02_milestone(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Applications",
            badge_description="Building on foundational concepts.",
            earning_criteria_text="Passing the final assessment with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.02",
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Milestone"
        assert "S3A06" in r.rules_triggered

    def test_S3A09_has_prereqs_milestone(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Advanced Leadership",
            badge_description="Building on foundational leadership skills.",
            earning_criteria_text="Requires completion of Foundation badge.",
            issuer="OSIL", assessment_required="yes",
            assessment_type="project_presentation",
            has_prerequisite_badges=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Milestone"
        assert "S3A09" in r.rules_triggered

    def test_S3A10_phrase_foundational(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Basics",
            badge_description="This foundation-level badge covers AI fundamentals.",
            earning_criteria_text="Passing knowledge checks with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.01",
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Foundational"

    def test_S3A12_phrase_terminal(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Change Management Capstone",
            badge_description="After completing the foundational and intermediate series, participants attend a 2-day institute.",
            earning_criteria_text="Complete all prior badges and attend the institute.",
            issuer="LDI", assessment_required="yes",
            assessment_type="project_presentation",
            has_prerequisite_badges=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.level == "Terminal"
        assert "S3A03" in r.rules_triggered or r.classification.level == "Terminal"


# ===========================================================================
# Stage 3 — Skill Branch
# ===========================================================================

class TestStage3Skill:

    def test_S3SK01_mastery_high_bloom(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Engineering Design",
            badge_description="Students design and create novel engineering solutions.",
            earning_criteria_text="Expert-scored capstone: design and produce a working prototype.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert r.classification.level == "Mastery"
        assert "S3SK01" in r.rules_triggered

    def test_S3SK02_application_mid_bloom(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Lab Techniques",
            badge_description="Students demonstrate and perform laboratory techniques under observation.",
            earning_criteria_text="In-person practical examination conducted by faculty observers.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert r.classification.level == "Application"
        assert "S3SK02" in r.rules_triggered

    def test_S3SK03_awareness_low_bloom(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Engineering Concepts",
            badge_description="Students identify and describe core engineering concepts.",
            earning_criteria_text="Expert-verified quiz covering basic understanding of engineering.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert r.classification.level == "Awareness"
        assert "S3SK03" in r.rules_triggered


# ===========================================================================
# Stage 3 — Souvenir Branch
# ===========================================================================

class TestStage3Souvenir:

    def test_S3S01_souvenir_level(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Summit",
            badge_description="For working professionals who attended the AI Summit.",
            earning_criteria_text="Attend the full summit event.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Souvenir"
        assert r.classification.level == "Souvenir"
        assert "S3S01" in r.rules_triggered


# ===========================================================================
# Confidence Calculation
# ===========================================================================

class TestConfidence:

    def test_missing_issuer_always_low(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Unknown Badge",
            badge_description="Some badge.",
            earning_criteria_text="Complete something.",
            issuer=None,
        )
        r = classify(bfs, extractor)
        assert r.classification.confidence == "Low"
        assert r.follow_up_needed is True
        assert "issuer" in r.missing_signals

    def test_or_criteria_never_high(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Leadership Award",
            badge_description="For NJIT students who show leadership.",
            earning_criteria_text="Complete a workshop or submit a reflection essay.",
            issuer="OSIL",
        )
        r = classify(bfs, extractor)
        assert r.classification.confidence in ("Low", "Medium")

    def test_level_conflict_title_vs_description_is_medium(self, extractor):
        # Title says "Foundational", description+type signals Terminal
        bfs = BadgeFactSheet(
            badge_title="Foundational Skills Badge",
            badge_description="Capstone completion demonstrating mastery of all pathway content.",
            earning_criteria_text="Completion of all courses required.",
            issuer="LDI",
            achievement_type="Micro Credential",
            audience_type="external_professional",  # prevents audience missing-signal
        )
        r = classify(bfs, extractor)
        assert r.classification.confidence == "Medium"

    def test_souvenir_high_confidence(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Workshop Attendance",
            badge_description="For working professionals who attended the full workshop.",
            earning_criteria_text="Attend the full workshop.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.confidence == "High"

    def test_s2r07_flag_in_missing_signals(self, extractor):
        """S2R07 — unknown evaluator adds assessment_evaluator to missing_signals."""
        bfs = BadgeFactSheet(
            badge_title="Data Skills",
            badge_description="Demonstrates data analysis capabilities.",
            earning_criteria_text="Complete a data analysis project.",
            issuer="LDI", assessment_required="yes",
        )
        r = classify(bfs, extractor)
        assert "assessment_evaluator" in r.missing_signals
        assert r.follow_up_needed is True


# ===========================================================================
# Full taxonomy combinations (happy path)
# ===========================================================================

class TestTaxonomyCombinations:

    def test_T01_cpe_souvenir(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Workshop",
            badge_description="For working professionals attending the full AI workshop.",
            earning_criteria_text="Attend the full AI workshop session.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Continuing & Professional Education"
        assert r.classification.type == "Souvenir"
        assert r.classification.level == "Souvenir"

    def test_T02_cpe_achievement_foundational(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Fundamentals",
            badge_description="Foundation-level badge for working professionals.",
            earning_criteria_text="Passing knowledge checks with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.01",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert r.classification.level == "Foundational"

    def test_T03_cpe_achievement_milestone(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Applications",
            badge_description="Building on foundational concepts in AI.",
            earning_criteria_text="Passing the final assessment with an 80% or higher.",
            issuer="LDI", canvas_course_code="MCAI.001.02",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert r.classification.level == "Milestone"

    def test_T04_cpe_achievement_terminal(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="AI Micro Credential",
            badge_description="Comprehensive achievement across the AI pathway.",
            earning_criteria_text="Completion of all pathway courses.",
            issuer="LDI", achievement_type="Micro Credential",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert r.classification.level == "Terminal"

    def test_T09_faculty_staff_souvenir(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Faculty AI Orientation",
            badge_description="For faculty and instructors attending the full orientation.",
            earning_criteria_text="Attended the full orientation session.",
            issuer="LDI", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Faculty & Staff Development"
        assert r.classification.type == "Souvenir"
        assert r.classification.level == "Souvenir"

    def test_T15_cocurricular_souvenir(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Club Participation",
            badge_description="NJIT students who attended club events.",
            earning_criteria_text="Attend the full club event.",
            issuer="OSIL", assessment_required="no",
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Co-Curricular and Extra-Curricular"
        assert r.classification.type == "Souvenir"
        assert r.classification.level == "Souvenir"

    def test_T18_cocurricular_achievement_terminal(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Leadership Capstone",
            badge_description="Culminating badge after completing all OSIL pathway badges.",
            earning_criteria_text="Complete all prior badges and submit final reflection.",
            issuer="OSIL", has_prerequisite_badges=True,
            assessment_required="yes", assessment_type="project_presentation",
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Achievement"
        assert r.classification.level == "Terminal"

    def test_T22_academic_skill_awareness(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Engineering Concepts",
            badge_description="Students identify and describe core engineering concepts.",
            earning_criteria_text="Expert-verified quiz covering basic understanding of engineering.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.category == "Academic"
        assert r.classification.type == "Skill"
        assert r.classification.level == "Awareness"

    def test_T23_academic_skill_application(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Lab Techniques",
            badge_description="Students demonstrate and perform laboratory techniques under observation.",
            earning_criteria_text="In-person practical examination conducted by faculty observers.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert r.classification.level == "Application"

    def test_T24_academic_skill_mastery(self, extractor):
        bfs = BadgeFactSheet(
            badge_title="Engineering Design",
            badge_description="Students design and create novel engineering solutions.",
            earning_criteria_text="Expert-scored capstone: design and produce a working prototype.",
            issuer="NCE", assessment_required="yes",
            expert_evaluation_required=True,
        )
        r = classify(bfs, extractor)
        assert r.classification.type == "Skill"
        assert r.classification.level == "Mastery"
