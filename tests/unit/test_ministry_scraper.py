"""
Unit tests for Ministry of Testing scraper
Tests for company extraction and job parsing
"""

import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jobs.ministry_scraper import MinistryScraper
from models import OpportunityData
from scrapers.ministry_of_testing_scraper import MinistryOfTestingScraper


class TestCompanyExtraction:
    """Test company name extraction from job title and location"""

    def test_extract_company_from_city_location(self):
        """Should NOT extract city names as company names"""
        scraper = MinistryOfTestingScraper()

        # Test case 1: "Toronto, Ontario" should NOT return "Toronto" as company
        company = scraper._extract_company(
            title="Quality Assurance (QA) Analyst", location="Toronto, Ontario"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

        # Test case 2: "Austin, TX (Remote)" should NOT return "Austin" as company
        company = scraper._extract_company(
            title="Senior Software Quality Assurance Engineer", location="Austin, TX (Remote)"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

        # Test case 3: "San Francisco, CA" should NOT return "San Francisco"
        company = scraper._extract_company(
            title="QA Automation Engineer", location="San Francisco, CA"
        )
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"

    def test_extract_company_from_title_with_hyphen(self):
        """Should extract company from 'Company - Title' format"""
        scraper = MinistryOfTestingScraper()

        company = scraper._extract_company(
            title="Acme Corp - Senior QA Engineer", location="Remote"
        )
        assert company == "Acme Corp", f"Expected 'Acme Corp' but got '{company}'"

    def test_extract_company_unknown_fallback(self):
        """Should return 'Unknown Company' when no company found"""
        scraper = MinistryOfTestingScraper()

        company = scraper._extract_company(title="QA Engineer", location="United States")
        assert company == "Unknown Company", f"Expected 'Unknown Company' but got '{company}'"


class TestJobParsing:
    """Test parsing jobs from markdown"""

    def test_parse_qa_jobs_from_markdown(self):
        """Should parse QA jobs with correct title, location, and links"""
        scraper = MinistryOfTestingScraper()

        markdown = """
[Quality Assurance (QA) Analyst](https://www.ministryoftesting.com/jobs/qa-analyst)

Toronto, Ontario

16 Jan

[Senior QA Engineer](https://www.ministryoftesting.com/jobs/senior-qa-engineer)

Remote

15 Jan
"""

        jobs = scraper.parse_jobs_from_page(markdown, target_locations=["Canada", "Remote"])

        # Should find 2 jobs
        assert len(jobs) == 2, f"Expected 2 jobs but got {len(jobs)}"

        # Check first job
        job1 = jobs[0]
        assert job1.title == "Quality Assurance (QA) Analyst"
        assert job1.location == "Toronto, Ontario"
        assert job1.link == "https://www.ministryoftesting.com/jobs/qa-analyst"
        assert job1.company != "Toronto", "Company should NOT be 'Toronto'"

        # Check second job
        job2 = jobs[1]
        assert job2.title == "Senior QA Engineer"
        assert job2.location == "Remote"
        assert job2.link == "https://www.ministryoftesting.com/jobs/senior-qa-engineer"

    def test_location_filtering(self):
        """Should filter jobs by target locations"""
        scraper = MinistryOfTestingScraper()

        markdown = """
[QA Engineer](https://www.ministryoftesting.com/jobs/qa-1)

Toronto, Ontario

16 Jan

[Test Engineer](https://www.ministryoftesting.com/jobs/test-1)

London, United Kingdom

15 Jan

[QA Analyst](https://www.ministryoftesting.com/jobs/qa-2)

Remote

14 Jan
"""

        # Filter for Canada and Remote only
        jobs = scraper.parse_jobs_from_page(markdown, target_locations=["Canada", "Remote"])

        # Should only get 2 jobs (Toronto + Remote, not London)
        assert len(jobs) == 2, f"Expected 2 jobs but got {len(jobs)}"

        locations = [job.location for job in jobs]
        assert "Toronto, Ontario" in locations
        assert "Remote" in locations
        assert "London, United Kingdom" not in locations


class TestMinistryScraper:
    """Test the main MinistryScraper class (bug fixes from PR #261)"""

    @pytest.fixture
    def mock_scraper(self):
        """Create a MinistryScraper with mocked dependencies"""
        with (
            patch("jobs.ministry_scraper.JobDatabase"),
            patch("jobs.ministry_scraper.get_multi_scorer"),
            patch("jobs.ministry_scraper.MinistryOfTestingScraper"),
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}),
            patch("jobs.ministry_scraper.FirecrawlApp"),
        ):
            scraper = MinistryScraper(profile="mario")
            return scraper

    def test_retry_operation_success_first_try(self, mock_scraper):
        """Should return result immediately on successful operation"""
        operation = MagicMock(return_value="success")

        result = mock_scraper._retry_db_operation(operation)

        assert result == "success"
        assert operation.call_count == 1

    def test_retry_operation_database_locked_then_success(self, mock_scraper):
        """Should retry on 'database is locked' error and succeed"""
        # First call raises lock error, second call succeeds
        operation = MagicMock(
            side_effect=[sqlite3.OperationalError("database is locked"), "success"]
        )

        result = mock_scraper._retry_db_operation(operation, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert operation.call_count == 2

    def test_retry_operation_exhausts_retries(self, mock_scraper):
        """Should raise exception after max retries exhausted"""
        # All attempts raise lock error
        operation = MagicMock(side_effect=sqlite3.OperationalError("database is locked"))

        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            mock_scraper._retry_db_operation(operation, max_retries=3, initial_delay=0.01)

        assert operation.call_count == 3

    def test_retry_operation_non_lock_error_immediate_raise(self, mock_scraper):
        """Should raise non-lock errors immediately without retry"""
        operation = MagicMock(side_effect=ValueError("invalid input"))

        with pytest.raises(ValueError, match="invalid input"):
            mock_scraper._retry_db_operation(operation, max_retries=3)

        assert operation.call_count == 1

    def test_retry_operation_exponential_backoff(self, mock_scraper):
        """Should use exponential backoff between retries"""
        operation = MagicMock(
            side_effect=[
                sqlite3.OperationalError("database is locked"),
                sqlite3.OperationalError("database is locked"),
                "success",
            ]
        )

        start_time = time.time()
        result = mock_scraper._retry_db_operation(operation, max_retries=3, initial_delay=0.05)
        elapsed = time.time() - start_time

        assert result == "success"
        assert operation.call_count == 3
        # Should have delays: 0.05s + 0.1s = 0.15s minimum
        assert elapsed >= 0.15

    def test_parse_page_handles_duplicate_job(self, mock_scraper):
        """Bug Fix #1: Should handle duplicate jobs (add_job returns None)"""
        # Mock database to return None for duplicate
        mock_scraper.database.add_job = MagicMock(return_value=None)

        # Mock parser to return a job
        mock_job = OpportunityData(
            source="ministry_of_testing",
            type="direct_job",
            title="Senior QA Engineer",
            company="Test Corp",
            location="Remote",
            link="https://example.com/job",
            posted_date="2024-01-15",
        )
        mock_scraper.mot_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(
            markdown=markdown, target_locations=["Remote"], min_score=47
        )

        # Should not attempt to score duplicate job
        assert stats["jobs_found"] == 1
        assert stats["jobs_stored"] == 0
        assert stats["jobs_scored"] == 0
        mock_scraper.multi_scorer.score_job_for_all.assert_not_called()

    def test_parse_page_handles_empty_profile_scores(self, mock_scraper):
        """Bug Fix #2: Should handle empty profile_scores (all profiles filtered job)"""
        # Mock database to return job_id
        mock_scraper.database.add_job = MagicMock(return_value=123)

        # Mock multi_scorer to return empty dict (all profiles filtered)
        mock_scraper.multi_scorer.score_job_for_all = MagicMock(return_value={})

        # Mock parser to return a job
        mock_job = OpportunityData(
            source="ministry_of_testing",
            type="direct_job",
            title="Software QA Engineer",
            company="Test Corp",
            location="Remote",
            link="https://example.com/job",
            posted_date="2024-01-15",
        )
        mock_scraper.mot_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(
            markdown=markdown, target_locations=["Remote"], min_score=47
        )

        # Should handle empty profile_scores without calling max()
        assert stats["jobs_found"] == 1
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1
        assert stats["profile_scores"] == {}

    def test_parse_page_successful_scoring(self, mock_scraper):
        """Should successfully score and store jobs with valid profile_scores"""
        # Mock database to return job_id
        mock_scraper.database.add_job = MagicMock(return_value=123)

        # Mock multi_scorer to return scores for multiple profiles
        mock_scraper.multi_scorer.score_job_for_all = MagicMock(
            return_value={"mario": (85, "A"), "wes": (65, "C")}
        )

        # Mock parser to return a job
        mock_job = OpportunityData(
            source="ministry_of_testing",
            type="direct_job",
            title="Senior QA Engineer",
            company="Hardware Corp",
            location="Remote",
            link="https://example.com/job",
            posted_date="2024-01-15",
        )
        mock_scraper.mot_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(
            markdown=markdown, target_locations=["Remote"], min_score=47
        )

        # Should successfully process job
        assert stats["jobs_found"] == 1
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1
        assert "mario" in stats["profile_scores"]
        assert "wes" in stats["profile_scores"]
        assert stats["profile_scores"]["mario"] == [(85, "A")]
        assert stats["profile_scores"]["wes"] == [(65, "C")]

    def test_parse_page_database_error_continues(self, mock_scraper):
        """Should continue processing after database errors"""
        # Mock database to raise error for first job, succeed for second
        mock_scraper.database.add_job = MagicMock(
            side_effect=[Exception("UNIQUE constraint failed"), 456]
        )

        mock_scraper.multi_scorer.score_job_for_all = MagicMock(return_value={"mario": (75, "B")})

        # Mock parser to return two jobs
        jobs = [
            OpportunityData(
                source="ministry_of_testing",
                type="direct_job",
                title="QA Engineer 1",
                company="Corp1",
                location="Remote",
                link="https://example.com/job1",
                posted_date="2024-01-15",
            ),
            OpportunityData(
                source="ministry_of_testing",
                type="direct_job",
                title="QA Engineer 2",
                company="Corp2",
                location="Remote",
                link="https://example.com/job2",
                posted_date="2024-01-16",
            ),
        ]
        mock_scraper.mot_scraper.parse_jobs_from_page = MagicMock(return_value=jobs)

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(
            markdown=markdown, target_locations=["Remote"], min_score=47
        )

        # Should skip first job but process second
        assert stats["jobs_found"] == 2
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1
