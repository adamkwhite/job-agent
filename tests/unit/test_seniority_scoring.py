"""
Tests for independent seniority scoring (Issue #219)

Verifies that seniority points are awarded independently of role type,
allowing users to filter by seniority alone without requiring role type matches.
"""

import pytest

from src.agents.profile_scorer import ProfileScorer
from src.utils.profile_manager import Profile


@pytest.fixture
def test_profile():
    """Create a test profile that targets director/VP roles"""
    return Profile(
        id="test",
        name="Test User",
        email="test@example.com",
        enabled=True,
        email_username="test@example.com",
        email_app_password_env="TEST_PASSWORD",
        scoring={
            "target_seniority": ["director", "vp", "vice president", "chief"],
            "role_types": {
                "engineering": ["engineering", "technical", "product"],
                "product": ["product", "product management"],
            },
            "domain_keywords": ["robotics", "hardware"],
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto"],
                "preferred_regions": ["ontario"],
            },
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="A",
        notifications_min_score=90,
    )


def test_director_of_marketing_scores_seniority_without_role_match(test_profile):
    """
    Test: "Director of Marketing" should score seniority independently of role type

    Before fix: seniority silenced to 0 because role=0
    After fix: seniority awarded independently (30 points due to "cto" substring match)

    Note: The 30 points is due to a known substring matching issue where "cto"
    matches in "director of". This is separate from the silencing bug being fixed.
    """
    scorer = ProfileScorer(test_profile)
    job = {
        "title": "Director of Marketing",
        "company": "Tech Corp",
        "location": "Remote",
    }

    score, grade, breakdown, classification = scorer.score_job(job)

    # Seniority should score non-zero (currently 30 due to cto substring)
    assert breakdown["seniority"] > 0, "Director title should score seniority points"

    # Role type should score 0 (marketing not in target roles)
    assert breakdown["role_type"] == 0, "Marketing role should score 0 points"

    # Total should be non-zero due to seniority
    assert score > 0, "Job should have non-zero score from seniority alone"


def test_vp_of_finance_scores_seniority_without_role_match(test_profile):
    """
    Test: "VP of Finance" should score seniority=30, role=0

    Before fix: seniority silenced to 0 because role=0
    After fix: seniority=30 awarded independently
    """
    scorer = ProfileScorer(test_profile)
    job = {
        "title": "VP of Finance",
        "company": "Startup Inc",
        "location": "Toronto, ON",
    }

    score, grade, breakdown, classification = scorer.score_job(job)

    # Seniority should score 30 (VP level)
    assert breakdown["seniority"] == 30, "VP title should score 30 points"

    # Role type should score 0 (finance not in target roles)
    assert breakdown["role_type"] == 0, "Finance role should score 0 points"

    # Total should be non-zero due to seniority
    assert score > 0, "Job should have non-zero score from seniority alone"


def test_director_of_engineering_scores_both_seniority_and_role(test_profile):
    """
    Test: "Director of Engineering" should score both seniority and role independently

    This ensures the fix doesn't break the normal case where both should score.

    Note: Seniority scores 30 points (not 25) due to "cto" substring match.
    This is a known issue separate from the silencing bug being fixed.
    """
    scorer = ProfileScorer(test_profile)
    job = {
        "title": "Director of Engineering",
        "company": "Robotics Co",
        "location": "Remote",
    }

    score, grade, breakdown, classification = scorer.score_job(job)

    # Both seniority and role should score
    assert breakdown["seniority"] > 0, "Director title should score seniority points"
    assert breakdown["role_type"] == 20, "Engineering role should score 20 points"

    # Total should include both
    assert score >= 20, "Job should score at least role type points"
