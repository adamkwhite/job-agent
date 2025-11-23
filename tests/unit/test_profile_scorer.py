"""
Tests for ProfileScorer - profile-based job scoring
"""

import pytest

from src.agents.profile_scorer import ProfileScorer, score_job_for_profile
from src.utils.profile_manager import Profile


@pytest.fixture
def wes_style_profile():
    """Profile similar to Wesley's (robotics/hardware executive)"""
    return Profile(
        id="wes_test",
        name="Test Wes",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["vp", "director", "head of", "chief"],
            "domain_keywords": [
                "robotics",
                "automation",
                "hardware",
                "iot",
                "mechatronics",
            ],
            "role_types": {
                "engineering_leadership": ["engineering", "r&d", "technical"],
                "product_leadership": ["product", "cpo"],
            },
            "company_stage": ["series a", "series b", "growth"],
            "avoid_keywords": ["junior", "intern"],
            "location_preferences": {
                "remote_keywords": ["remote", "wfh", "anywhere"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto", "waterloo"],
                "preferred_regions": ["ontario", "canada"],
            },
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=True,
        notifications_min_grade="B",
        notifications_min_score=80,
    )


@pytest.fixture
def adam_style_profile():
    """Profile similar to Adam's (software/product)"""
    return Profile(
        id="adam_test",
        name="Test Adam",
        email="adam@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["senior", "staff", "lead", "principal"],
            "domain_keywords": ["software", "fullstack", "backend", "python", "data"],
            "role_types": {
                "engineering": ["software engineer", "developer"],
                "data": ["data engineer", "ml engineer"],
            },
            "company_stage": ["startup", "series a", "tech"],
            "avoid_keywords": ["junior", "intern", "sales"],
            "location_preferences": {
                "remote_keywords": ["remote", "wfh"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto", "ottawa"],
                "preferred_regions": ["ontario", "canada"],
            },
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=True,
        notifications_min_grade="F",
        notifications_min_score=0,
    )


class TestProfileScorer:
    """Test ProfileScorer scoring logic"""

    def test_score_vp_robotics_job_for_wes(self, wes_style_profile):
        """VP of Robotics should score highly for Wes-style profile"""
        scorer = ProfileScorer(wes_style_profile)

        job = {
            "title": "VP of Engineering",
            "company": "Robotics Startup",
            "location": "Remote, USA",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should score well: VP seniority + robotics domain + remote
        assert score >= 70
        assert grade in ["A", "B"]
        assert breakdown["seniority"] >= 25  # VP-level
        assert breakdown["domain"] >= 15  # robotics keyword
        assert breakdown["location"] == 15  # remote

    def test_score_senior_software_job_for_adam(self, adam_style_profile):
        """Senior Software Engineer should score well for Adam-style profile"""
        scorer = ProfileScorer(adam_style_profile)

        job = {
            "title": "Senior Software Engineer",
            "company": "Tech Startup",
            "location": "Toronto, Canada",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should score reasonably: senior level + software domain + toronto
        assert score >= 50
        assert breakdown["seniority"] >= 10  # senior level
        assert breakdown["domain"] >= 15  # software keyword
        assert breakdown["location"] >= 8  # toronto

    def test_score_junior_job_low(self, wes_style_profile):
        """Junior roles should score low"""
        scorer = ProfileScorer(wes_style_profile)

        job = {
            "title": "Junior Developer",
            "company": "Some Company",
            "location": "Unknown",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should score low: no seniority match, no domain match
        assert score < 50
        assert grade in ["D", "F"]

    def test_score_director_role(self, wes_style_profile):
        """Director roles should score well"""
        scorer = ProfileScorer(wes_style_profile)

        job = {
            "title": "Director of Hardware Engineering",
            "company": "IoT Solutions Inc",
            "location": "Waterloo, Ontario",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["seniority"] >= 20  # Director level
        assert breakdown["location"] >= 8  # Waterloo/Ontario

    def test_grade_thresholds(self, wes_style_profile):  # noqa: ARG002
        """Test grade calculation thresholds (using shared utility)"""
        from src.utils.scoring_utils import calculate_grade

        # Test grade boundaries
        assert calculate_grade(98) == "A"
        assert calculate_grade(97) == "B"
        assert calculate_grade(80) == "B"
        assert calculate_grade(79) == "C"
        assert calculate_grade(63) == "C"
        assert calculate_grade(62) == "D"
        assert calculate_grade(46) == "D"
        assert calculate_grade(45) == "F"
        assert calculate_grade(0) == "F"

    def test_location_scoring_remote(self, adam_style_profile):
        """Remote location should score 15 points"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("remote")
        assert score == 15

        score = scorer._score_location("wfh position")
        assert score == 15

    def test_location_scoring_hybrid_preferred(self, adam_style_profile):
        """Hybrid in preferred city should score 15 points"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("Hybrid - Toronto, ON")
        assert score == 15

    def test_location_scoring_preferred_city(self, adam_style_profile):
        """Preferred city should score 12 points"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("Toronto, Canada")
        assert score == 12

    def test_location_scoring_preferred_region(self, adam_style_profile):
        """Preferred region should score 8 points"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("Somewhere in Ontario")
        assert score == 8

    def test_location_scoring_no_match(self, adam_style_profile):
        """Non-matching location should score 0"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("San Francisco, CA")
        assert score == 0

    def test_location_scoring_empty(self, adam_style_profile):
        """Empty location should score 0"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_location("")
        assert score == 0

    def test_domain_scoring_multiple_matches(self, adam_style_profile):
        """Multiple domain keyword matches should score higher"""
        scorer = ProfileScorer(adam_style_profile)

        # 3+ matches = 25 points
        score = scorer._score_domain("software backend python developer", "tech startup")
        assert score >= 20

    def test_domain_scoring_no_matches(self, adam_style_profile):
        """No domain matches should score low but not zero"""
        scorer = ProfileScorer(adam_style_profile)

        score = scorer._score_domain("executive assistant", "law firm")
        assert score <= 10

    def test_technical_keywords_scoring(self, adam_style_profile):
        """Technical keywords should add bonus points"""
        scorer = ProfileScorer(adam_style_profile)

        # Multiple matches, max 10 points
        score = scorer._score_technical_keywords("python backend software engineer", "data company")
        assert score >= 6
        assert score <= 10


class TestScoreJobForProfile:
    """Test convenience function"""

    def test_score_job_for_existing_profile(self, mocker, wes_style_profile):
        """Test scoring job for an existing profile"""
        # Mock the profile manager
        mock_manager = mocker.Mock()
        mock_manager.get_profile.return_value = wes_style_profile
        mocker.patch("src.agents.profile_scorer.get_profile_manager", return_value=mock_manager)

        job = {"title": "VP Engineering", "company": "Robotics Co", "location": "Remote"}

        result = score_job_for_profile(job, "wes_test")

        assert result is not None
        score, grade, breakdown = result
        assert isinstance(score, int)
        assert grade in ["A", "B", "C", "D", "F"]
        assert isinstance(breakdown, dict)

    def test_score_job_for_nonexistent_profile(self, mocker):
        """Test scoring job for non-existent profile returns None"""
        mock_manager = mocker.Mock()
        mock_manager.get_profile.return_value = None
        mocker.patch("src.agents.profile_scorer.get_profile_manager", return_value=mock_manager)

        job = {"title": "Some Job", "company": "Some Company", "location": "Somewhere"}

        result = score_job_for_profile(job, "nonexistent")

        assert result is None
