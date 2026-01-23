"""
Unit tests for Mario's profile scoring
Tests to ensure QA/testing jobs score correctly for Mario
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.profile_scorer import ProfileScorer
from utils.profile_manager import get_profile_manager


class TestMarioSeniorityScoring:
    """Test that Mario's profile correctly scores seniority for QA roles"""

    def test_senior_qa_engineer_gets_seniority_points(self):
        """Senior QA Engineer should match Mario's 'senior' seniority keyword"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Senior QA Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        # Should get seniority points for "Senior"
        assert breakdown["seniority"] > 0, (
            f"Expected seniority > 0 for 'Senior QA Engineer' but got {breakdown['seniority']}"
        )

    def test_lead_qa_engineer_gets_seniority_points(self):
        """Lead QA Engineer should match Mario's 'lead' seniority keyword"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Lead QA Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["seniority"] > 0, (
            f"Expected seniority > 0 for 'Lead QA Engineer' but got {breakdown['seniority']}"
        )

    def test_qa_automation_lead_gets_seniority_points(self):
        """QA Automation Lead should match Mario's 'lead' seniority keyword"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "QA Automation Lead",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["seniority"] > 0, (
            f"Expected seniority > 0 for 'QA Automation Lead' but got {breakdown['seniority']}"
        )

    def test_staff_test_engineer_gets_seniority_points(self):
        """Staff Test Engineer should match Mario's 'staff' seniority keyword"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Staff Test Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["seniority"] > 0, (
            f"Expected seniority > 0 for 'Staff Test Engineer' but got {breakdown['seniority']}"
        )


class TestMarioRoleTypeScoring:
    """Test that Mario's profile correctly scores role types for QA/testing jobs"""

    def test_qa_engineer_gets_role_type_points(self):
        """QA Engineer should match Mario's role_types"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "QA Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        # Should get role_type points
        assert breakdown["role_type"] > 0, (
            f"Expected role_type > 0 for 'QA Engineer' but got {breakdown['role_type']}"
        )

    def test_test_automation_engineer_gets_role_type_points(self):
        """Test Automation Engineer should match Mario's role_types"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Test Automation Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["role_type"] > 0, (
            f"Expected role_type > 0 for 'Test Automation Engineer' but got {breakdown['role_type']}"
        )

    def test_sdet_gets_role_type_points(self):
        """SDET should match Mario's role_types"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "SDET",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["role_type"] > 0, (
            f"Expected role_type > 0 for 'SDET' but got {breakdown['role_type']}"
        )


class TestMarioDomainScoring:
    """Test that Mario's profile correctly scores domain keywords for QA jobs"""

    def test_qa_gets_domain_points(self):
        """'QA' should match Mario's domain keywords"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Senior QA Engineer",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "Quality assurance and testing",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        # Should get domain points for QA keywords
        assert breakdown["domain"] > 0, (
            f"Expected domain > 0 for QA job but got {breakdown['domain']}"
        )

    def test_test_automation_gets_domain_points(self):
        """'test automation' should match Mario's domain keywords"""
        manager = get_profile_manager()
        mario = manager.get_profile("mario")
        if not mario:
            pytest.skip("Mario's profile not found")
        scorer = ProfileScorer(mario)

        job = {
            "title": "Test Automation Lead",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/job",
            "description": "Building test automation frameworks",
        }

        score, grade, breakdown, _ = scorer.score_job(job)

        assert breakdown["domain"] > 0, (
            f"Expected domain > 0 for test automation job but got {breakdown['domain']}"
        )
