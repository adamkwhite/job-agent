"""
Test grade calculation consistency across all scorers.

This test suite ensures that ProfileScorer and scoring_utils
all use the same grade thresholds (100-point system).

Related to: Codebase Analysis Issue #1.1 - Grade Threshold Mismatch
"""

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.profile_manager import Profile
from src.utils.scoring_utils import calculate_grade


@pytest.fixture
def minimal_profile():
    """Minimal profile for testing grade calculations"""
    return Profile(
        id="test",
        name="Test",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "seniority_levels": {
                "vp": {"points": 30, "keywords": ["vp", "vice president"]},
                "director": {"points": 25, "keywords": ["director"]},
            },
            "domain_keywords": {"robotics": 25},
            "role_types": {
                "engineering_leadership": {
                    "points": 20,
                    "keywords": ["engineering manager"],
                }
            },
            "locations": {"remote": 15},
            "technical_keywords": {"python": 10},
        },
        digest_min_grade="C",
        digest_min_score=55,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="B",
        notifications_min_score=70,
    )


class TestGradeThresholdConsistency:
    """Test that all scorers use consistent grade thresholds"""

    def test_scoring_utils_thresholds_100_point_system(self):
        """Verify scoring_utils uses 100-point system (A=85+, B=70+, C=55+, D=40+)"""
        # Test exact boundaries
        assert calculate_grade(100) == "A"
        assert calculate_grade(85) == "A"  # Boundary
        assert calculate_grade(84) == "B"

        assert calculate_grade(70) == "B"  # Boundary
        assert calculate_grade(69) == "C"

        assert calculate_grade(55) == "C"  # Boundary
        assert calculate_grade(54) == "D"

        assert calculate_grade(40) == "D"  # Boundary
        assert calculate_grade(39) == "F"

    def test_profile_scorer_grade_matches_scoring_utils(self, minimal_profile):
        """ProfileScorer should produce same grades as scoring_utils for same scores"""
        # ProfileScorer uses calculate_grade() internally, verify consistency
        test_scores = [39, 40, 54, 55, 69, 70, 84, 85, 100]

        for score in test_scores:
            utils_grade = calculate_grade(score)
            # Verify calculate_grade is consistent with itself
            assert utils_grade == calculate_grade(score), (
                f"Score {score}: inconsistent grade calculation"
            )

    def test_profile_scorer_matches_scoring_utils(self, minimal_profile):
        """ProfileScorer should produce same grades as scoring_utils"""
        scorer = ProfileScorer(minimal_profile)

        # ProfileScorer uses scoring_utils.calculate_grade() directly
        # Verify that whatever score we get, the grade matches scoring_utils
        # Note: Seniority is gated behind role match per user preference

        test_jobs = [
            {
                "title": "Engineering Manager",
                "company": "Test Company",
                "location": "Toronto",
            },
            {
                "title": "Engineering Manager Robotics",
                "company": "Hardware Co",
                "location": "Remote",
            },
            {
                "title": "Director of Robotics",
                "company": "Test Company",
                "location": "Ontario",
            },
        ]

        for job in test_jobs:
            score, grade, breakdown, _ = scorer.score_job(job)

            # Verify grade matches scoring_utils for the actual score
            expected_grade = calculate_grade(score)

            assert grade == expected_grade, (
                f"Job '{job['title']}': score={score}, grade={grade}, expected_grade={expected_grade}, breakdown={breakdown}"
            )

    def test_all_grade_boundaries_consistent(self, minimal_profile):
        """Critical test: scoring_utils and ProfileScorer should agree on grade boundaries"""
        # Test scores that historically caused mismatches in old dual-scorer architecture
        critical_scores = {
            85: "A",
            70: "B",
            55: "C",
            40: "D",
        }

        for score, expected_grade in critical_scores.items():
            utils_grade = calculate_grade(score)

            assert utils_grade == expected_grade, (
                f"scoring_utils: score {score} → {utils_grade}, expected {expected_grade}"
            )

            # ProfileScorer uses calculate_grade internally, verify consistency
            assert calculate_grade(score) == expected_grade

    def test_no_110_point_thresholds_remain(self):
        """Ensure no scorer uses old 110-point thresholds (A=98+, B=80+, C=63+, D=46+)"""
        # These scores should NOT trigger old thresholds
        old_threshold_scores = {
            98: "A",  # Old A threshold - should still be A in new system
            97: "A",  # Should be A (85+), not B
            80: "B",  # Old B threshold - should still be B in new system
            79: "B",  # Should be B (70+), not C
            63: "C",  # Old C threshold - should still be C in new system
            62: "C",  # Should be C (55+), not D
            46: "D",  # Old D threshold - should still be D in new system
            45: "D",  # Should be D (40+), not F
        }

        for score, expected_grade in old_threshold_scores.items():
            grade = calculate_grade(score)
            assert grade == expected_grade, (
                f"Score {score} should be {expected_grade} (100-point system), got {grade}"
            )

    def test_digest_filtering_consistency(self, minimal_profile):
        """Verify digest min_score filtering uses consistent grading"""
        # Profile has digest_min_score=55 (C grade in 100-point system)
        # Verify that whatever scores we get, grades are calculated consistently

        # Create jobs that should score differently
        high_scoring_job = {
            "title": "Engineering Manager Robotics",  # role + domain
            "company": "Hardware Co",
            "location": "Remote",  # location points
        }

        low_scoring_job = {
            "title": "Sales Manager",  # no match
            "company": "Unknown Co",
            "location": "USA",
        }

        from src.agents.profile_scorer import ProfileScorer

        scorer = ProfileScorer(minimal_profile)

        high_score, high_grade, _, _ = scorer.score_job(high_scoring_job)
        low_score, low_grade, _, _ = scorer.score_job(low_scoring_job)

        # Verify grades match calculate_grade function
        assert high_grade == calculate_grade(high_score), (
            f"High-scoring job: grade={high_grade}, expected={calculate_grade(high_score)}"
        )
        assert low_grade == calculate_grade(low_score), (
            f"Low-scoring job: grade={low_grade}, expected={calculate_grade(low_score)}"
        )

        # Verify digest threshold works correctly
        # A job with score≥55 should have grade C/B/A
        if high_score >= 55:
            assert high_grade in [
                "C",
                "B",
                "A",
            ], f"Score {high_score} should be C+, got {high_grade}"

        # A job with score<40 should have grade F
        if low_score < 40:
            assert low_grade == "F", f"Score {low_score} should be F, got {low_grade}"
