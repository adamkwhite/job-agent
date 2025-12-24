"""
Unit tests for digest email job display logic

Tests that ALL jobs matching the criteria are displayed in the email,
not just a hardcoded subset.

Addresses Issue #135 - Digest count mismatch (summary vs displayed jobs)
"""

import re
from unittest.mock import MagicMock

from src.send_profile_digest import generate_email_html


class TestDigestJobDisplay:
    """Test that job display matches summary counts"""

    def _create_mock_profile(self):
        """Create a mock profile for testing"""
        profile = MagicMock()
        profile.name = "Test User"
        profile.get_target_seniority.return_value = ["director", "vp"]
        profile.get_domain_keywords.return_value = ["robotics", "automation"]
        return profile

    def _create_mock_job(self, score: int, title: str = "Test Job", company: str = "Test Co"):
        """Create a mock job with specified score"""
        grade_map = {
            range(98, 116): "A",
            range(80, 98): "B",
            range(63, 80): "C",
            range(46, 63): "D",
            range(0, 46): "F",
        }
        grade = next((g for r, g in grade_map.items() if score in r), "F")

        return {
            "company": company,
            "title": title,
            "link": f"https://example.com/jobs/{score}",
            "location": "Remote",
            "fit_score": score,
            "fit_grade": grade,
            "score_breakdown": '{"seniority": 20, "domain": 15, "role_type": 10, "location": 15, "technical": 5, "company_classification": 0}',
        }

    def test_all_excellent_matches_displayed_no_limit(self):
        """Test that ALL excellent matches (70+) are displayed, not just 10"""
        profile = self._create_mock_profile()

        # Create 15 excellent matches (more than old limit of 10)
        jobs = [self._create_mock_job(score=70 + i, title=f"Job {i}") for i in range(15)]

        html = generate_email_html(jobs, profile)

        # Verify summary says 15
        assert "15</strong> excellent matches" in html

        # Count how many job links appear in the excellent section
        # Each job has a unique link with its score in the URL
        excellent_jobs_in_html = 0
        for i in range(15):
            expected_link = f"https://example.com/jobs/{70 + i}"
            if expected_link in html:
                excellent_jobs_in_html += 1

        # All 15 should be in the HTML
        assert excellent_jobs_in_html == 15, (
            f"Expected 15 excellent jobs, found {excellent_jobs_in_html}"
        )

    def test_all_good_matches_displayed_no_limit(self):
        """Test that ALL good matches (55-69) are displayed, not just 5"""
        profile = self._create_mock_profile()

        # Create 10 excellent (70+) and 8 good (55-69) matches
        jobs = []
        jobs.extend(
            [self._create_mock_job(score=70 + i, title=f"Excellent {i}") for i in range(10)]
        )
        jobs.extend([self._create_mock_job(score=55 + i, title=f"Good {i}") for i in range(8)])

        html = generate_email_html(jobs, profile)

        # Verify summary says 10 excellent, 8 good (55-69 only)
        assert "10</strong> excellent matches" in html
        assert "8</strong> good matches (55-69 score)" in html

        # Count good matches (55-69 only) in the HTML
        good_jobs_in_html = 0
        for i in range(8):
            expected_link = f"https://example.com/jobs/{55 + i}"
            if expected_link in html:
                good_jobs_in_html += 1

        # All 8 should be in the HTML
        assert good_jobs_in_html == 8, f"Expected 8 good jobs, found {good_jobs_in_html}"

    def test_summary_counts_match_displayed_jobs(self):
        """Test that summary counts exactly match displayed job counts"""
        profile = self._create_mock_profile()

        # Create 12 excellent (70+) and 5 good (55-69) matches
        jobs = []
        jobs.extend([self._create_mock_job(score=85, company=f"Company {i}") for i in range(12)])
        jobs.extend(
            [self._create_mock_job(score=60, company=f"Company {i + 12}") for i in range(5)]
        )

        html = generate_email_html(jobs, profile)

        # Extract summary counts
        excellent_match = re.search(r"(\d+)</strong> excellent matches", html)
        good_match = re.search(r"(\d+)</strong> good matches", html)

        assert excellent_match, "Summary should mention excellent matches"
        assert good_match, "Summary should mention good matches"

        summary_excellent = int(excellent_match.group(1))
        summary_good = int(good_match.group(1))

        assert summary_excellent == 12
        assert summary_good == 5  # 5 good (55-69 only)

        # Count actual job entries in HTML
        # Each job has a table row with company name
        displayed_companies = []
        for i in range(12):
            if f"Company {i}" in html:
                displayed_companies.append(f"Company {i}")
        for i in range(12, 17):
            if f"Company {i}" in html:
                displayed_companies.append(f"Company {i}")

        assert len(displayed_companies) == 17, (
            f"Expected 17 jobs displayed, found {len(displayed_companies)}"
        )

    def test_no_good_section_if_all_excellent(self):
        """Test that good section doesn't appear if all jobs are 70+"""
        profile = self._create_mock_profile()

        # Create only excellent matches
        jobs = [self._create_mock_job(score=85) for _ in range(8)]

        html = generate_email_html(jobs, profile)

        # Should have excellent section
        assert "Top Matches (70+ Score)" in html

        # Should NOT have good section (no 55-69 jobs)
        assert "Also Worth Considering (55-69 Score)" not in html

    def test_good_section_appears_when_70_79_jobs_exist(self):
        """Test that good section appears when there are 55-69 jobs"""
        profile = self._create_mock_profile()

        # Create mix of excellent and good
        jobs = []
        jobs.extend([self._create_mock_job(score=85) for _ in range(5)])
        jobs.extend([self._create_mock_job(score=60) for _ in range(3)])

        html = generate_email_html(jobs, profile)

        # Should have both sections
        assert "Top Matches (70+ Score)" in html
        assert "Also Worth Considering (55-69 Score)" in html

    def test_empty_jobs_list(self):
        """Test handling of empty jobs list"""
        profile = self._create_mock_profile()
        jobs = []

        html = generate_email_html(jobs, profile)

        # Should still generate valid HTML
        assert "<html>" in html
        assert "0</strong> excellent matches" in html
        assert "0</strong> good matches" in html

    def test_regression_issue_135_elis_case(self):
        """
        Regression test for Issue #135 - Eli's specific case

        Eli's digest said:
        - 15 excellent matches (70+)
        - 17 good matches (70+)

        But only showed:
        - 10 excellent
        - 2 good

        This test ensures that exact scenario is now fixed.
        """
        profile = self._create_mock_profile()

        # Recreate Eli's exact scenario
        jobs = []

        # 15 excellent matches (80-94)
        jobs.extend(
            [self._create_mock_job(score=70 + i, title=f"Excellent {i}") for i in range(15)]
        )

        # 2 good matches (55-69) - only 2 in 55-69 range
        jobs.extend([self._create_mock_job(score=60, title="Good 1")])
        jobs.extend([self._create_mock_job(score=57, title="Good 2")])

        html = generate_email_html(jobs, profile)

        # Verify summary
        assert "15</strong> excellent matches" in html
        assert "2</strong> good matches (55-69 score)" in html  # 2 in 55-69 range only

        # Verify ALL 15 excellent jobs are in HTML
        for i in range(15):
            assert f"Excellent {i}" in html, f"Missing excellent job {i}"

        # Verify BOTH good jobs are in HTML
        assert "Good 1" in html
        assert "Good 2" in html

        # Count total unique job titles in HTML (15 excellent + 2 good)
        job_titles = re.findall(r"(Excellent \d+|Good \d+)", html)
        assert len(job_titles) == 17, (
            f"Expected 17 jobs in HTML (15 excellent + 2 good), found {len(job_titles)}: {job_titles}"
        )
