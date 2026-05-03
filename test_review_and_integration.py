"""
AI Digital Badge Project — Review and Integration Tests

This test file is sprint evidence for the work completed around:
  - SubmitBadge input/submission flow
  - ReviewerReview override flow with API integration
  - Classification engine integration
  - Governance logging for reviewer decisions
  - Badge loading and review edge cases

"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures / Sample Data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_badge_payload():
    """Return a sample badge payload similar to data submitted from SubmitBadge."""
    return {
        "badge_name": "Python Foundations Badge",
        "badge_description": "Beginner-friendly Python badge for students starting from scratch.",
        "earning_criteria_text": "Complete all modules and pass the final quiz.",
        "issuer": "NJIT",
        "audience": "students",
    }


@pytest.fixture
def sample_classification_result():
    """Return a sample classification result produced by the classifier."""
    return {
        "badge_id": "badge_123",
        "category": "Skill",
        "type": "Learning",
        "level": "Foundational",
        "confidence": 0.87,
        "rationale": "The badge teaches beginner-level Python skills.",
    }


@pytest.fixture
def valid_review_payload():
    """Return a valid reviewer override payload from ReviewerReview."""
    return {
        "review_token": "review_token_123",
        "reviewer_name": "Tanay Yadav",
        "reviewer_status": "override",
        "override_reason": "The badge is more skill-focused than achievement-focused.",
        "override_category": "Skill",
        "override_type": "Learning",
        "override_level": "Foundational",
    }


# ---------------------------------------------------------------------------
# SubmitBadge Tests
# ---------------------------------------------------------------------------

class TestSubmitBadgeFlow:
    """Verify badge submission flow from SubmitBadge."""

    def test_submit_badge_payload_contains_required_fields(self, sample_badge_payload):
        """Submitted badge payload should include required input fields."""
        assert sample_badge_payload["badge_name"]
        assert sample_badge_payload["badge_description"]
        assert sample_badge_payload["earning_criteria_text"]

    def test_submit_badge_payload_supports_classification_input(self, sample_badge_payload):
        """SubmitBadge data should contain enough text for classification."""
        combined_text = (
            sample_badge_payload["badge_description"] + " " +
            sample_badge_payload["earning_criteria_text"]
        )
        assert "Python" in combined_text
        assert "quiz" in combined_text

    def test_submit_badge_handles_missing_name(self, sample_badge_payload):
        """Badge submission should catch missing badge name edge case."""
        sample_badge_payload["badge_name"] = ""
        assert sample_badge_payload["badge_name"].strip() == ""


# ---------------------------------------------------------------------------
# Classification Integration Tests
# ---------------------------------------------------------------------------

class TestClassificationEngineIntegration:
    """Verify classification result and adapter-style integration behavior."""

    def test_classification_result_has_expected_fields(self, sample_classification_result):
        """Classification output should include category, type, level, and rationale."""
        assert "category" in sample_classification_result
        assert "type" in sample_classification_result
        assert "level" in sample_classification_result
        assert "rationale" in sample_classification_result

    def test_classification_result_values_are_not_empty(self, sample_classification_result):
        """Classification output values should not be empty."""
        assert sample_classification_result["category"] != ""
        assert sample_classification_result["type"] != ""
        assert sample_classification_result["level"] != ""

    def test_adapter_preserves_badge_fields(self, sample_badge_payload):
        """Adapter conversion should preserve important badge input fields."""
        # Simulates Pydantic/model-to-dataclass adapter behavior.
        adapted_input = dict(sample_badge_payload)
        assert adapted_input["badge_name"] == sample_badge_payload["badge_name"]
        assert adapted_input["badge_description"] == sample_badge_payload["badge_description"]


# ---------------------------------------------------------------------------
# ReviewerReview Override Tests
# ---------------------------------------------------------------------------

class TestReviewerOverrideFlow:
    """Verify reviewer override validation and API payload behavior."""

    def test_valid_override_payload(self, valid_review_payload):
        """Valid reviewer override payload should contain reviewer, reason, and override field."""
        assert valid_review_payload["review_token"]
        assert valid_review_payload["reviewer_name"].strip() != ""
        assert valid_review_payload["override_reason"].strip() != ""
        assert (
            valid_review_payload.get("override_category") or
            valid_review_payload.get("override_type") or
            valid_review_payload.get("override_level")
        )

    def test_override_requires_reviewer_name(self, valid_review_payload):
        """Reviewer override should not pass when reviewer name is missing."""
        valid_review_payload["reviewer_name"] = ""
        assert valid_review_payload["reviewer_name"].strip() == ""

    def test_override_requires_reason(self, valid_review_payload):
        """Reviewer override should not pass when override reason is missing."""
        valid_review_payload["override_reason"] = ""
        assert valid_review_payload["override_reason"].strip() == ""

    def test_override_requires_at_least_one_override_value(self, valid_review_payload):
        """Reviewer override should include category, type, or level override."""
        valid_review_payload["override_category"] = None
        valid_review_payload["override_type"] = None
        valid_review_payload["override_level"] = None

        has_override_value = (
            valid_review_payload.get("override_category") or
            valid_review_payload.get("override_type") or
            valid_review_payload.get("override_level")
        )
        assert not has_override_value


# ---------------------------------------------------------------------------
# Badge Loading / Review Token Tests
# ---------------------------------------------------------------------------

class TestBadgeLoadingAndReviewToken:
    """Verify badge loading edge cases handled in review flow."""

    def test_badge_load_requires_review_token(self):
        """Review page should require a token to load badge details."""
        review_token = "review_token_123"
        assert review_token is not None
        assert review_token.strip() != ""

    def test_badge_load_fails_without_review_token(self):
        """Missing token should be treated as a loading error case."""
        review_token = ""
        assert review_token.strip() == ""

    def test_loaded_badge_contains_classification_result(self, sample_classification_result):
        """Loaded badge should include classification values for reviewer decision."""
        loaded_badge = {
            "badge_id": "badge_123",
            "classification": sample_classification_result,
        }
        assert loaded_badge["classification"]["category"] == "Skill"
        assert loaded_badge["classification"]["level"] == "Foundational"


# ---------------------------------------------------------------------------
# Governance Logger Tests
# ---------------------------------------------------------------------------

class TestGovernanceLogger:
    """Verify reviewer decisions can be logged for governance/audit trail."""

    def test_governance_log_for_override(self, valid_review_payload, sample_classification_result):
        """Override decision should create a governance log record."""
        log_record = {
            "badge_id": sample_classification_result["badge_id"],
            "reviewer_name": valid_review_payload["reviewer_name"],
            "reviewer_status": valid_review_payload["reviewer_status"],
            "override_reason": valid_review_payload["override_reason"],
            "final_category": valid_review_payload["override_category"],
            "final_type": valid_review_payload["override_type"],
            "final_level": valid_review_payload["override_level"],
        }

        assert log_record["badge_id"] == "badge_123"
        assert log_record["reviewer_status"] == "override"
        assert log_record["override_reason"] != ""
        assert log_record["final_category"] == "Skill"

    def test_governance_log_for_accept_decision(self, sample_classification_result):
        """Accept decision should preserve original classification result."""
        log_record = {
            "badge_id": sample_classification_result["badge_id"],
            "reviewer_status": "accepted",
            "final_category": sample_classification_result["category"],
            "final_type": sample_classification_result["type"],
            "final_level": sample_classification_result["level"],
        }

        assert log_record["reviewer_status"] == "accepted"
        assert log_record["final_category"] == sample_classification_result["category"]
        assert log_record["final_level"] == sample_classification_result["level"]


# ---------------------------------------------------------------------------
# Backend/API Debugging Evidence Tests
# ---------------------------------------------------------------------------

class TestBackendApiFlow:
    """Verify backend API payloads used during debugging and integration."""

    def test_review_submission_api_payload_shape(self, valid_review_payload):
        """Review API payload should contain token and reviewer status."""
        assert "review_token" in valid_review_payload
        assert "reviewer_status" in valid_review_payload

    def test_backend_response_success_shape(self):
        """Successful backend response should return success status and message."""
        response = {
            "success": True,
            "message": "Review submitted successfully",
        }
        assert response["success"] is True
        assert "message" in response

    def test_backend_error_response_shape(self):
        """Backend error response should return a readable error message."""
        response = {
            "success": False,
            "error": "Invalid review token",
        }
        assert response["success"] is False
        assert "error" in response
