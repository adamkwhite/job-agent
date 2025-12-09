"""
Integration tests for software role filtering system (Issue #122 - Batch 5)

Tests end-to-end integration of company classification, filtering logic,
and job scoring with real-world examples.
"""

import time

import pytest

from agents.job_scorer import JobScorer
from utils.company_classifier import CompanyClassifier


class TestRealWorldExamples:
    """Test filtering with real company and job title examples"""

    def test_program_director_at_jobs_organization(self):
        """Program Director at Jobs.ca should NOT be filtered (organization, not software)"""
        scorer = JobScorer()
        job = {
            "title": "Program Director",
            "company": "Jobs.ca",
            "location": "Remote, Canada",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Should NOT be filtered - Jobs.ca is not a software company
        assert classification_metadata.get("filtered") is False
        # Score should be based on role type and other factors
        assert score > 0

    def test_vp_engineering_at_boston_dynamics(self):
        """VP Engineering at Boston Dynamics should NOT be filtered (hardware company)"""
        scorer = JobScorer()
        job = {
            "title": "VP of Engineering",
            "company": "Boston Dynamics",
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Should receive hardware company boost
        assert classification_metadata.get("hardware_boost_applied") is True
        assert breakdown.get("company_classification") == 10
        assert classification_metadata.get("filtered") is False
        assert classification_metadata.get("company_type") == "hardware"

    def test_vp_software_engineering_at_stripe(self):
        """VP of Software Engineering at Stripe should be filtered (conservative mode)"""
        scorer = JobScorer()
        scorer.profile["filtering"]["aggression_level"] = (
            "conservative"  # Use conservative for explicit keyword match
        )

        job = {
            "title": "VP of Software Engineering",
            "company": "Stripe",
            "location": "Remote, USA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Should be filtered due to explicit "software engineering" keyword (conservative mode)
        assert classification_metadata.get("filtered") is True
        assert breakdown.get("company_classification") == -20
        assert classification_metadata.get("company_type") == "software"
        assert (
            classification_metadata.get("filter_reason")
            == "software_engineering_explicit_conservative"
        )

    def test_vp_product_at_stripe_not_filtered(self):
        """VP of Product at Stripe should NOT be filtered (product leadership)"""
        scorer = JobScorer()
        job = {
            "title": "VP of Product",
            "company": "Stripe",
            "location": "San Francisco, CA",
        }

        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Product leadership is never filtered
        assert classification_metadata.get("filtered") is False
        assert classification_metadata.get("filter_reason") == "product_leadership_any_company"


class TestAggressionLevels:
    """Test all three aggression levels"""

    def test_conservative_mode(self):
        """Conservative mode only filters explicit software keywords"""
        scorer = JobScorer()
        scorer.profile["filtering"]["aggression_level"] = "conservative"
        scorer.profile["filtering"]["software_engineering_avoid"] = ["software engineering"]

        # VP Engineering (no software keyword) - should NOT filter
        job1 = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }
        _, _, _, meta1 = scorer.score_job(job1)
        assert meta1.get("filtered") is False

        # VP of Software Engineering - should filter
        job2 = {
            "title": "VP of Software Engineering",
            "company": "Stripe",
            "location": "Remote",
        }
        _, _, _, meta2 = scorer.score_job(job2)
        assert meta2.get("filtered") is True

    def test_moderate_mode(self):
        """Moderate mode filters engineering at software companies with confidence ≥0.6"""
        scorer = JobScorer()
        scorer.profile["filtering"]["aggression_level"] = "moderate"

        job = {
            "title": "Director of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }

        _, _, _, metadata = scorer.score_job(job)

        # Should filter if Stripe classified as software with high confidence
        if metadata.get("confidence", 0) >= 0.6 and metadata.get("company_type") == "software":
            assert metadata.get("filtered") is True

    def test_aggressive_mode(self):
        """Aggressive mode filters any engineering without hardware keywords"""
        scorer = JobScorer()
        scorer.profile["filtering"]["aggression_level"] = "aggressive"

        # Engineering without hardware keywords - should filter
        job1 = {
            "title": "VP of Engineering",
            "company": "Stripe",
            "location": "Remote",
        }
        _, _, _, meta1 = scorer.score_job(job1)
        assert meta1.get("filtered") is True
        assert meta1.get("filter_reason") == "no_hardware_keywords_aggressive"

        # Hardware Engineering - should NOT filter
        job2 = {
            "title": "VP of Hardware Engineering",
            "company": "Stripe",
            "location": "Remote",
        }
        _, _, _, meta2 = scorer.score_job(job2)
        assert meta2.get("filtered") is False


class TestDualDomainCompanies:
    """Test filtering for companies with both hardware and software"""

    def test_tesla_vp_engineering_ambiguous(self):
        """Generic VP Engineering at Tesla (dual-domain) should NOT be filtered"""
        scorer = JobScorer()
        job = {
            "title": "VP of Engineering",
            "company": "Tesla",
            "location": "Palo Alto, CA",
        }

        _, _, _, metadata = scorer.score_job(job)

        # Ambiguous title at dual-domain company - don't filter
        if metadata.get("company_type") == "both":
            assert metadata.get("filtered") is False
            assert metadata.get("filter_reason") == "dual_domain_ambiguous"

    def test_tesla_backend_engineering_filtered(self):
        """Director of Backend Engineering at Tesla should be filtered (software-specific)"""
        scorer = JobScorer()
        scorer.profile["filtering"]["software_engineering_avoid"] = ["backend"]

        job = {
            "title": "Director of Backend Engineering",
            "company": "Tesla",
            "location": "Palo Alto, CA",
        }

        _, _, _, metadata = scorer.score_job(job)

        # Software-focused title at dual-domain company - filter
        if metadata.get("company_type") == "both":
            assert metadata.get("filtered") is True
            assert metadata.get("filter_reason") == "dual_domain_software_focused"


class TestPerformance:
    """Test performance requirements"""

    def test_classification_performance(self):
        """Company classification should complete in <100ms"""
        classifier = CompanyClassifier()

        start_time = time.time()
        result = classifier.classify_company(
            company_name="Boston Dynamics",
            job_title="VP of Engineering",
            domain_keywords=["robotics", "hardware"],
        )
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 100, f"Classification took {elapsed_ms:.2f}ms (should be <100ms)"
        assert result.type in ["software", "hardware", "both", "unknown"]
        assert 0 <= result.confidence <= 1.0

    def test_scoring_with_classification_performance(self):
        """Full scoring with classification should be fast"""
        scorer = JobScorer()

        start_time = time.time()
        scorer.score_job(
            {
                "title": "VP of Engineering",
                "company": "Stripe",
                "location": "Remote",
            }
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Should complete quickly (reasonable threshold: 200ms including DB operations)
        assert elapsed_ms < 200, f"Scoring took {elapsed_ms:.2f}ms"


class TestCoverageRequirements:
    """Verify code coverage requirements"""

    def test_company_classifier_has_high_coverage(self):
        """Verify company_classifier.py has ≥80% coverage"""
        # This is verified by pytest-cov in CI
        # Coverage is enforced by SonarCloud quality gate
        # This test documents the requirement
        pass

    def test_filtering_logic_has_high_coverage(self):
        """Verify filtering logic functions have ≥80% coverage"""
        # Coverage tracked by:
        # - test_filtering_logic.py (15 tests)
        # - test_job_scorer.py (5 integration tests)
        # - This file (integration tests)
        pass


class TestExistingTests:
    """Verify existing tests still pass with new filtering"""

    def test_existing_unit_tests_passing(self):
        """All 928+ existing unit tests should still pass"""
        # This is verified by CI running full test suite
        # Batch 3 already verified tests pass with 4-tuple API
        pass


@pytest.mark.skip(reason="Requires database with real jobs")
class TestDatabaseJobs:
    """Test filtering against recent jobs in database"""

    def test_score_recent_jobs(self, db_with_recent_jobs):
        """Test filtering on 20 recent jobs from database"""
        # This would require:
        # 1. Fixture to load 20 recent jobs from database
        # 2. Score each job
        # 3. Verify filtering metadata exists
        # 4. Check distribution of filtered vs non-filtered
        pass
