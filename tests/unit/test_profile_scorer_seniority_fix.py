"""
Unit tests for ProfileScorer seniority scoring fix

Tests that "senior" keyword is correctly categorized as senior-level (15 pts)
instead of mid-level (10 pts) across all profiles.

Bug: "senior" was in mid_keywords, causing "Senior Product Manager" to score
as mid-level instead of senior-level.

Fix: Moved "senior" from mid_keywords to senior_keywords.
"""

import pytest

from agents.profile_scorer import ProfileScorer
from utils.profile_manager import Profile


@pytest.fixture
def profile_with_senior_target():
    """Profile targeting senior-level roles"""
    return Profile(
        id="test_senior",
        name="Test Senior Profile",
        email="test@example.com",
        enabled=True,
        email_username="test@example.com",
        email_app_password_env="TEST_PASSWORD",
        scoring={
            "target_seniority": ["senior", "staff", "lead", "principal"],
            "domain_keywords": ["software", "product", "technology"],
            "role_types": {
                "engineering": ["software engineer", "engineering"],
                "product": ["product manager", "product"],
            },
            "location_preferences": {"remote_keywords": ["remote"]},
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="B",
        notifications_min_score=80,
    )


class TestSeniorKeywordCategorization:
    """Test that 'senior' keyword is in senior_keywords, not mid_keywords"""

    def test_senior_product_manager_gets_senior_points(self, profile_with_senior_target):
        """Senior Product Manager should get 15 seniority points, not 10"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Senior Product Manager",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should get 15 points (senior-level), not 10 (mid-level)
        assert breakdown["seniority"] == 15, (
            f"Senior Product Manager should get 15 seniority points (senior-level), "
            f"got {breakdown['seniority']} (mid-level)"
        )

    def test_senior_software_engineer_gets_senior_points(self, profile_with_senior_target):
        """Senior Software Engineer should get 15 seniority points"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Senior Software Engineer",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["seniority"] == 15, (
            f"Senior Software Engineer should get 15 points, got {breakdown['seniority']}"
        )

    def test_product_manager_without_senior_gets_mid_points(self, profile_with_senior_target):
        """Product Manager (without Senior) should get 10 seniority points"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Product Manager",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should get 10 points (mid-level) since no "senior" keyword
        assert breakdown["seniority"] == 10, (
            f"Product Manager should get 10 seniority points (mid-level), "
            f"got {breakdown['seniority']}"
        )

    def test_staff_product_manager_gets_senior_points(self, profile_with_senior_target):
        """Staff Product Manager should get 15 seniority points"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Staff Product Manager",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["seniority"] == 15, (
            f"Staff Product Manager should get 15 points, got {breakdown['seniority']}"
        )

    def test_principal_software_engineer_gets_senior_points(self, profile_with_senior_target):
        """Principal Software Engineer should get 15 seniority points"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Principal Software Engineer",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should match role_type (engineering) AND get senior seniority points
        assert breakdown["role_type"] > 0, "Should match engineering role type"
        assert breakdown["seniority"] == 15, (
            f"Principal Software Engineer should get 15 points, got {breakdown['seniority']}"
        )


class TestSeniorityPointsProgression:
    """Test the complete seniority points progression"""

    def test_seniority_progression_product_roles(self, profile_with_senior_target):
        """Test seniority progression from PM to VP"""
        scorer = ProfileScorer(profile_with_senior_target)

        test_cases = [
            ("Product Manager", 10, "mid-level"),
            ("Senior Product Manager", 15, "senior-level"),
            ("Staff Product Manager", 15, "senior-level"),
            ("Principal Product Manager", 15, "senior-level"),
            ("Director of Product", 0, "not in target_seniority"),
            ("VP of Product", 0, "not in target_seniority"),
        ]

        for title, expected_points, description in test_cases:
            job = {"title": title, "company": "Tech Company", "location": "Remote"}
            score, grade, breakdown = scorer.score_job(job)

            assert breakdown["seniority"] == expected_points, (
                f"{title} should get {expected_points} points ({description}), "
                f"got {breakdown['seniority']}"
            )


class TestRegressionPrevention:
    """Prevent regression of the original bug"""

    def test_senior_not_in_mid_keywords(self, profile_with_senior_target):
        """Ensure 'senior' doesn't get categorized as mid-level again"""
        scorer = ProfileScorer(profile_with_senior_target)

        # Test multiple "Senior X" titles that match role_types
        senior_titles = [
            "Senior Product Manager",  # matches product role_type
            "Senior Software Engineer",  # matches engineering role_type
        ]

        for title in senior_titles:
            job = {"title": title, "company": "Tech Company", "location": "Remote"}
            score, grade, breakdown = scorer.score_job(job)

            # Should match role_type first
            assert breakdown["role_type"] > 0, f"{title} should match a role_type"

            # Then should get senior-level seniority points
            assert breakdown["seniority"] >= 15, (
                f"{title} should get at least 15 points (senior-level), "
                f"got {breakdown['seniority']} (likely matched mid-level)"
            )

    def test_lead_still_gets_mid_points(self, profile_with_senior_target):
        """Lead roles should still get 10 points (mid-level)"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {
            "title": "Product Lead",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # "Lead" is in mid_keywords and should get 10 points
        assert breakdown["seniority"] == 10, (
            f"Product Lead should get 10 points (mid-level), got {breakdown['seniority']}"
        )
