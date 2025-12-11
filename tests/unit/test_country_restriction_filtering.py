"""
Unit tests for country-restricted remote job filtering

Tests that Canadian candidates don't receive 15 points for US-only remote jobs.
Addresses Issue #132 - Filter out country-restricted remote jobs
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.job_scorer import JobScorer


class TestCountryRestrictionFiltering:
    """Test country restriction detection for remote jobs"""

    def _create_test_job(
        self, location: str, description: str = "", title: str = "Director of Engineering"
    ) -> dict:
        """Create a mock job for testing"""
        return {
            "title": title,
            "company": "Test Company",
            "location": location,
            "description": description,
            "link": "https://example.com/job",
            "source": "test",
        }

    def test_unrestricted_remote_gets_15_points(self):
        """Test that unrestricted 'Remote' jobs get 15 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = self._create_test_job(location="Remote")
            score, grade, breakdown, _ = scorer.score_job(job)

            assert breakdown["location"] == 15, "Unrestricted remote should get 15 points"

    def test_us_only_remote_location_gets_0_points(self):
        """Test that 'United States (Remote)' gets 0 points for Canadian candidates"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = self._create_test_job(location="United States (Remote)")
            score, grade, breakdown, _ = scorer.score_job(job)

            assert breakdown["location"] == 0, "US-only remote should get 0 points"

    def test_remote_us_format_gets_0_points(self):
        """Test that 'Remote - United States' gets 0 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = self._create_test_job(location="Remote - United States")
            score, grade, breakdown, _ = scorer.score_job(job)

            assert breakdown["location"] == 0, "Remote - US should get 0 points"

    def test_remote_with_us_state_gets_0_points(self):
        """Test that remote jobs with US state/city get 0 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            test_cases = [
                "Montgomery, AL (Remote)",
                "Remote - California",
                "Texas (Remote)",
                "San Francisco (Remote)",
            ]

            for location in test_cases:
                job = self._create_test_job(location=location)
                score, grade, breakdown, _ = scorer.score_job(job)

                assert breakdown["location"] == 0, (
                    f"Remote job with US location '{location}' should get 0 points"
                )

    def test_canada_friendly_remote_gets_15_points(self):
        """Test that Canada-specific remote jobs get 15 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            test_cases = [
                "Remote - Canada",
                "Remote - North America",
                "Canada (Remote)",
            ]

            for location in test_cases:
                job = self._create_test_job(location=location)
                score, grade, breakdown, _ = scorer.score_job(job)

                assert breakdown["location"] == 15, (
                    f"Canada-friendly remote '{location}' should get 15 points"
                )

    def test_us_work_auth_in_description_gets_0_points(self):
        """Test that job description with US work auth requirement gets 0 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            descriptions = [
                "Must be based in the U.S. and authorized to work.",
                "U.S. work authorization required.",
                "Candidates must reside in the United States.",
                "Only considering U.S. applicants.",
            ]

            for desc in descriptions:
                job = self._create_test_job(location="Remote", description=desc)
                score, grade, breakdown, _ = scorer.score_job(job)

                assert breakdown["location"] == 0, (
                    f"Remote job with US requirement in description should get 0 points: {desc}"
                )

    def test_canada_friendly_description_gets_15_points(self):
        """Test that job description welcoming Canadian candidates gets 15 points"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            descriptions = [
                "Canadian candidates welcome to apply!",
                "Open to Canadian applicants.",
                "Remote - North America (US/Canada)",
            ]

            for desc in descriptions:
                job = self._create_test_job(location="Remote", description=desc)
                score, grade, breakdown, _ = scorer.score_job(job)

                assert breakdown["location"] == 15, (
                    f"Remote job welcoming Canadians should get 15 points: {desc}"
                )

    def test_regression_issue_132_alma_example(self):
        """
        Regression test for Issue #132 - Alma job example

        Wes received: Alma - "United States (Remote)" - 80 points
        Should get 0 location points, dropping overall score
        """
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = {
                "title": "Director, Clinical Operations",
                "company": "Alma",
                "location": "United States (Remote)",
                "description": "",
                "link": "https://example.com/job",
                "source": "test",
            }

            score, grade, breakdown, _ = scorer.score_job(job)

            assert breakdown["location"] == 0, (
                "Alma US-only remote job should get 0 location points"
            )

    def test_regression_issue_132_steris_example(self):
        """
        Regression test for Issue #132 - STERIS job example

        Wes received: STERIS - "Montgomery, AL (Remote)" - 80 points
        Should get 0 location points
        """
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = {
                "title": "Sr. Director, Project Management",
                "company": "STERIS",
                "location": "Montgomery, AL (Remote)",
                "description": "",
                "link": "https://example.com/job",
                "source": "test",
            }

            score, grade, breakdown, _ = scorer.score_job(job)

            assert breakdown["location"] == 0, (
                "STERIS Montgomery, AL remote job should get 0 location points"
            )

    def test_is_country_restricted_method_directly(self):
        """Test the _is_country_restricted helper method directly"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            # US-only cases (should return True)
            assert scorer._is_country_restricted("United States (Remote)") is True
            assert scorer._is_country_restricted("Remote - US") is True
            assert scorer._is_country_restricted("Montgomery, AL (Remote)") is True
            assert scorer._is_country_restricted("Remote", "Must be based in the U.S.") is True

            # Canada-friendly cases (should return False)
            assert scorer._is_country_restricted("Remote - Canada") is False
            assert scorer._is_country_restricted("Remote - North America") is False
            assert scorer._is_country_restricted("Remote") is False
            assert scorer._is_country_restricted("Remote", "Canadian candidates welcome") is False

    def test_edge_case_or_not_matched_as_oregon(self):
        """Test that 'OR' in 'Director' doesn't match Oregon state code"""
        with patch("agents.job_scorer.JobDatabase"):
            scorer = JobScorer()

            job = self._create_test_job(location="Remote", title="Director of Engineering")
            score, grade, breakdown, _ = scorer.score_job(job)

            # Should still get 15 points (not falsely matched as Oregon)
            assert breakdown["location"] == 15

    def test_location_config_loads_correctly(self):
        """Test that location settings config file loads properly"""
        config_path = Path(__file__).parent.parent.parent / "config" / "location-settings.json"

        assert config_path.exists(), "location-settings.json should exist"

        with open(config_path) as f:
            config = json.load(f)

        assert "country_restriction_patterns" in config
        assert "us_only" in config["country_restriction_patterns"]
        assert "us_states" in config["country_restriction_patterns"]
        assert "canada_friendly" in config["country_restriction_patterns"]
