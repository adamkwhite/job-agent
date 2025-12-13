"""Tests for digest email count accuracy (Issue #140/#141)."""

import json

import pytest

from src.send_profile_digest import generate_email_html
from src.utils.profile_manager import Profile


@pytest.fixture
def test_profile():
    """Create a test profile."""
    return Profile(
        id="test",
        name="Test User",
        email="test@example.com",
        enabled=True,
        email_username="",
        email_app_password_env="",
        scoring={
            "target_seniority": ["senior", "staff"],
            "domain_keywords": ["engineering", "software"],
            "role_types": {"engineering": ["engineer"]},
            "location_preferences": {},
            "filtering": {"aggression_level": "conservative"},
        },
        digest_min_grade="C",
        digest_min_score=60,
        digest_min_location_score=0,
        digest_include_grades=["A", "B", "C"],
        digest_frequency="daily",
        notifications_enabled=True,
        notifications_min_grade="B",
        notifications_min_score=80,
    )


class TestDigestCountAccuracy:
    """Test that digest counts match displayed jobs (Issue #140/#141)."""

    def test_excellent_and_good_matches_count(self, test_profile):
        """Test that excellent (80+) and good (70-79) counts are accurate."""
        # Create jobs: 18 excellent (80+) and 2 good (70-79)
        jobs = []

        # Add 18 excellent matches (80+)
        for i in range(18):
            jobs.append(
                {
                    "title": f"VP Engineering {i}",
                    "company": f"Company {i}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i}",
                    "fit_score": 80 + i,  # Scores from 80 to 97
                    "fit_grade": "A",
                    "score_breakdown": json.dumps(
                        {
                            "seniority": 30,
                            "domain": 25,
                            "role_type": 20,
                            "location": 15,
                            "technical": 5,
                            "company_fit": 5,
                        }
                    ),
                    "location_score": 15,
                }
            )

        # Add 2 good matches (70-79)
        for i in range(2):
            jobs.append(
                {
                    "title": f"Senior Engineer {i}",
                    "company": f"Startup {i}",
                    "location": "Hybrid",
                    "link": f"https://example.com/job/{i + 20}",
                    "fit_score": 70 + i,  # Scores 70, 71
                    "fit_grade": "B",
                    "score_breakdown": json.dumps(
                        {
                            "seniority": 20,
                            "domain": 25,
                            "role_type": 15,
                            "location": 10,
                            "technical": 5,
                            "company_fit": -5,
                        }
                    ),
                    "location_score": 10,
                }
            )

        # Generate email HTML
        html = generate_email_html(jobs, test_profile)

        # Verify counts in summary
        assert "18</strong> excellent matches (80+ score)" in html
        assert "2</strong> good matches (70-79 score)" in html

        # Verify both sections are shown
        assert "⭐ Top Matches (80+ Score)" in html
        assert "✅ Also Worth Considering (70-79 Score)" in html

        # Verify all excellent matches are in the HTML
        for i in range(18):
            assert f"VP Engineering {i}" in html

        # Verify all good matches are in the HTML
        for i in range(2):
            assert f"Senior Engineer {i}" in html

    def test_only_excellent_matches(self, test_profile):
        """Test with only excellent matches (no 70-79 jobs)."""
        # Create jobs: 10 excellent (80+), 0 good (70-79)
        jobs = []

        for i in range(10):
            jobs.append(
                {
                    "title": f"VP Engineering {i}",
                    "company": f"Company {i}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i}",
                    "fit_score": 85 + i,
                    "fit_grade": "A",
                    "score_breakdown": json.dumps(
                        {
                            "seniority": 30,
                            "domain": 25,
                            "role_type": 20,
                            "location": 15,
                            "technical": 5,
                            "company_fit": 5,
                        }
                    ),
                    "location_score": 15,
                }
            )

        html = generate_email_html(jobs, test_profile)

        # Verify counts
        assert "10</strong> excellent matches (80+ score)" in html
        assert "0</strong> good matches (70-79 score)" in html

        # Only excellent section should show
        assert "⭐ Top Matches (80+ Score)" in html
        assert "✅ Also Worth Considering (70-79 Score)" not in html

    def test_only_good_matches(self, test_profile):
        """Test with only good matches (no 80+ jobs)."""
        # Create jobs: 0 excellent (80+), 5 good (70-79)
        jobs = []

        for i in range(5):
            jobs.append(
                {
                    "title": f"Senior Engineer {i}",
                    "company": f"Startup {i}",
                    "location": "Hybrid",
                    "link": f"https://example.com/job/{i}",
                    "fit_score": 70 + i,
                    "fit_grade": "B",
                    "score_breakdown": json.dumps(
                        {
                            "seniority": 20,
                            "domain": 25,
                            "role_type": 15,
                            "location": 10,
                            "technical": 5,
                            "company_fit": -5,
                        }
                    ),
                    "location_score": 10,
                }
            )

        html = generate_email_html(jobs, test_profile)

        # Verify counts
        assert "0</strong> excellent matches (80+ score)" in html
        assert "5</strong> good matches (70-79 score)" in html

        # Only good section should show
        assert "⭐ Top Matches (80+ Score)" not in html
        assert "✅ Also Worth Considering (70-79 Score)" in html

    def test_regression_issue_140(self, test_profile):
        """Regression test for Issue #140: 20 good matches count but only 2 shown."""
        # Recreate the exact scenario from the bug report:
        # - 18 excellent matches (80+)
        # - 2 good matches (70-79)
        # - Summary incorrectly showed "20 good matches" (counting 70+)
        # - Should show "2 good matches" (counting 70-79 only)

        jobs = []

        # 18 excellent matches
        for i in range(18):
            jobs.append(
                {
                    "title": f"Job {i}",
                    "company": f"Company {i}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i}",
                    "fit_score": 80 + i,
                    "fit_grade": "A",
                    "score_breakdown": json.dumps({"seniority": 30}),
                    "location_score": 15,
                }
            )

        # 2 good matches
        for i in range(2):
            jobs.append(
                {
                    "title": f"Job {i + 20}",
                    "company": f"Company {i + 20}",
                    "location": "Hybrid",
                    "link": f"https://example.com/job/{i + 20}",
                    "fit_score": 70 + i,
                    "fit_grade": "B",
                    "score_breakdown": json.dumps({"seniority": 20}),
                    "location_score": 10,
                }
            )

        html = generate_email_html(jobs, test_profile)

        # The bug was showing "20 good matches (70+ score)"
        # Should show "2 good matches (70-79 score)"
        assert "2</strong> good matches (70-79 score)" in html
        assert "20</strong> good matches" not in html

        # Verify 18 excellent are shown
        assert "18</strong> excellent matches (80+ score)" in html

    def test_boundary_scores(self, test_profile):
        """Test jobs at score boundaries (69, 70, 79, 80)."""
        jobs = [
            {
                "title": "Job 69",
                "company": "Company A",
                "location": "Remote",
                "link": "https://example.com/job/69",
                "fit_score": 69,
                "fit_grade": "C",
                "score_breakdown": json.dumps({"seniority": 20}),
                "location_score": 10,
            },
            {
                "title": "Job 70",
                "company": "Company B",
                "location": "Remote",
                "link": "https://example.com/job/70",
                "fit_score": 70,
                "fit_grade": "B",
                "score_breakdown": json.dumps({"seniority": 20}),
                "location_score": 10,
            },
            {
                "title": "Job 79",
                "company": "Company C",
                "location": "Remote",
                "link": "https://example.com/job/79",
                "fit_score": 79,
                "fit_grade": "B",
                "score_breakdown": json.dumps({"seniority": 25}),
                "location_score": 10,
            },
            {
                "title": "Job 80",
                "company": "Company D",
                "location": "Remote",
                "link": "https://example.com/job/80",
                "fit_score": 80,
                "fit_grade": "A",
                "score_breakdown": json.dumps({"seniority": 30}),
                "location_score": 15,
            },
        ]

        html = generate_email_html(jobs, test_profile)

        # 70 and 79 should be counted as "good matches"
        # 80 should be counted as "excellent matches"
        # 69 should not be counted in either
        assert "1</strong> excellent matches (80+ score)" in html
        assert "2</strong> good matches (70-79 score)" in html

        # Verify the jobs are in the right sections
        assert "Job 70" in html
        assert "Job 79" in html
        assert "Job 80" in html
        # Job 69 might not be in the email at all depending on filtering

    def test_regression_issue_149_mario_case(self, test_profile):
        """Regression test for Issue #149: Opening count matches summary counts.

        Mario's case: Email said "I've analyzed 1 opportunities" but showed "0 excellent, 0 good".
        This happened when the only job scored below 70.
        """
        jobs = [
            {
                "title": "Low Scoring Job",
                "company": "Company X",
                "location": "Remote",
                "link": "https://example.com/job/low",
                "fit_score": 65,  # Below 70 threshold
                "fit_grade": "C",
                "score_breakdown": json.dumps({"seniority": 15}),
                "location_score": 10,
            }
        ]

        html = generate_email_html(jobs, test_profile)

        # Opening should say "0 opportunities" to match summary
        assert "0 opportunities</strong>" in html

        # Summary should show 0 for both categories
        assert "0</strong> excellent matches (80+ score)" in html
        assert "0</strong> good matches (70-79 score)" in html

    def test_opening_count_matches_summary_with_mixed_scores(self, test_profile):
        """Test that opening paragraph count matches summary across various scenarios."""
        # Scenario 1: 5 excellent, 3 good, 2 below threshold
        jobs = []

        # 5 excellent (80+)
        for i in range(5):
            jobs.append(
                {
                    "title": f"Excellent {i}",
                    "company": f"Company {i}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i}",
                    "fit_score": 85 + i,
                    "fit_grade": "A",
                    "score_breakdown": json.dumps({"seniority": 30}),
                    "location_score": 15,
                }
            )

        # 3 good (70-79)
        for i in range(3):
            jobs.append(
                {
                    "title": f"Good {i}",
                    "company": f"Company {i + 5}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i + 5}",
                    "fit_score": 72 + i,
                    "fit_grade": "B",
                    "score_breakdown": json.dumps({"seniority": 20}),
                    "location_score": 10,
                }
            )

        # 2 below threshold (<70)
        for i in range(2):
            jobs.append(
                {
                    "title": f"Low {i}",
                    "company": f"Company {i + 8}",
                    "location": "Remote",
                    "link": f"https://example.com/job/{i + 8}",
                    "fit_score": 65 + i,
                    "fit_grade": "C",
                    "score_breakdown": json.dumps({"seniority": 15}),
                    "location_score": 8,
                }
            )

        html = generate_email_html(jobs, test_profile)

        # Opening should say "8 opportunities" (5 excellent + 3 good), NOT "10 opportunities"
        assert "8 opportunities</strong>" in html

        # Summary counts should match
        assert "5</strong> excellent matches (80+ score)" in html
        assert "3</strong> good matches (70-79 score)" in html
