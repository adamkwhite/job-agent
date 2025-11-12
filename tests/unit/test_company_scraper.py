"""
Tests for CompanyScraper

Tests company monitoring scraping functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.jobs.company_scraper import CompanyScraper
from src.models import OpportunityData


@pytest.fixture
def company_scraper():
    """Create CompanyScraper instance with mocked dependencies"""
    with (
        patch("src.jobs.company_scraper.CompanyService"),
        patch("src.jobs.company_scraper.FirecrawlCareerScraper"),
        patch("src.jobs.company_scraper.JobFilter"),
        patch("src.jobs.company_scraper.JobScorer"),
        patch("src.jobs.company_scraper.JobDatabase"),
        patch("src.jobs.company_scraper.JobNotifier"),
    ):
        scraper = CompanyScraper()
        return scraper


class TestCompanyScraperInit:
    """Test CompanyScraper initialization"""

    def test_init_creates_dependencies(self, company_scraper):
        """Should initialize all required dependencies"""
        assert company_scraper.company_service is not None
        assert company_scraper.firecrawl_scraper is not None
        assert company_scraper.job_filter is not None
        assert company_scraper.scorer is not None
        assert company_scraper.database is not None
        assert company_scraper.notifier is not None


class TestScrapeAllCompanies:
    """Test scrape_all_companies method"""

    def test_scrape_all_companies_returns_stats(self, company_scraper):
        """Should return statistics dictionary"""
        # Mock company service to return empty list
        company_scraper.company_service.get_all_companies = MagicMock(return_value=[])

        stats = company_scraper.scrape_all_companies()

        assert isinstance(stats, dict)
        assert "companies_checked" in stats
        assert "jobs_scraped" in stats
        assert "jobs_stored" in stats

    def test_scrape_all_companies_processes_companies(self, company_scraper):
        """Should process each company"""
        # Mock company data
        companies = [
            {
                "id": 1,
                "name": "Test Company",
                "careers_url": "https://test.com/careers",
                "notes": "From Wes",
            }
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.firecrawl_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies()

        assert stats["companies_checked"] == 1
        company_scraper.firecrawl_scraper.scrape_jobs.assert_called_once()

    def test_scrape_all_companies_filters_by_notes(self, company_scraper):
        """Should filter companies by notes when company_filter provided"""
        companies = [
            {
                "id": 1,
                "name": "Wes Company",
                "careers_url": "https://test1.com",
                "notes": "From Wes",
            },
            {
                "id": 2,
                "name": "Other Company",
                "careers_url": "https://test2.com",
                "notes": "Other",
            },
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.firecrawl_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies(company_filter="From Wes")

        # Should only process the one company matching filter
        assert stats["companies_checked"] == 1

    def test_scrape_all_companies_handles_scraping_errors(self, company_scraper):
        """Should handle scraping errors gracefully"""
        companies = [
            {"id": 1, "name": "Test Company", "careers_url": "https://test.com", "notes": "Test"}
        ]
        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.firecrawl_scraper.scrape_jobs = MagicMock(
            side_effect=Exception("Scraping failed")
        )
        company_scraper.company_service.update_last_checked = MagicMock()

        stats = company_scraper.scrape_all_companies()

        assert stats["companies_checked"] == 1
        assert stats["scraping_errors"] == 1


class TestProcessScrapedJobs:
    """Test process_scraped_jobs method"""

    def test_process_scraped_jobs_filters_leadership(self, company_scraper):
        """Should filter for leadership roles"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job1",
                source="company_monitoring",
            ),
            OpportunityData(
                type="direct_job",
                title="Software Engineer",
                company="Test Company",
                location="Remote",
                link="https://test.com/job2",
                source="company_monitoring",
            ),
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(side_effect=[True, False])
        company_scraper.scorer.score_job = MagicMock(return_value=(75, "B", "{}"))
        company_scraper.database.job_exists = MagicMock(return_value=False)
        company_scraper.database.add_job = MagicMock()
        company_scraper.notifier.notify = MagicMock()

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should process leadership job but not IC role
        assert stats["leadership_jobs"] == 1

    def test_process_scraped_jobs_applies_min_score(self, company_scraper):
        """Should only store jobs above minimum score"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(
            return_value=(45, "F", "{}")
        )  # Below threshold
        company_scraper.database.job_exists = MagicMock(return_value=False)

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Job scored 45, min is 50, should not be stored
        assert stats["jobs_stored"] == 0

    def test_process_scraped_jobs_stores_high_score_job(self, company_scraper):
        """Should store jobs above minimum score"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(return_value=(75, "B", "{}"))
        company_scraper.database.job_exists = MagicMock(return_value=False)
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.notifier.notify_job = MagicMock()

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should store job with 75 score (above 50 min)
        assert stats["jobs_above_threshold"] == 1
        assert stats["jobs_stored"] == 1
        company_scraper.database.add_job.assert_called_once()
        company_scraper.database.update_job_score.assert_called_once()

    def test_process_scraped_jobs_sends_notifications_for_high_scores(self, company_scraper):
        """Should send notifications for jobs above notify threshold"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="VP of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(return_value=(85, "A", "{}"))
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.database.mark_notified = MagicMock()
        company_scraper.notifier.notify_job = MagicMock(return_value={"email": True, "sms": False})

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should send notification for 85 score (above 80 threshold)
        assert stats["notifications_sent"] == 1
        company_scraper.notifier.notify_job.assert_called_once()
        company_scraper.database.mark_notified.assert_called_once_with(1)

    def test_process_scraped_jobs_handles_notification_errors(self, company_scraper):
        """Should handle notification errors gracefully"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="VP of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(return_value=(85, "A", "{}"))
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.notifier.notify_job = MagicMock(
            side_effect=Exception("Notification failed")
        )

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should not crash but also not count notification as sent
        assert stats["notifications_sent"] == 0
        assert stats["jobs_stored"] == 1

    def test_process_scraped_jobs_skips_duplicates(self, company_scraper):
        """Should skip duplicate jobs"""
        jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(return_value=(75, "B", "{}"))
        company_scraper.database.add_job = MagicMock(return_value=None)  # None means duplicate

        stats = company_scraper.process_scraped_jobs(
            "Test Company", jobs, min_score=50, notify_threshold=80
        )

        # Should skip duplicate
        assert stats["duplicates_skipped"] == 1
        assert stats["jobs_stored"] == 0

    def test_scrape_all_companies_aggregates_job_stats(self, company_scraper):
        """Should aggregate stats from processed jobs"""
        companies = [
            {
                "id": 1,
                "name": "Test Company",
                "careers_url": "https://test.com/careers",
                "notes": "Test",
            }
        ]
        jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Company",
                location="Remote",
                link="https://test.com/job",
                source="company_monitoring",
            )
        ]

        company_scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        company_scraper.firecrawl_scraper.scrape_jobs = MagicMock(return_value=jobs)
        company_scraper.company_service.update_last_checked = MagicMock()
        company_scraper.job_filter.is_leadership_role = MagicMock(return_value=True)
        company_scraper.scorer.score_job = MagicMock(return_value=(75, "B", "{}"))
        company_scraper.database.add_job = MagicMock(return_value=1)
        company_scraper.database.update_job_score = MagicMock()
        company_scraper.notifier.notify_job = MagicMock()

        stats = company_scraper.scrape_all_companies()

        # Should aggregate stats properly
        assert stats["companies_checked"] == 1
        assert stats["jobs_scraped"] == 1
        assert stats["leadership_jobs"] == 1
        assert stats["jobs_above_threshold"] == 1
        assert stats["jobs_stored"] == 1
