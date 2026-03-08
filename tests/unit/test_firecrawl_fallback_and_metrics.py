"""
Tests for Firecrawl fallback (Issue #342) and extraction metrics (Issue #343).

Tests the fallback mechanism when primary scraper returns 0 jobs,
and the per-run extraction metrics recording.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.jobs.company_scraper import CompanyScraper


@pytest.fixture
def company_scraper():
    """Create CompanyScraper with mocked dependencies."""
    with (
        patch("src.jobs.company_scraper.CompanyService"),
        patch("src.scrapers.playwright_career_scraper.PlaywrightCareerScraper"),
        patch("src.jobs.company_scraper.JobFilter"),
        patch("src.jobs.company_scraper.ProfileScorer"),
        patch("src.jobs.company_scraper.JobDatabase"),
        patch("src.jobs.company_scraper.JobNotifier"),
    ):
        scraper = CompanyScraper()
        scraper.company_service.increment_company_failures = MagicMock(return_value=1)
        return scraper


class TestGetFallbackScraper:
    """Test _get_fallback_scraper lazy initialization."""

    def test_returns_none_when_already_firecrawl(self, company_scraper):
        """No fallback needed if primary is already Firecrawl."""
        company_scraper.backend = "firecrawl"
        assert company_scraper._get_fallback_scraper() is None

    def test_creates_firecrawl_scraper_on_first_call(self, company_scraper):
        """Should lazy-init a Firecrawl scraper on first call."""
        company_scraper.backend = "crawl4ai"
        mock_scraper = MagicMock()
        with patch.object(CompanyScraper, "_create_career_scraper", return_value=mock_scraper):
            result = company_scraper._get_fallback_scraper()
        assert result is mock_scraper

    def test_caches_fallback_scraper(self, company_scraper):
        """Should return same instance on subsequent calls."""
        company_scraper.backend = "playwright"
        mock_scraper = MagicMock()
        company_scraper._fallback_scraper = mock_scraper
        result = company_scraper._get_fallback_scraper()
        assert result is mock_scraper

    def test_returns_none_on_creation_failure(self, company_scraper):
        """Should return None if Firecrawl scraper creation fails."""
        company_scraper.backend = "crawl4ai"
        with patch.object(
            CompanyScraper, "_create_career_scraper", side_effect=Exception("No API key")
        ):
            result = company_scraper._get_fallback_scraper()
        assert result is None


class TestRecordExtractionMetrics:
    """Test _record_extraction_metrics method."""

    def test_records_regex_and_llm_counts(self, company_scraper):
        """Should count regex vs LLM jobs and pass to database."""
        jobs = [
            (MagicMock(), "regex"),
            (MagicMock(), "regex"),
            (MagicMock(), "llm"),
        ]
        company_scraper._record_extraction_metrics(
            "Acme Corp", "https://acme.com/careers", jobs, "crawl4ai"
        )
        company_scraper.database.store_extraction_metrics.assert_called_once_with(
            company_name="Acme Corp",
            regex_jobs_found=2,
            llm_jobs_found=1,
            total_jobs_found=3,
            scraper_backend="crawl4ai",
            careers_url="https://acme.com/careers",
            fetch_success=True,
        )

    def test_records_zero_jobs_with_fetch_failure(self, company_scraper):
        """Should record fetch_success=False when no jobs found."""
        company_scraper._record_extraction_metrics(
            "FailCorp", "https://fail.com/careers", [], "playwright", fetch_success=False
        )
        company_scraper.database.store_extraction_metrics.assert_called_once_with(
            company_name="FailCorp",
            regex_jobs_found=0,
            llm_jobs_found=0,
            total_jobs_found=0,
            scraper_backend="playwright",
            careers_url="https://fail.com/careers",
            fetch_success=False,
        )

    def test_records_all_regex_jobs(self, company_scraper):
        """Should handle jobs with only regex extraction."""
        jobs = [(MagicMock(), "regex")] * 5
        company_scraper._record_extraction_metrics(
            "RegexCo", "https://regex.com/careers", jobs, "firecrawl"
        )
        call_kwargs = company_scraper.database.store_extraction_metrics.call_args[1]
        assert call_kwargs["regex_jobs_found"] == 5
        assert call_kwargs["llm_jobs_found"] == 0
        assert call_kwargs["total_jobs_found"] == 5


class TestFallbackInScrapeLoop:
    """Test Firecrawl fallback integration in scrape_all_companies."""

    def _setup_companies(self, scraper, companies):
        """Helper to set up company list for scraping."""
        scraper.company_service.get_all_companies = MagicMock(return_value=companies)
        scraper.company_service.get_company_failures = MagicMock(return_value=0)

    def test_fallback_triggered_when_primary_returns_zero(self, company_scraper):
        """Should try Firecrawl when primary scraper finds 0 jobs."""
        companies = [
            {
                "id": 1,
                "name": "BlockedCo",
                "careers_url": "https://blocked.com/careers",
                "notes": "",
            },
        ]
        self._setup_companies(company_scraper, companies)

        # Primary returns empty, fallback returns jobs
        fallback_jobs = [(MagicMock(), "regex"), (MagicMock(), "regex")]
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.backend = "crawl4ai"

        mock_fallback = MagicMock()
        mock_fallback.scrape_jobs = MagicMock(return_value=fallback_jobs)
        company_scraper._fallback_scraper = mock_fallback

        stats = company_scraper.scrape_all_companies()

        # Fallback should have been called
        mock_fallback.scrape_jobs.assert_called_once_with(
            careers_url="https://blocked.com/careers",
            company_name="BlockedCo",
        )
        assert stats["jobs_scraped"] == 2

    def test_no_fallback_when_primary_finds_jobs(self, company_scraper):
        """Should NOT try Firecrawl when primary scraper succeeds."""
        companies = [
            {"id": 1, "name": "GoodCo", "careers_url": "https://good.com/careers", "notes": ""},
        ]
        self._setup_companies(company_scraper, companies)

        primary_jobs = [(MagicMock(), "regex")]
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=primary_jobs)
        company_scraper.backend = "crawl4ai"

        mock_fallback = MagicMock()
        company_scraper._fallback_scraper = mock_fallback

        company_scraper.scrape_all_companies()

        # Fallback should NOT have been called
        mock_fallback.scrape_jobs.assert_not_called()

    def test_no_fallback_when_backend_is_firecrawl(self, company_scraper):
        """Should NOT try fallback when already using Firecrawl."""
        companies = [
            {"id": 1, "name": "FailCo", "careers_url": "https://fail.com/careers", "notes": ""},
        ]
        self._setup_companies(company_scraper, companies)

        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.backend = "firecrawl"

        stats = company_scraper.scrape_all_companies()

        # Should still be in failed extractions
        assert len(stats["failed_extractions"]) == 1

    def test_metrics_recorded_for_primary_and_fallback(self, company_scraper):
        """Should record metrics for both primary and fallback attempts."""
        companies = [
            {"id": 1, "name": "TestCo", "careers_url": "https://test.com/careers", "notes": ""},
        ]
        self._setup_companies(company_scraper, companies)

        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=[])
        company_scraper.backend = "crawl4ai"

        mock_fallback = MagicMock()
        mock_fallback.scrape_jobs = MagicMock(return_value=[(MagicMock(), "regex")])
        company_scraper._fallback_scraper = mock_fallback

        company_scraper.scrape_all_companies()

        # Should have recorded metrics twice: once for primary, once for fallback
        assert company_scraper.database.store_extraction_metrics.call_count == 2
        calls = company_scraper.database.store_extraction_metrics.call_args_list

        # First call: primary (crawl4ai, 0 jobs)
        assert calls[0][1]["scraper_backend"] == "crawl4ai"
        assert calls[0][1]["total_jobs_found"] == 0

        # Second call: fallback (firecrawl, 1 job)
        assert calls[1][1]["scraper_backend"] == "firecrawl"
        assert calls[1][1]["total_jobs_found"] == 1

    def test_metrics_recorded_for_successful_primary(self, company_scraper):
        """Should record metrics even when primary succeeds (no fallback)."""
        companies = [
            {"id": 1, "name": "OkCo", "careers_url": "https://ok.com/careers", "notes": ""},
        ]
        self._setup_companies(company_scraper, companies)

        primary_jobs = [(MagicMock(), "regex"), (MagicMock(), "llm")]
        company_scraper.career_scraper.scrape_jobs = MagicMock(return_value=primary_jobs)
        company_scraper.backend = "playwright"

        company_scraper.scrape_all_companies()

        # Should have recorded exactly once (primary only)
        company_scraper.database.store_extraction_metrics.assert_called_once()
        call_kwargs = company_scraper.database.store_extraction_metrics.call_args[1]
        assert call_kwargs["scraper_backend"] == "playwright"
        assert call_kwargs["regex_jobs_found"] == 1
        assert call_kwargs["llm_jobs_found"] == 1
        assert call_kwargs["total_jobs_found"] == 2


class TestStoreExtractionMetrics:
    """Test database.store_extraction_metrics with new columns."""

    def test_store_with_new_fields(self, tmp_path):
        """Should store metrics including backend, URL, and fetch_success."""
        from src.database import JobDatabase

        db = JobDatabase(str(tmp_path / "test.db"))
        row_id = db.store_extraction_metrics(
            company_name="TestCo",
            regex_jobs_found=3,
            llm_jobs_found=1,
            total_jobs_found=4,
            scraper_backend="crawl4ai",
            careers_url="https://test.com/careers",
            fetch_success=True,
        )
        assert row_id > 0

    def test_store_with_defaults(self, tmp_path):
        """Should work with just company_name (all others default)."""
        from src.database import JobDatabase

        db = JobDatabase(str(tmp_path / "test.db"))
        row_id = db.store_extraction_metrics(company_name="MinimalCo")
        assert row_id > 0

    def test_unique_constraint_includes_backend(self, tmp_path):
        """Same company+date with different backends should both store."""
        from src.database import JobDatabase

        db = JobDatabase(str(tmp_path / "test.db"))
        id1 = db.store_extraction_metrics(company_name="DualCo", scraper_backend="crawl4ai")
        id2 = db.store_extraction_metrics(company_name="DualCo", scraper_backend="firecrawl")
        # Both should succeed (different backends = different unique keys)
        assert id1 > 0
        assert id2 > 0

    def test_fetch_success_stored_as_integer(self, tmp_path):
        """fetch_success bool should be stored as 0/1 integer."""
        import sqlite3

        from src.database import JobDatabase

        db = JobDatabase(str(tmp_path / "test.db"))
        db.store_extraction_metrics(
            company_name="BoolCo",
            scraper_backend="playwright",
            fetch_success=False,
        )
        # Query raw DB to verify integer storage
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.execute(
            "SELECT fetch_success FROM extraction_metrics WHERE company_name = ?",
            ("BoolCo",),
        )
        row = cursor.fetchone()
        conn.close()
        assert row[0] == 0
