"""
Unit tests for HybridJobScraper (orchestration)
"""

from unittest.mock import MagicMock, patch

import pytest

from jobs.hybrid_scraper import HybridJobScraper
from models import OpportunityData


@pytest.fixture
def mock_dependencies():
    """Mock all HybridJobScraper dependencies"""
    mock_career_scraper = MagicMock()
    with (
        patch("jobs.hybrid_scraper.CompanyService") as mock_company_service,
        patch("jobs.hybrid_scraper.CompanyDiscoverer") as mock_discoverer,
        patch.object(HybridJobScraper, "_create_scraper", return_value=mock_career_scraper),
        patch("jobs.hybrid_scraper.RoboticsDeeptechScraper") as mock_robotics,
        patch("jobs.hybrid_scraper.JobFilter") as mock_filter,
        patch("jobs.hybrid_scraper.ProfileScorer") as mock_scorer,
        patch("jobs.hybrid_scraper.JobDatabase") as mock_database,
        patch("jobs.hybrid_scraper.JobNotifier") as mock_notifier,
    ):
        yield {
            "company_service": mock_company_service.return_value,
            "discoverer": mock_discoverer.return_value,
            "firecrawl": mock_career_scraper,
            "robotics": mock_robotics.return_value,
            "filter": mock_filter.return_value,
            "scorer": mock_scorer.return_value,
            "database": mock_database.return_value,
            "notifier": mock_notifier.return_value,
        }


@pytest.fixture
def scraper(mock_dependencies):  # noqa: ARG001
    """Create HybridJobScraper with mocked dependencies"""
    return HybridJobScraper()


class TestHybridJobScraper:
    """Test HybridJobScraper orchestration"""

    def test_init_default_thresholds(self, mock_dependencies):  # noqa: ARG002
        """Test initialization with default parameters"""
        scraper = HybridJobScraper()

        assert scraper.similarity_threshold == 90.0
        assert scraper.min_score == 50
        assert scraper.notify_threshold == 80

    def test_init_custom_thresholds(self, mock_dependencies):  # noqa: ARG002
        """Test initialization with custom parameters"""
        scraper = HybridJobScraper(
            similarity_threshold=85.0,
            min_score=60,
            notify_threshold=90,
        )

        assert scraper.similarity_threshold == 85.0
        assert scraper.min_score == 60
        assert scraper.notify_threshold == 90

    def test_run_hybrid_scrape_discovery_only(self, scraper, mock_dependencies):
        """Test hybrid scrape with skip_scraping=True"""
        # Setup mocks
        mock_opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="robotics_sheet",
            )
        ]
        mock_dependencies["robotics"].scrape.return_value = mock_opportunities
        mock_dependencies["discoverer"].discover_from_robotics_sheet.return_value = [
            {"name": "Test Co", "careers_url": "https://example.com", "source": "robotics"}
        ]
        mock_dependencies["company_service"].add_companies_batch.return_value = {
            "added": 1,
            "skipped_duplicates": 0,
            "errors": 0,
            "details": [],
        }

        # Run with skip_scraping=True
        stats = scraper.run_hybrid_scrape(skip_scraping=True)

        assert stats["companies_discovered"] == 1
        assert stats["companies_added"] == 1
        assert stats["companies_scraped"] == 0  # No scraping
        assert stats["jobs_found"] == 0

    def test_run_hybrid_scrape_with_poc_companies(self, scraper, mock_dependencies):
        """Test hybrid scrape with POC company filter"""
        # Setup mocks
        mock_opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Boston Dynamics",
                location="Waltham, MA",
                link="https://bostondynamics.com/jobs/123",
                source="robotics_sheet",
            ),
            OpportunityData(
                type="direct_job",
                title="VP",
                company="Skydio",
                location="San Mateo, CA",
                link="https://skydio.com/jobs/456",
                source="robotics_sheet",
            ),
        ]
        mock_dependencies["robotics"].scrape.return_value = mock_opportunities
        mock_dependencies["discoverer"].discover_from_robotics_sheet.return_value = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"},
            {"name": "Skydio", "careers_url": "https://skydio.com"},
        ]
        mock_dependencies["discoverer"].filter_by_company_names.return_value = [
            {"name": "Boston Dynamics", "careers_url": "https://bostondynamics.com"}
        ]
        mock_dependencies["company_service"].add_companies_batch.return_value = {
            "added": 0,
            "skipped_duplicates": 1,
            "errors": 0,
            "details": [],
        }

        # Run with POC filter
        stats = scraper.run_hybrid_scrape(poc_companies=["Boston Dynamics"], skip_scraping=True)

        # Should have called filter
        mock_dependencies["discoverer"].filter_by_company_names.assert_called_once()
        assert stats["companies_discovered"] == 2  # Before filtering

    def test_run_hybrid_scrape_scrapes_newly_added_companies(self, scraper, mock_dependencies):
        """Test that newly added companies get scraped"""
        # Setup mocks
        mock_opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="New Company",
                location="Remote",
                link="https://newco.com/jobs/123",
                source="robotics_sheet",
            )
        ]
        mock_dependencies["robotics"].scrape.return_value = mock_opportunities
        mock_dependencies["discoverer"].discover_from_robotics_sheet.return_value = [
            {"name": "New Company", "careers_url": "https://newco.com"}
        ]
        mock_dependencies["company_service"].add_companies_batch.return_value = {
            "added": 1,
            "skipped_duplicates": 0,
            "errors": 0,
            "details": [{"company": "New Company", "status": "added", "url": "https://newco.com"}],
        }
        mock_dependencies["firecrawl"].scrape_jobs.return_value = []

        # Run scrape
        stats = scraper.run_hybrid_scrape(skip_scraping=False)

        assert stats["companies_added"] == 1
        assert stats["companies_scraped"] == 1
        # Firecrawl should have been called
        mock_dependencies["firecrawl"].scrape_jobs.assert_called_once_with(
            "https://newco.com", "New Company"
        )

    def test_scrape_company_no_jobs_found(self, scraper, mock_dependencies):
        """Test _scrape_company when no jobs found"""
        mock_dependencies["firecrawl"].scrape_jobs.return_value = []

        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["jobs_found"] == 0
        assert stats["leadership_jobs"] == 0
        assert stats["jobs_stored"] == 0

    def test_scrape_company_filters_leadership_roles(self, scraper, mock_dependencies):
        """Test _scrape_company only processes leadership roles"""
        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            ),
            OpportunityData(
                type="direct_job",
                title="Junior Engineer",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/456",
                source="company_monitoring",
            ),
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (85, "B", {}, {})
        mock_dependencies["database"].add_job.return_value = 1

        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["jobs_found"] == 2
        assert stats["leadership_jobs"] == 1  # Only director role
        assert stats["jobs_stored"] == 1

    def test_scrape_company_scores_and_stores_jobs(self, scraper, mock_dependencies):
        """Test _scrape_company scores and stores qualifying jobs"""
        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="VP of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (92, "A", {"seniority": 30}, {})
        mock_dependencies["database"].add_job.return_value = 1

        stats = scraper._scrape_company("Test Co", "https://example.com")

        # Should have scored the job
        mock_dependencies["scorer"].score_job.assert_called_once()
        # Should have stored the job
        mock_dependencies["database"].add_job.assert_called_once()
        mock_dependencies["database"].update_job_score.assert_called_once()
        assert stats["jobs_stored"] == 1

    def test_scrape_company_skips_low_score_jobs(self, scraper, mock_dependencies):
        """Test _scrape_company skips jobs below min_score"""
        scraper.min_score = 50

        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Sales",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (35, "F", {}, {})  # Below threshold

        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["leadership_jobs"] == 1
        assert stats["jobs_stored"] == 0  # Not stored due to low score
        mock_dependencies["database"].add_job.assert_not_called()

    def test_scrape_company_sends_notification_for_high_scores(self, scraper, mock_dependencies):
        """Test _scrape_company sends notifications for A/B grade jobs"""
        scraper.notify_threshold = 80

        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="VP of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (92, "A", {}, {})
        mock_dependencies["database"].add_job.return_value = 1
        mock_dependencies["notifier"].notify_job.return_value = {"email": True, "sms": True}

        stats = scraper._scrape_company("Test Co", "https://example.com")

        # Should have sent notification
        mock_dependencies["notifier"].notify_job.assert_called_once()
        mock_dependencies["database"].mark_notified.assert_called_once_with(1)
        assert stats["notifications_sent"] == 1

    def test_scrape_company_no_notification_below_threshold(self, scraper, mock_dependencies):
        """Test _scrape_company does not notify for scores below threshold"""
        scraper.notify_threshold = 80
        scraper.min_score = 50

        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (65, "C", {}, {})  # Below notify
        mock_dependencies["database"].add_job.return_value = 1

        stats = scraper._scrape_company("Test Co", "https://example.com")

        # Should store but not notify
        assert stats["jobs_stored"] == 1
        assert stats["notifications_sent"] == 0
        mock_dependencies["notifier"].notify_job.assert_not_called()

    def test_scrape_company_handles_duplicates(self, scraper, mock_dependencies):
        """Test _scrape_company tracks duplicate jobs"""
        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="Director of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (85, "B", {}, {})
        mock_dependencies["database"].add_job.return_value = None  # Duplicate

        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["duplicates_skipped"] == 1
        assert stats["jobs_stored"] == 0
        mock_dependencies["database"].update_job_score.assert_not_called()

    def test_scrape_company_handles_notification_error(self, scraper, mock_dependencies):
        """Test _scrape_company handles notification failures gracefully"""
        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="VP of Engineering",
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            )
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs
        mock_dependencies["scorer"].score_job.return_value = (92, "A", {}, {})
        mock_dependencies["database"].add_job.return_value = 1
        mock_dependencies["notifier"].notify_job.side_effect = Exception("Email failed")

        # Should not crash
        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["jobs_stored"] == 1
        assert stats["notifications_sent"] == 0  # Failed to send

    def test_scrape_company_with_non_leadership_title(self, scraper, mock_dependencies):
        """Test _scrape_company filters out non-leadership roles"""
        mock_jobs = [
            OpportunityData(
                type="direct_job",
                title="Software Engineer",  # Not leadership
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/123",
                source="company_monitoring",
            ),
            OpportunityData(
                type="direct_job",
                title="Junior Developer",  # Not leadership
                company="Test Co",
                location="Remote",
                link="https://example.com/jobs/456",
                source="company_monitoring",
            ),
        ]
        mock_dependencies["firecrawl"].scrape_jobs.return_value = mock_jobs

        stats = scraper._scrape_company("Test Co", "https://example.com")

        assert stats["jobs_found"] == 2
        assert stats["leadership_jobs"] == 0  # No leadership roles
        assert stats["jobs_stored"] == 0

    def test_run_hybrid_scrape_no_new_companies(self, scraper, mock_dependencies):
        """Test hybrid scrape when all companies already exist"""
        mock_opportunities = [
            OpportunityData(
                type="direct_job",
                title="Director",
                company="Existing Co",
                location="Remote",
                link="https://existing.com/jobs/123",
                source="robotics_sheet",
            )
        ]
        mock_dependencies["robotics"].scrape.return_value = mock_opportunities
        mock_dependencies["discoverer"].discover_from_robotics_sheet.return_value = [
            {"name": "Existing Co", "careers_url": "https://existing.com"}
        ]
        mock_dependencies["company_service"].add_companies_batch.return_value = {
            "added": 0,  # All duplicates
            "skipped_duplicates": 1,
            "errors": 0,
            "details": [],
        }

        stats = scraper.run_hybrid_scrape(skip_scraping=False)

        assert stats["companies_discovered"] == 1
        assert stats["companies_added"] == 0
        assert stats["companies_scraped"] == 0  # Nothing new to scrape
