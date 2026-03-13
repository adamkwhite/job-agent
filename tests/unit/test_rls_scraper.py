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

    def test_remote_only_no_location(self) -> None:
        """Remote status without a city shows just the status."""
        job = {"remote_status": "Remote", "location": ""}
        result = RLSJobBoardScraper._build_job_dict(job)
        assert result["location"] == "Remote"

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
    """Tests for the full scrape flow (store/score delegated to shared utils)"""

    @patch("jobs.rls_scraper.score_single_job")
    @patch("jobs.rls_scraper.store_single_job")
    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_successful_scrape(
        self,
        mock_get: MagicMock,
        mock_db_cls: MagicMock,
        mock_scorer: MagicMock,
        mock_store: MagicMock,
        mock_score: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_store.side_effect = [100, 101, 102]

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 3
        assert mock_store.call_count == 3
        assert mock_score.call_count == 3

    @patch("jobs.rls_scraper.score_single_job")
    @patch("jobs.rls_scraper.store_single_job")
    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_duplicates_skip_scoring(
        self,
        mock_get: MagicMock,
        mock_db_cls: MagicMock,
        mock_scorer: MagicMock,
        mock_store: MagicMock,
        mock_score: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE[:2]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_store.side_effect = [100, None]  # Second is duplicate

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 2
        assert mock_store.call_count == 2
        assert mock_score.call_count == 1  # Only scored non-duplicate

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

    @patch("jobs.rls_scraper.store_single_job")
    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_empty_api_response(
        self,
        mock_get: MagicMock,
        mock_db_cls: MagicMock,
        mock_scorer: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        scraper = RLSJobBoardScraper()
        stats = scraper.scrape_rls_jobs()

        assert stats["jobs_found"] == 0
        assert mock_store.call_count == 0

    @patch("jobs.rls_scraper.score_single_job")
    @patch("jobs.rls_scraper.store_single_job")
    @patch("jobs.rls_scraper.get_multi_scorer")
    @patch("jobs.rls_scraper.JobDatabase")
    @patch("jobs.rls_scraper.requests.get")
    def test_passes_correct_args_to_store_and_score(
        self,
        mock_get: MagicMock,
        mock_db_cls: MagicMock,
        mock_scorer: MagicMock,
        mock_store: MagicMock,
        mock_score: MagicMock,
    ) -> None:
        """Verify scraper passes database/scorer instances to shared functions."""
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE[:1]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_store.return_value = 42

        scraper = RLSJobBoardScraper()
        scraper.scrape_rls_jobs(min_score=60)

        # store_single_job receives the database instance
        store_call = mock_store.call_args
        assert store_call[0][0] is scraper.database

        # score_single_job receives the multi_scorer instance
        score_call = mock_score.call_args
        assert score_call[0][0] is scraper.multi_scorer
        assert score_call[0][3] == 42  # job_id
        assert score_call[0][5] == 60  # min_score


class TestPrintSummary:
    """Tests for print_summary output"""

    def test_basic_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        stats = {"jobs_found": 10, "jobs_stored": 8, "jobs_scored": 8, "profile_scores": {}}
        RLSJobBoardScraper.print_summary(stats)
        captured = capsys.readouterr()
        assert "Jobs found: 10" in captured.out
        assert "Jobs stored: 8" in captured.out

    def test_summary_with_profile_scores(self, capsys: pytest.CaptureFixture[str]) -> None:
        stats = {
            "jobs_found": 5,
            "jobs_stored": 5,
            "jobs_scored": 5,
            "profile_scores": {
                "adam": [(80, "B"), (90, "A"), (60, "C")],
                "wes": [(95, "A"), (88, "A")],
            },
        }
        RLSJobBoardScraper.print_summary(stats)
        captured = capsys.readouterr()
        assert "adam:" in captured.out
        assert "Total: 3 jobs" in captured.out
        assert "Avg score: 76.7" in captured.out
        assert "wes:" in captured.out
        assert "Total: 2 jobs" in captured.out

    def test_summary_with_empty_scores_list(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A profile with an empty scores list is skipped."""
        stats = {
            "jobs_found": 0,
            "jobs_stored": 0,
            "profile_scores": {"adam": []},
        }
        RLSJobBoardScraper.print_summary(stats)
        captured = capsys.readouterr()
        assert "adam:" not in captured.out

    def test_summary_no_profile_scores(self, capsys: pytest.CaptureFixture[str]) -> None:
        stats = {"jobs_found": 0, "jobs_stored": 0, "profile_scores": {}}
        RLSJobBoardScraper.print_summary(stats)
        captured = capsys.readouterr()
        assert "Scores by profile:" not in captured.out
