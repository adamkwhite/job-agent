"""
Unit tests for ProfileScorer seniority scoring (Issue #311)

Verifies that ProfileScorer uses BaseScorer's relative seniority scoring
(Issue #244) instead of a hardcoded ladder. Jobs matching the candidate's
target_seniority get 30pts, one level away gets 25pts, etc.

Previous bug: ProfileScorer._score_seniority() override capped
senior/staff/principal at 15pts even when they were perfect matches.
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


@pytest.fixture
def profile_with_director_target():
    """Profile targeting director/VP roles (e.g., Wes)"""
    return Profile(
        id="test_director",
        name="Test Director Profile",
        email="test@example.com",
        enabled=True,
        email_username="test@example.com",
        email_app_password_env="TEST_PASSWORD",
        scoring={
            "target_seniority": ["director", "vp", "head of"],
            "domain_keywords": ["robotics", "hardware"],
            "role_types": {
                "engineering_leadership": ["engineering", "technical"],
                "product_leadership": ["product"],
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


class TestRelativeSeniorityScoring:
    """Verify BaseScorer relative scoring flows through ProfileScorer (Issue #311)"""

    def test_perfect_match_gets_30pts(self, profile_with_senior_target):
        """Senior Engineer (no 'manager') for a profile targeting senior → 30pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        # Use a title where "senior" is the only seniority keyword
        # "Senior Product Manager" has both senior(2) and manager(5) — highest wins
        job = {"title": "Senior Software Engineer", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30, (
            f"Perfect target match should get 30pts, got {breakdown['seniority']}"
        )

    def test_staff_perfect_match_gets_30pts(self, profile_with_senior_target):
        """Staff Engineer for a profile targeting staff → 30pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {"title": "Staff Software Engineer", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30

    def test_principal_perfect_match_gets_30pts(self, profile_with_senior_target):
        """Principal Engineer for a profile targeting principal → 30pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {"title": "Principal Software Engineer", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30

    def test_lead_perfect_match_gets_30pts(self, profile_with_senior_target):
        """Lead title for a profile targeting lead → 30pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {"title": "Product Lead", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30

    def test_one_level_away_gets_25pts(self, profile_with_senior_target):
        """Manager is one level above lead (level 5 vs target level 3) → distance varies"""
        scorer = ProfileScorer(profile_with_senior_target)
        # Target: senior(2), staff(2), lead(3), principal(2)
        # Architect is level 4, one away from lead(3) → 25pts
        job = {"title": "Software Architect", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 25

    def test_two_levels_away_gets_15pts(self, profile_with_senior_target):
        """Manager (level 5) is 2 away from lead (level 3) → 15pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {"title": "Engineering Manager", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 15

    def test_director_profile_perfect_match(self, profile_with_director_target):
        """Director title for a profile targeting director → 30pts"""
        scorer = ProfileScorer(profile_with_director_target)
        job = {"title": "Director of Engineering", "company": "Robotics Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30

    def test_vp_profile_perfect_match(self, profile_with_director_target):
        """VP title for a profile targeting VP → 30pts"""
        scorer = ProfileScorer(profile_with_director_target)
        job = {"title": "VP of Engineering", "company": "Robotics Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 30

    def test_no_seniority_keywords_gets_0pts(self, profile_with_senior_target):
        """Title with no seniority keywords → 0pts"""
        scorer = ProfileScorer(profile_with_senior_target)
        job = {"title": "Product Designer", "company": "Tech Co", "location": "Remote"}
        _score, _grade, breakdown, _ = scorer.score_job(job)
        assert breakdown["seniority"] == 0


class TestSeniorityProgressionProduct:
    """Test complete seniority progression for senior-targeting profile"""

    def test_progression_with_relative_scoring(self, profile_with_senior_target):
        """Verify full progression uses relative distances, not fixed ladder

        Note: _detect_seniority_level returns HIGHEST level found in title.
        "Senior Product Manager" → manager(5) wins over senior(2).
        "Junior Analyst" → analyst(1) wins over junior(0).
        """
        scorer = ProfileScorer(profile_with_senior_target)
        # Target levels: senior(2), staff(2), lead(3), principal(2) → unique: {2, 3}

        test_cases = [
            # (title, expected_points, reason)
            # Titles with single seniority keywords (unambiguous)
            ("Junior Designer", 15, "level 0, distance 2 from target 2"),
            ("Product Analyst", 25, "level 1, distance 1 from target 2"),
            ("Senior Software Engineer", 30, "level 2, perfect match"),
            ("Staff Software Engineer", 30, "level 2, perfect match"),
            ("Principal Data Scientist", 30, "level 2, perfect match"),
            ("Product Lead", 30, "level 3, perfect match"),
            ("Product Architect", 25, "level 4, distance 1 from target 3"),
            ("Engineering Manager", 15, "level 5, distance 2 from target 3"),
            ("Director of Product", 10, "level 6, distance 3 from target 3"),
            ("VP of Product", 5, "level 7, distance 4 from target 3"),
        ]

        for title, expected_pts, reason in test_cases:
            job = {"title": title, "company": "Tech Co", "location": "Remote"}
            _score, _grade, breakdown, _ = scorer.score_job(job)
            assert breakdown["seniority"] == expected_pts, (
                f"{title}: expected {expected_pts}pts ({reason}), got {breakdown['seniority']}pts"
            )


class TestMarioScenario:
    """Reproduce the exact bug from Issue #311"""

    def test_mario_senior_qa_engineer_gets_30pts(self):
        """Mario targets senior/staff/lead. Senior QA Engineer should get 30pts, not 15."""
        mario_profile = Profile(
            id="mario",
            name="Mario",
            email="mario@example.com",
            enabled=True,
            email_username="mario@example.com",
            email_app_password_env="MARIO_PASSWORD",
            scoring={
                "target_seniority": ["senior", "staff", "lead"],
                "domain_keywords": ["qa", "testing", "quality"],
                "role_types": {
                    "qa_engineering": ["qa", "quality", "test"],
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

        scorer = ProfileScorer(mario_profile)
        job = {"title": "Senior QA Engineer", "company": "Tech Co", "location": "Remote"}
        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["seniority"] == 30, (
            f"Mario's perfect target match should get 30pts, got {breakdown['seniority']}"
        )
        # With 30pts seniority, total should push into B grade territory
        assert score >= 70, f"Mario should get B+ grade, got {score} ({grade})"


class TestRegressionPrevention:
    """Ensure the override doesn't come back"""

    def test_profile_scorer_uses_base_scorer_seniority(self):
        """ProfileScorer should NOT override _score_seniority"""
        # If someone re-adds the override, this test fails
        assert not hasattr(ProfileScorer, "_score_seniority") or (
            ProfileScorer._score_seniority is ProfileScorer.__mro__[1]._score_seniority
        ), "ProfileScorer should not override BaseScorer._score_seniority()"
