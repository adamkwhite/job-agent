"""
Tests for relative URL resolution in BaseCareerScraper (PR #352).

Cheaper LLM models (e.g. Gemini Flash) return relative URLs like "/jobs/123"
instead of full URLs. These tests verify that _validate_job_urls resolves
relative URLs against the base career page URL before validation.
"""

from unittest.mock import MagicMock, patch

from src.models import OpportunityData
from src.scrapers.base_career_scraper import BaseCareerScraper


def _make_job(link: str, title: str = "VP Engineering") -> OpportunityData:
    """Create a minimal OpportunityData for testing."""
    return OpportunityData(
        source="company_monitoring",
        source_email=None,
        type="direct_job",
        company="TestCorp",
        title=title,
        location="Remote",
        link=link,
        description=None,
        salary=None,
        job_type=None,
        posted_date=None,
        needs_research=False,
    )


def _create_scraper() -> BaseCareerScraper:
    """Create a concrete scraper subclass for testing abstract base."""

    class ConcreteScraper(BaseCareerScraper):
        def _fetch_page_content(self, url: str) -> str | None:
            return "<html></html>"

    with patch("src.scrapers.base_career_scraper.Path.mkdir"):
        return ConcreteScraper(enable_llm_extraction=False)


class TestRelativeUrlResolution:
    """Test _validate_job_urls resolves relative URLs against base_url."""

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_relative_url_resolved(self, _mock_validate):
        """Relative URLs like '/jobs/123' should be resolved to full URLs."""
        scraper = _create_scraper()
        jobs = [_make_job("/careers/vp-engineering")]

        result = scraper._validate_job_urls(
            jobs, "TestCorp", base_url="https://testcorp.com/careers"
        )

        assert len(result) == 1
        assert result[0].link == "https://testcorp.com/careers/vp-engineering"

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_absolute_url_unchanged(self, _mock_validate):
        """Absolute URLs should not be modified even with base_url."""
        scraper = _create_scraper()
        original_url = "https://other.com/jobs/456"
        jobs = [_make_job(original_url)]

        result = scraper._validate_job_urls(
            jobs, "TestCorp", base_url="https://testcorp.com/careers"
        )

        assert len(result) == 1
        assert result[0].link == original_url

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_no_base_url_relative_stays_relative(self, _mock_validate):
        """Without base_url, relative URLs are passed through as-is."""
        scraper = _create_scraper()
        jobs = [_make_job("/jobs/123")]

        result = scraper._validate_job_urls(jobs, "TestCorp", base_url=None)

        assert len(result) == 1
        assert result[0].link == "/jobs/123"

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_no_link_skips_resolution(self, _mock_validate):
        """Jobs with no link should be passed through without resolution."""
        scraper = _create_scraper()
        jobs = [_make_job(link=None)]

        result = scraper._validate_job_urls(jobs, "TestCorp", base_url="https://testcorp.com")

        assert len(result) == 1
        assert result[0].link is None

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_multiple_jobs_mixed_urls(self, _mock_validate):
        """Mix of relative and absolute URLs should each be handled correctly."""
        scraper = _create_scraper()
        jobs = [
            _make_job("/remote-job/vp-engineering", "VP Engineering"),
            _make_job("https://boards.greenhouse.io/company/jobs/789", "Director Ops"),
            _make_job("/jobs/lead-robotics", "Lead Robotics"),
        ]

        result = scraper._validate_job_urls(
            jobs, "TestCorp", base_url="https://testcorp.com/careers"
        )

        assert len(result) == 3
        assert result[0].link == "https://testcorp.com/remote-job/vp-engineering"
        assert result[1].link == "https://boards.greenhouse.io/company/jobs/789"
        assert result[2].link == "https://testcorp.com/jobs/lead-robotics"


class TestProcessExtractedJobsBaseUrl:
    """Test _process_extracted_jobs threads base_url to validation."""

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_base_url_threaded_to_validation(self, _mock_validate):
        """base_url param should reach _validate_job_urls."""
        scraper = _create_scraper()
        jobs = [_make_job("/jobs/123")]

        result = scraper._process_extracted_jobs(
            jobs, "TestCorp", "llm", base_url="https://testcorp.com/careers"
        )

        assert len(result) == 1
        job, method = result[0]
        assert method == "llm"
        assert job.link == "https://testcorp.com/jobs/123"


class TestRunLlmExtractionBaseUrl:
    """Test _run_llm_extraction threads base_url."""

    @patch("src.scrapers.base_career_scraper.validate_job_url", return_value=(True, None))
    def test_llm_extraction_passes_base_url(self, _mock_validate):
        """LLM extraction should resolve relative URLs via base_url."""
        scraper = _create_scraper()
        scraper.enable_llm_extraction = True

        mock_extractor = MagicMock()
        mock_extractor.extract_jobs.return_value = [_make_job("/jobs/llm-found")]
        scraper.llm_extractor = mock_extractor

        result = scraper._run_llm_extraction(
            "# Careers\nSome markdown", "TestCorp", base_url="https://testcorp.com"
        )

        assert len(result) == 1
        job, method = result[0]
        assert method == "llm"
        assert job.link == "https://testcorp.com/jobs/llm-found"
