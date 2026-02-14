"""
Unit tests for TestDevJobs scraper
Tests for job parsing and multi-location scraping
"""

import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jobs.testdevjobs_scraper import TestDevJobsWeeklyScraper
from scrapers.testdevjobs_scraper import TestDevJobsScraper


class TestJobParsing:
    """Test parsing jobs from TestDevJobs markdown"""

    def test_parse_jobs_with_all_fields(self):
        """Should parse jobs with complete metadata (salary, tech tags, etc.)"""
        scraper = TestDevJobsScraper()

        markdown = """
[D](https://testdevjobs.com/job/deepgram-model-evaluation-qa-lead-17195/)

Deepgram

February 11, 2026

[Model Evaluation QA Lead](https://testdevjobs.com/job/deepgram-model-evaluation-qa-lead-17195/)

📍 United States
USD💵 $180,000 - $230,000🌐 Fully Remote
⏰ Full Time

[AWS](https://testdevjobs.com/tag/aws-testing-jobs/) [Python](https://testdevjobs.com/tag/python-testing-jobs/) [Jenkins](https://testdevjobs.com/tag/jenkins-testing-jobs/)
"""

        jobs = scraper.parse_jobs_from_page(markdown)

        assert len(jobs) == 1, f"Expected 1 job but got {len(jobs)}"

        job = jobs[0]
        assert job.company == "Deepgram"
        assert job.title == "Model Evaluation QA Lead"
        assert job.location == "United States"
        assert job.salary == "$180,000 - $230,000"
        assert job.remote_status == "Fully Remote"
        assert job.job_type == "Full Time"
        assert job.link == "https://testdevjobs.com/job/deepgram-model-evaluation-qa-lead-17195/"
        assert "AWS" in job.tech_tags
        assert "Python" in job.tech_tags
        assert "Jenkins" in job.tech_tags

    def test_parse_jobs_without_salary(self):
        """Should handle jobs without salary information"""
        scraper = TestDevJobsScraper()

        markdown = """
[N](https://testdevjobs.com/job/neoris-qa-engineer-17225/)

NEORIS

February 12, 2026

[QA Engineer](https://testdevjobs.com/job/neoris-qa-engineer-17225/)

📍 Colombia
🌐 Fully Remote
⏰ Full Time

[iOS](https://testdevjobs.com/tag/i-os-testing-jobs/) [Git](https://testdevjobs.com/tag/git-testing-jobs/)
"""

        jobs = scraper.parse_jobs_from_page(markdown)

        assert len(jobs) == 1
        job = jobs[0]
        assert job.company == "NEORIS"
        assert job.title == "QA Engineer"
        assert job.salary == ""  # No salary field
        assert job.remote_status == "Fully Remote"
        assert len(job.tech_tags) == 2

    def test_parse_multiple_jobs(self):
        """Should parse multiple jobs from single page"""
        scraper = TestDevJobsScraper()

        markdown = """
[P](https://testdevjobs.com/job/panoptyc-qa-engineering-manager-17221/)

Panoptyc

February 12, 2026

[QA Engineering Manager](https://testdevjobs.com/job/panoptyc-qa-engineering-manager-17221/)

📍 Argentina, Philippines
🌐 Fully Remote
⏰ Full Time

[Playwright](https://testdevjobs.com/tag/playwright-testing-jobs/)

[L](https://testdevjobs.com/job/litify-qa-engineer-17194/)

Litify

February 11, 2026

[QA Engineer](https://testdevjobs.com/job/litify-qa-engineer-17194/)

📍 United States
USD💵 $90,000 - $100,000🌐 Fully Remote
⏰ Full Time

[Playwright](https://testdevjobs.com/tag/playwright-testing-jobs/) [Cypress](https://testdevjobs.com/tag/cypress-testing-jobs/)
"""

        jobs = scraper.parse_jobs_from_page(markdown)

        assert len(jobs) == 2

        # Check first job
        assert jobs[0].company == "Panoptyc"
        assert jobs[0].title == "QA Engineering Manager"
        assert jobs[0].location == "Argentina, Philippines"

        # Check second job
        assert jobs[1].company == "Litify"
        assert jobs[1].title == "QA Engineer"
        assert jobs[1].salary == "$90,000 - $100,000"

    def test_parse_contract_and_internship_types(self):
        """Should handle different job types (Contract, Internship)"""
        scraper = TestDevJobsScraper()

        markdown = """
[H](https://testdevjobs.com/job/highlight-ta-qa-analyst-17181/)

HighlightTA

February 11, 2026

[QA Analyst](https://testdevjobs.com/job/highlight-ta-qa-analyst-17181/)

📍 New Zealand
🌐 Fully Remote
⏰ Contract

[B](https://testdevjobs.com/job/blaise-transit-qa-analyst-intern-summer-2026-17173/)

Blaise Transit

February 11, 2026

[QA Analyst Intern – Summer 2026](https://testdevjobs.com/job/blaise-transit-qa-analyst-intern-summer-2026-17173/)

📍 Canada
🌐 Fully Remote
⏰ Internship

[JavaScript](https://testdevjobs.com/tag/java-script-testing-jobs/)
"""

        jobs = scraper.parse_jobs_from_page(markdown)

        assert len(jobs) == 2
        assert jobs[0].job_type == "Contract"
        assert jobs[1].job_type == "Internship"

    def test_parse_empty_markdown(self):
        """Should return empty list for empty markdown"""
        scraper = TestDevJobsScraper()

        jobs = scraper.parse_jobs_from_page("")

        assert len(jobs) == 0

    def test_parse_jobs_with_no_tech_tags(self):
        """Should handle jobs without tech stack tags"""
        scraper = TestDevJobsScraper()

        markdown = """
[H](https://testdevjobs.com/job/henry-schein-quality-engineer-17164/)

Henry Schein

February 11, 2026

[Quality Engineer](https://testdevjobs.com/job/henry-schein-quality-engineer-17164/)

📍 United Kingdom
🌐 Fully Remote
⏰ Full Time
"""

        jobs = scraper.parse_jobs_from_page(markdown)

        assert len(jobs) == 1
        assert len(jobs[0].tech_tags) == 0


class TestTestDevJobsWeeklyScraper:
    """Test the main TestDevJobsWeeklyScraper class"""

    @pytest.fixture
    def mock_scraper(self):
        """Create a TestDevJobsWeeklyScraper with mocked dependencies"""
        with (
            patch("jobs.testdevjobs_scraper.JobDatabase"),
            patch("jobs.testdevjobs_scraper.get_multi_scorer"),
            patch("jobs.testdevjobs_scraper.TestDevJobsScraper"),
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}),
            patch("jobs.testdevjobs_scraper.FirecrawlApp"),
        ):
            scraper = TestDevJobsWeeklyScraper(profile="mario")
            return scraper

    def test_retry_operation_success_first_try(self, mock_scraper):
        """Should return result immediately on successful operation"""
        operation = MagicMock(return_value="success")

        result = mock_scraper._retry_db_operation(operation)

        assert result == "success"
        assert operation.call_count == 1

    def test_retry_operation_database_locked_then_success(self, mock_scraper):
        """Should retry on 'database is locked' error and succeed"""
        operation = MagicMock(
            side_effect=[sqlite3.OperationalError("database is locked"), "success"]
        )

        result = mock_scraper._retry_db_operation(operation, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert operation.call_count == 2

    def test_retry_operation_exhausts_retries(self, mock_scraper):
        """Should raise exception after max retries exhausted"""
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
        """Should handle duplicate jobs (add_job returns None)"""
        # Mock database to return None for duplicate
        mock_scraper.database.add_job = MagicMock(return_value=None)

        # Mock parser to return a job
        from scrapers.testdevjobs_scraper import TestDevJob

        mock_job = TestDevJob(
            company="Test Corp",
            title="Senior QA Engineer",
            location="Remote",
            link="https://testdevjobs.com/job/test",
            posted_date="February 11, 2026",
            salary="$100,000",
            remote_status="Fully Remote",
            job_type="Full Time",
            tech_tags=["Python", "AWS"],
        )
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(markdown=markdown, min_score=47)

        # Should not attempt to score duplicate job
        assert stats["jobs_found"] == 1  # type: ignore[operator]
        assert stats["jobs_stored"] == 0
        assert stats["jobs_scored"] == 0
        mock_scraper.multi_scorer.score_job_for_all.assert_not_called()

    def test_parse_page_handles_empty_profile_scores(self, mock_scraper):
        """Should handle empty profile_scores (all profiles filtered job)"""
        # Mock database to return job_id
        mock_scraper.database.add_job = MagicMock(return_value=123)

        # Mock multi_scorer to return empty dict (all profiles filtered)
        mock_scraper.multi_scorer.score_job_for_all = MagicMock(return_value={})

        # Mock parser to return a job
        from scrapers.testdevjobs_scraper import TestDevJob

        mock_job = TestDevJob(
            company="Test Corp",
            title="Software QA Engineer",
            location="Remote",
            link="https://testdevjobs.com/job/test",
            posted_date="February 11, 2026",
            salary="",
            remote_status="Fully Remote",
            job_type="Full Time",
            tech_tags=[],
        )
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(markdown=markdown, min_score=47)

        # Should handle empty profile_scores without calling max()
        assert stats["jobs_found"] == 1  # type: ignore[operator]
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
        from scrapers.testdevjobs_scraper import TestDevJob

        mock_job = TestDevJob(
            company="Hardware Corp",
            title="Senior QA Engineer",
            location="Remote",
            link="https://testdevjobs.com/job/test",
            posted_date="February 11, 2026",
            salary="$120,000",
            remote_status="Fully Remote",
            job_type="Full Time",
            tech_tags=["Selenium", "Python"],
        )
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(markdown=markdown, min_score=47)

        # Should successfully process job
        assert stats["jobs_found"] == 1  # type: ignore[operator]
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1
        assert "mario" in stats["profile_scores"]
        assert "wes" in stats["profile_scores"]
        assert stats["profile_scores"]["mario"] == [(85, "A")]
        assert stats["profile_scores"]["wes"] == [(65, "C")]

    def test_multi_location_stats_accumulation(self, mock_scraper):
        """Should correctly accumulate stats across multiple locations"""
        # Mock Firecrawl to return markdown for each location
        mock_document = MagicMock()
        mock_document.markdown = "test markdown"
        mock_scraper.firecrawl.scrape = MagicMock(return_value=mock_document)

        # Mock parser to return different number of jobs per location
        from scrapers.testdevjobs_scraper import TestDevJob

        job1 = TestDevJob(
            company="Corp1",
            title="QA Engineer",
            location="Canada",
            link="https://testdevjobs.com/job/1",
            posted_date="Feb 11",
            salary="",
            remote_status="Remote",
            job_type="Full Time",
            tech_tags=[],
        )
        job2 = TestDevJob(
            company="Corp2",
            title="Senior QA",
            location="US",
            link="https://testdevjobs.com/job/2",
            posted_date="Feb 11",
            salary="",
            remote_status="Remote",
            job_type="Full Time",
            tech_tags=[],
        )

        # First call returns 1 job, second call returns 2 jobs
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(
            side_effect=[[job1], [job2, job2]]
        )

        # Mock database and scorer
        mock_scraper.database.add_job = MagicMock(side_effect=[1, 2, 3])
        mock_scraper.multi_scorer.score_job_for_all = MagicMock(return_value={"mario": (75, "B")})

        stats = mock_scraper.scrape_testdevjobs(
            locations=["remote-canada", "remote-united-states"], min_score=47
        )

        # Stats should accumulate: 1 job from first location + 2 from second
        assert stats["pages_scraped"] == 2
        assert stats["jobs_found"] == 3  # 1 + 2
        assert stats["jobs_stored"] == 3
        assert stats["jobs_scored"] == 3

    def test_scrape_handles_firecrawl_errors(self, mock_scraper):
        """Should handle Firecrawl API errors gracefully"""
        # Mock Firecrawl to raise exception
        mock_scraper.firecrawl.scrape = MagicMock(side_effect=Exception("Firecrawl API error"))

        stats = mock_scraper.scrape_testdevjobs(locations=["remote-canada"], min_score=47)

        # Should return stats with 0 pages scraped (error logged and continued)
        assert stats["pages_scraped"] == 0
        assert stats["jobs_found"] == 0

    def test_scrape_handles_empty_markdown(self, mock_scraper):
        """Should handle empty/None markdown from Firecrawl"""
        # Mock Firecrawl to return empty markdown
        mock_document = MagicMock()
        mock_document.markdown = None
        mock_scraper.firecrawl.scrape = MagicMock(return_value=mock_document)

        stats = mock_scraper.scrape_testdevjobs(locations=["remote-canada"], min_score=47)

        # Should skip page with no markdown
        assert stats["pages_scraped"] == 0
        assert stats["jobs_found"] == 0

    def test_parse_page_handles_storage_errors(self, mock_scraper):
        """Should handle database storage errors (non-duplicate)"""
        # Mock database to raise non-duplicate error
        mock_scraper.database.add_job = MagicMock(side_effect=ValueError("Database error"))

        # Mock parser to return a job
        from scrapers.testdevjobs_scraper import TestDevJob

        mock_job = TestDevJob(
            company="Test Corp",
            title="QA Engineer",
            location="Remote",
            link="https://testdevjobs.com/job/test",
            posted_date="February 11, 2026",
            salary="",
            remote_status="Fully Remote",
            job_type="Full Time",
            tech_tags=[],
        )
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(markdown=markdown, min_score=47)

        # Should log error and continue
        assert stats["jobs_found"] == 1
        assert stats["jobs_stored"] == 0  # Failed to store
        assert stats["jobs_scored"] == 0  # Didn't reach scoring

    def test_parse_page_handles_scoring_errors(self, mock_scraper):
        """Should handle scoring errors gracefully"""
        # Mock database to return job_id
        mock_scraper.database.add_job = MagicMock(return_value=123)

        # Mock multi_scorer to raise exception
        mock_scraper.multi_scorer.score_job_for_all = MagicMock(
            side_effect=Exception("Scoring error")
        )

        # Mock parser to return a job
        from scrapers.testdevjobs_scraper import TestDevJob

        mock_job = TestDevJob(
            company="Test Corp",
            title="QA Engineer",
            location="Remote",
            link="https://testdevjobs.com/job/test",
            posted_date="February 11, 2026",
            salary="",
            remote_status="Fully Remote",
            job_type="Full Time",
            tech_tags=[],
        )
        mock_scraper.testdev_scraper.parse_jobs_from_page = MagicMock(return_value=[mock_job])

        markdown = "test markdown"
        stats = mock_scraper.parse_page_and_store(markdown=markdown, min_score=47)

        # Should store job but log scoring error
        assert stats["jobs_found"] == 1
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 0  # Scoring failed

    def test_print_summary(self, mock_scraper, capsys):
        """Should print formatted summary with stats"""
        stats = {
            "pages_scraped": 4,
            "jobs_found": 127,
            "jobs_stored": 100,
            "jobs_scored": 100,
            "profile_scores": {
                "mario": [(85, "A"), (75, "B"), (65, "C")],
                "wes": [(55, "C"), (45, "D")],
            },
        }

        mock_scraper.print_summary(stats)

        captured = capsys.readouterr()
        output = captured.out

        # Check key summary elements
        assert "TESTDEVJOBS SCRAPER - SUMMARY" in output
        assert "Pages scraped: 4" in output
        assert "Jobs found: 127" in output
        assert "Jobs stored: 100" in output
        assert "Jobs scored: 100" in output
        assert "mario:" in output
        assert "Total: 3 jobs" in output
        assert "Avg score: 75.0" in output
        assert "wes:" in output
        assert "Total: 2 jobs" in output
