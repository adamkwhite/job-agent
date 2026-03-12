"""Tests for RLS Job Board scraper"""

from unittest.mock import MagicMock, patch

import pytest

from jobs.rls_scraper import RLSJobBoardScraper

SAMPLE_API_RESPONSE = [
    {
        "id": "1",
        "role_title": "Lead, Technical Product Manager",
        "company": "EdReports",
        "company_description": "Nonprofit education focused",
        "company_logo_url": "https://example.com/logo.png",
        "location": "United States",
        "remote_status": "Remote",
        "salary_range": "$102,824–$139,114",
        "experience_level": "Senior",
        "is_management": True,
        "job_function": "Product",
        "role_type": "Full-time",
        "job_description": "Lead product management...",
        "url": "https://edreports.org/careers/tpm",
        "extracted_at": "2026-03-10T12:00:00",
        "classification": "tech",
    },
    {
        "id": "2",
        "role_title": "Product Design Manager",
        "company": "Everlaw",
        "company_description": "Legal tech/ediscovery",
        "company_logo_url": "https://example.com/logo2.png",
        "location": "Oakland, CA",
        "remote_status": "Hybrid",
        "salary_range": "$192,000–$243,000",
        "experience_level": "Senior",
        "is_management": True,
        "job_function": "Design",
        "role_type": "Full-time",
        "job_description": "Manage design team...",
        "url": "https://everlaw.com/careers/design-mgr",
        "extracted_at": "2026-03-10T14:00:00",
        "classification": "tech",
    },
    {
        "id": "3",
        "role_title": "Backend Engineer",
        "company": "SumUp",
        "company_description": "Fintech payments",
        "company_logo_url": "",
        "location": "Berlin, Germany",
        "remote_status": "Onsite",
        "salary_range": "",
        "experience_level": "Mid",
        "is_management": False,
        "job_function": "Engineering",
        "role_type": "Full-time",
        "job_description": "Build backend services...",
        "url": "https://sumup.com/careers/backend",
        "extracted_at": "2026-03-10T16:00:00",
        "classification": "tech",
    },
]


class TestBuildJobDict:
    """Tests for _build_job_dict field mapping"""

    def test_basic_fields(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert result["title"] == "Lead, Technical Product Manager"
        assert result["company"] == "EdReports"
        assert result["link"] == "https://edreports.org/careers/tpm"
        assert result["source"] == "rls_job_board"
        assert result["salary"] == "$102,824–$139,114"
        assert result["job_type"] == "Full-time"

    def test_remote_location_format(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert result["location"] == "United States (Remote)"

    def test_hybrid_location_format(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[1])
        assert result["location"] == "Oakland, CA (Hybrid)"

    def test_onsite_location_no_suffix(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[2])
        assert result["location"] == "Berlin, Germany"

    def test_description_includes_experience(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert "Experience: Senior" in result["description"]

    def test_description_includes_function(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert "Function: Product" in result["description"]

    def test_description_includes_management(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert "Management role" in result["description"]

    def test_description_excludes_management_when_false(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[2])
        assert "Management role" not in result["description"]

    def test_empty_salary(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[2])
        assert result["salary"] == ""

    def test_posted_date_from_extracted_at(self) -> None:
        result = RLSJobBoardScraper._build_job_dict(SAMPLE_API_RESPONSE[0])
        assert result["posted_date"] == "2026-03-10T12:00:00"

    def test_missing_fields_handled(self) -> None:
        """Handles jobs with missing optional fields"""
        minimal_job = {
            "role_title": "Manager",
            "company": "Acme",
            "url": "https://example.com",
        }
        result = RLSJobBoardScraper._build_job_dict(minimal_job)
        assert result["title"] == "Manager"
        assert result["company"] == "Acme"
        assert result["location"] == ""
        assert result["salary"] == ""


class TestScrapeRlsJobs:
    """Tests for the full scrape flow"""

    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_successful_scrape(
        self, mock_get: MagicMock, mock_db_cls: MagicMock, mock_scorer: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_db.add_job.side_effect = [100, 101, 102]
        mock_db_cls.return_value = mock_db

        mock_multi = MagicMock()
        mock_multi.score_job_for_all.return_value = {"adam": (75, "B")}
        mock_scorer.return_value = mock_multi

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 3
        assert stats["jobs_stored"] == 3
        assert stats["jobs_scored"] == 3
        assert mock_db.add_job.call_count == 3

    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_duplicates_not_counted(
        self, mock_get: MagicMock, mock_db_cls: MagicMock, mock_scorer: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE[:2]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_db.add_job.side_effect = [100, None]  # Second is duplicate
        mock_db_cls.return_value = mock_db

        mock_multi = MagicMock()
        mock_multi.score_job_for_all.return_value = {"adam": (65, "C")}
        mock_scorer.return_value = mock_multi

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 2
        assert stats["jobs_stored"] == 1
        assert stats["jobs_scored"] == 1

    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_api_failure_returns_error(
        self, mock_get: MagicMock, mock_db_cls: MagicMock, mock_scorer: MagicMock
    ) -> None:
        import requests

        mock_get.side_effect = requests.RequestException("Connection refused")

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 0
        assert "error" in stats
        assert "Connection refused" in stats["error"]

    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_empty_api_response(
        self, mock_get: MagicMock, mock_db_cls: MagicMock, mock_scorer: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 0
        assert stats["jobs_stored"] == 0

    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_profile_scores_aggregated(
        self, mock_get: MagicMock, mock_db_cls: MagicMock, mock_scorer: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE[:2]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_db.add_job.side_effect = [100, 101]
        mock_db_cls.return_value = mock_db

        mock_multi = MagicMock()
        mock_multi.score_job_for_all.side_effect = [
            {"adam": (80, "B"), "wes": (90, "A")},
            {"adam": (60, "C")},
        ]
        mock_scorer.return_value = mock_multi

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert len(stats["profile_scores"]["adam"]) == 2
        assert len(stats["profile_scores"]["wes"]) == 1
        assert stats["profile_scores"]["wes"][0] == (90, "A")


class TestRetryDbOperation:
    """Tests for database retry logic"""

    def test_succeeds_first_try(self) -> None:
        result = RLSJobBoardScraper._retry_db_operation(lambda: 42)
        assert result == 42

    def test_retries_on_lock_error(self) -> None:
        call_count = 0

        def flaky_op() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("database is locked")
            return 99

        result = RLSJobBoardScraper._retry_db_operation(flaky_op)
        assert result == 99
        assert call_count == 3

    def test_raises_non_lock_errors(self) -> None:
        with pytest.raises(ValueError, match="bad data"):
            RLSJobBoardScraper._retry_db_operation(
                lambda: (_ for _ in ()).throw(ValueError("bad data"))
            )
