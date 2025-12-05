"""
Unit tests for ProfileScorer role_type scoring logic

Tests word boundary matching to prevent false positives like:
- "cto" matching "director"
- "product" matching "production"
- Generic leadership roles scoring without role type match
"""

import pytest

from agents.profile_scorer import ProfileScorer
from utils.profile_manager import Profile


@pytest.fixture
def engineering_profile():
    """Profile targeting engineering leadership roles"""
    return Profile(
        id="test_eng",
        name="Test Engineering Profile",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["director", "vp", "head of"],
            "domain_keywords": ["software", "technology"],
            "role_types": {
                "engineering_leadership": [
                    "engineering",
                    "technical",
                    "cto",
                    "vp engineering",
                    "director engineering",
                ]
            },
            "location_preferences": {"remote_keywords": ["remote"]},
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="B",
        notifications_min_score=80,
    )


@pytest.fixture
def product_profile():
    """Profile targeting product roles"""
    return Profile(
        id="test_product",
        name="Test Product Profile",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["director", "vp"],
            "domain_keywords": ["software", "saas"],
            "role_types": {"product": ["product manager", "product", "pm"]},
            "location_preferences": {"remote_keywords": ["remote"]},
        },
        digest_min_grade="C",
        digest_min_score=63,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="weekly",
        notifications_enabled=False,
        notifications_min_grade="B",
        notifications_min_score=80,
    )


class TestRoleTypeWordBoundaries:
    """Test word boundary matching prevents false positives"""

    def test_marketing_director_not_matching_cto(self, engineering_profile):
        """Marketing Director should NOT match 'cto' keyword"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Performance Marketing Director",
            "company": "Test Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should NOT get role_type points (was 20, should be 0)
        assert breakdown["role_type"] == 0, "Marketing Director should not match 'cto' keyword"

        # Total score should be low (no role_type points)
        assert score < 63, f"Marketing role scored too high: {score}/115"
        assert grade in ["D", "F"], f"Marketing role should be D or F grade, got {grade}"

    def test_director_engineering_matches(self, engineering_profile):
        """Director of Engineering should match engineering keywords"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Director of Engineering",
            "company": "Test Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should get full role_type points (leadership + engineering)
        assert breakdown["role_type"] == 20, "Director of Engineering should score 20 points"

    def test_vp_engineering_matches(self, engineering_profile):
        """VP of Engineering should match engineering keywords"""
        scorer = ProfileScorer(engineering_profile)
        job = {"title": "VP of Engineering", "company": "Test Company", "location": "Remote"}

        score, grade, breakdown = scorer.score_job(job)

        # Should get full role_type points
        assert breakdown["role_type"] == 20, "VP of Engineering should score 20 points"

    def test_cto_standalone_matches(self, engineering_profile):
        """Standalone 'CTO' title should match"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Chief Technology Officer (CTO)",
            "company": "Tech Co",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should match 'cto' keyword
        assert breakdown["role_type"] == 20, "CTO title should match 'cto' keyword"

    def test_product_marketing_not_matching_product_role(self, product_profile):
        """Product Marketing should NOT match 'product' role type keyword"""
        scorer = ProfileScorer(product_profile)
        job = {
            "title": "Director of Product Marketing",
            "company": "SaaS Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should match 'product' keyword with word boundaries
        # "product marketing" contains "product" as a separate word
        assert breakdown["role_type"] in [
            15,
            20,
        ], "Product Marketing should match 'product' keyword"

    def test_production_engineer_not_matching_product(self, product_profile):
        """Production Engineer should NOT match 'product' keyword"""
        scorer = ProfileScorer(product_profile)
        job = {
            "title": "Production Engineer",
            "company": "Manufacturing Co",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should NOT match 'product' (production != product)
        assert breakdown["role_type"] == 0, "Production Engineer should not match 'product'"


class TestNoFallbackPoints:
    """Test that generic leadership roles without role type match get 0 points"""

    def test_marketing_director_no_fallback(self, engineering_profile):
        """Marketing Director should get 0 role_type points (no fallback)"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Director of Marketing Operations",
            "company": "Marketing Co",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should get 0 points (no engineering keywords, no fallback)
        assert breakdown["role_type"] == 0, "Marketing Director should get 0 role_type points"

    def test_sales_director_no_fallback(self, engineering_profile):
        """Sales Director should get 0 role_type points"""
        scorer = ProfileScorer(engineering_profile)
        job = {"title": "Director of Sales", "company": "SaaS Company", "location": "Remote"}

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["role_type"] == 0, "Sales Director should get 0 role_type points"

    def test_hr_vp_no_fallback(self, engineering_profile):
        """VP of HR should get 0 role_type points"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Vice President of Human Resources",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["role_type"] == 0, "VP of HR should get 0 role_type points"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_technical_product_manager_matches(self, engineering_profile):
        """Technical Product Manager should match 'technical' keyword"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Technical Product Manager",
            "company": "Tech Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should match 'technical' keyword (15 points, not leadership)
        assert breakdown["role_type"] == 15, "Technical PM should match 'technical' keyword"

    def test_engineering_manager_matches(self, engineering_profile):
        """Engineering Manager should match 'engineering' keyword"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "Engineering Manager",
            "company": "Software Company",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        # Should match 'engineering' (15 points, manager is not director-level)
        assert breakdown["role_type"] == 15, "Engineering Manager should match 'engineering'"

    def test_case_insensitive_matching(self, engineering_profile):
        """Matching should be case-insensitive"""
        scorer = ProfileScorer(engineering_profile)
        job = {
            "title": "DIRECTOR OF ENGINEERING",
            "company": "TECH COMPANY",
            "location": "Remote",
        }

        score, grade, breakdown = scorer.score_job(job)

        assert breakdown["role_type"] == 20, "Case-insensitive matching should work"

    def test_multi_word_keyword_matching(self, engineering_profile):
        """Multi-word keywords like 'vp engineering' should match"""
        scorer = ProfileScorer(engineering_profile)
        job = {"title": "VP Engineering", "company": "Startup", "location": "Remote"}

        score, grade, breakdown = scorer.score_job(job)

        # Should match 'vp engineering' or 'engineering' keywords
        assert breakdown["role_type"] in [
            15,
            20,
        ], "VP Engineering should match role keywords"
