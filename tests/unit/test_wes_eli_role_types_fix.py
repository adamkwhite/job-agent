"""
Unit tests for Wes and Eli role_types domain keyword fixes

Tests that domain-specific leadership titles properly match role_types
across all profiles, preventing critical scoring failures.

Bug: "Head of Robotics" scored 42/F for Wes (should be 80/B)
      "Head of FinTech" scored F for Eli (should be 80/B)

Root Cause: role_types didn't include domain keywords like "robotics", "fintech"
Result: 0 role_type + 0 seniority = automatic FAIL

Fix: Added domain keywords to role_types for proper matching.
"""

import pytest

from agents.profile_scorer import ProfileScorer
from utils.profile_manager import Profile


@pytest.fixture
def eli_profile():
    """Eli's profile inline for CI-safe testing"""
    return Profile(
        id="eli",
        name="Eli",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["director", "vp", "head of", "chief", "cto", "cpo"],
            "domain_keywords": [
                "fintech",
                "healthtech",
                "proptech",
                "insurtech",
                "edtech",
                "regtech",
                "legaltech",
            ],
            "role_types": {
                "engineering_leadership": [
                    "engineering",
                    "technical",
                    "cto",
                    "vp engineering",
                    "director engineering",
                    "fintech",
                    "healthtech",
                    "saas",
                ],
            },
            "location_preferences": {
                "remote_keywords": ["remote"],
                "hybrid_keywords": ["hybrid"],
                "preferred_cities": ["toronto"],
                "preferred_regions": ["ontario", "canada"],
            },
            "filtering": {
                "aggression_level": "moderate",
                "hardware_company_boost": 10,
                "software_company_penalty": -20,
            },
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


class TestWesRoboticsKeywords:
    """Test Wes's profile recognizes robotics domain leadership roles"""

    def test_robotics_in_role_types(self, wes_profile):
        """Verify 'robotics' is in Wes's role_types"""
        role_types = wes_profile.scoring.get("role_types", {})
        all_keywords = []
        for keywords in role_types.values():
            all_keywords.extend(keywords)

        assert "robotics" in all_keywords, "Wes's role_types should include 'robotics' keyword"

    def test_automation_in_role_types(self, wes_profile):
        """Verify 'automation' is in Wes's role_types"""
        role_types = wes_profile.scoring.get("role_types", {})
        all_keywords = []
        for keywords in role_types.values():
            all_keywords.extend(keywords)

        assert "automation" in all_keywords, "Wes's role_types should include 'automation' keyword"

    def test_head_of_robotics_scores_b_grade(self, wes_profile):
        """Head of Robotics should score B grade (70+), not F (42)"""
        scorer = ProfileScorer(wes_profile)
        job = {
            "title": "Head of Robotics",
            "company": "Robotics Company",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        # Should get role_type match
        assert breakdown["role_type"] > 0, "Should match robotics role_type"

        # Should get seniority points (depends on role_type > 0)
        assert breakdown["seniority"] >= 25, (
            f"Head of should get 25+ seniority points, got {breakdown['seniority']}"
        )

        # Should score A grade overall (with hardware company boost)
        assert score >= 85, (
            f"Head of Robotics should score at least 85 for Wes (with hardware boost), got {score}/100 ({grade})"
        )
        assert grade in ["A", "B"], f"Expected A or B grade, got {grade}"

    def test_director_of_automation_scores_b_grade(self, wes_profile):
        """Director of Automation should score A or B grade (with hardware boost)"""
        scorer = ProfileScorer(wes_profile)
        job = {
            "title": "Director of Automation",
            "company": "Automation Inc",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should match automation role_type"
        assert breakdown["seniority"] >= 25, "Director should get 25+ seniority"
        assert score >= 70, f"Should score 70+ (with hardware boost), got {score}/100"
        assert grade in ["A", "B"], f"Expected A or B grade (with hardware boost), got {grade}"

    def test_vp_of_manufacturing_scores_b_grade(self, wes_profile):
        """VP of Manufacturing should score A or B grade (with hardware boost)"""
        scorer = ProfileScorer(wes_profile)
        job = {
            "title": "VP of Manufacturing",
            "company": "Manufacturing Co",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should match manufacturing role_type"
        assert breakdown["seniority"] == 30, "VP should get 30 seniority points"
        assert score >= 70, f"Should score 70+ (with hardware boost), got {score}/100"
        assert grade in ["A", "B"], f"Expected A or B grade (with hardware boost), got {grade}"


class TestEliDomainKeywords:
    """Test Eli's profile recognizes fintech/healthtech/saas leadership roles"""

    def test_fintech_in_role_types(self, eli_profile):
        """Verify 'fintech' is in Eli's role_types"""
        role_types = eli_profile.scoring.get("role_types", {})
        all_keywords = []
        for keywords in role_types.values():
            all_keywords.extend(keywords)

        assert "fintech" in all_keywords, "Eli's role_types should include 'fintech' keyword"

    def test_healthtech_in_role_types(self, eli_profile):
        """Verify 'healthtech' is in Eli's role_types"""
        role_types = eli_profile.scoring.get("role_types", {})
        all_keywords = []
        for keywords in role_types.values():
            all_keywords.extend(keywords)

        assert "healthtech" in all_keywords, "Eli's role_types should include 'healthtech' keyword"

    def test_saas_in_role_types(self, eli_profile):
        """Verify 'saas' is in Eli's role_types"""
        role_types = eli_profile.scoring.get("role_types", {})
        all_keywords = []
        for keywords in role_types.values():
            all_keywords.extend(keywords)

        assert "saas" in all_keywords, "Eli's role_types should include 'saas' keyword"

    def test_head_of_fintech_scores_b_grade(self, eli_profile):
        """Head of FinTech should score B grade (70+), not F"""
        scorer = ProfileScorer(eli_profile)
        job = {
            "title": "Head of FinTech",
            "company": "Financial Company",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should match fintech role_type"
        assert breakdown["seniority"] >= 25, "Head of should get 25+ seniority"
        assert score >= 70, f"Should score 70+, got {score}/100"
        assert grade == "B", f"Expected B grade, got {grade}"

    def test_director_of_healthtech_scores_b_grade(self, eli_profile):
        """Director of HealthTech should score B grade (70+)"""
        scorer = ProfileScorer(eli_profile)
        job = {
            "title": "Director of HealthTech",
            "company": "Health Company",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should match healthtech role_type"
        assert breakdown["seniority"] >= 25, "Director should get 25+ seniority"
        assert score >= 70, f"Should score 70+, got {score}/100"
        assert grade == "B", f"Expected B grade, got {grade}"

    def test_vp_of_saas_scores_b_grade(self, eli_profile):
        """VP of SaaS should score B grade (70+)"""
        scorer = ProfileScorer(eli_profile)
        job = {
            "title": "VP of SaaS",
            "company": "SaaS Company",
            "location": "Remote",
        }

        score, grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert breakdown["role_type"] > 0, "Should match saas role_type"
        assert breakdown["seniority"] == 30, "VP should get 30 seniority points"
        assert score >= 70, f"Should score 70+, got {score}/100"
        assert grade == "B", f"Expected B grade, got {grade}"


class TestCrossProfileConsistency:
    """Ensure all profiles handle domain-specific leadership roles correctly"""

    def test_wes_engineering_leadership_keywords(self, wes_profile):
        """Wes's engineering_leadership should include robotics-specific keywords"""
        role_types = wes_profile.scoring.get("role_types", {})
        eng_leadership = role_types.get("engineering_leadership", [])

        required_keywords = ["robotics", "automation", "mechatronics"]
        for keyword in required_keywords:
            assert keyword in eng_leadership, (
                f"Wes's engineering_leadership should include '{keyword}'"
            )

    def test_wes_operations_leadership_exists(self, wes_profile):
        """Wes should have operations_leadership role type"""
        role_types = wes_profile.scoring.get("role_types", {})

        assert "operations_leadership" in role_types, (
            "Wes's profile should have operations_leadership role type"
        )

        ops_leadership = role_types.get("operations_leadership", [])
        assert "manufacturing" in ops_leadership, (
            "operations_leadership should include 'manufacturing'"
        )

    def test_eli_engineering_leadership_keywords(self, eli_profile):
        """Eli's engineering_leadership should include fintech-specific keywords"""
        role_types = eli_profile.scoring.get("role_types", {})
        eng_leadership = role_types.get("engineering_leadership", [])

        required_keywords = ["fintech", "healthtech", "saas"]
        for keyword in required_keywords:
            assert keyword in eng_leadership, (
                f"Eli's engineering_leadership should include '{keyword}'"
            )
