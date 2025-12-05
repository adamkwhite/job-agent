"""
Unit tests for JobValidator

Tests URL validation logic for job posting URLs.
Target: 80%+ code coverage
"""

from unittest.mock import Mock, patch

import pytest
import requests

from src.utils.job_validator import JobValidator


class TestJobValidator:
    """Test suite for JobValidator class"""

    @pytest.fixture
    def validator(self):
        """Create a validator instance for tests"""
        return JobValidator(timeout=5)

    # Basic Validation Tests
    def test_empty_url(self, validator):
        """Test empty URL returns invalid"""
        is_valid, reason = validator.validate_url("")
        assert is_valid is False
        assert reason == "empty_url"

    def test_none_url(self, validator):
        """Test None URL returns invalid"""
        is_valid, reason = validator.validate_url(None)
        assert is_valid is False
        assert reason == "empty_url"

    # 404 Detection Tests
    @patch("requests.Session.head")
    def test_404_detection(self, mock_head, validator):
        """Test 404 URLs are detected as invalid"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://jobs.lever.co/company/fake-job")
        assert is_valid is False
        assert reason == "404_not_found"

    # LinkedIn Detection Tests
    @patch("requests.Session.head")
    def test_linkedin_redirect_to_login(self, mock_head, validator):
        """Test LinkedIn redirect to login is flagged as unverifiable but valid"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://www.linkedin.com/login?fromSignIn=true"
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://www.linkedin.com/jobs/view/12345")
        assert is_valid is True  # LinkedIn jobs assumed valid (can't verify)
        assert reason == "linkedin_unverifiable"

    @patch("requests.Session.head")
    def test_linkedin_authwall(self, mock_head, validator):
        """Test LinkedIn authwall redirect"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://www.linkedin.com/authwall?trk=..."
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://www.linkedin.com/jobs/view/12345")
        assert is_valid is True
        assert reason == "linkedin_unverifiable"

    # Generic Career Page Detection Tests
    def test_ashby_generic_url(self, validator):
        """Test Ashby generic career page URL is invalid"""
        # This URL has no job ID, just the company page
        url = "https://jobs.ashbyhq.com/graymatter-robotics"
        # Mock the HTTP request to return 200
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is False
            assert reason == "generic_career_page"

    def test_ashby_specific_job_url(self, validator):
        """Test Ashby specific job URL is valid"""
        url = "https://jobs.ashbyhq.com/graymatter-robotics/8f5e099e-4f3f-4d3b-9e27-ed843428b048"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is True
            assert reason == "valid"

    def test_lever_generic_url(self, validator):
        """Test Lever generic career page URL is invalid"""
        url = "https://jobs.lever.co/company"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is False
            assert reason == "generic_career_page"

    def test_lever_specific_job_url(self, validator):
        """Test Lever specific job URL is valid"""
        url = "https://jobs.lever.co/NimbleAI/32fed95d-6209-4215-a120-a6ebcb396467"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is True
            assert reason == "valid"

    def test_greenhouse_generic_url(self, validator):
        """Test Greenhouse generic career page URL is invalid"""
        url = "https://job-boards.greenhouse.io/company"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is False
            assert reason == "generic_career_page"

    def test_greenhouse_specific_job_url(self, validator):
        """Test Greenhouse specific job URL is valid"""
        url = "https://job-boards.greenhouse.io/figureai/jobs/4123456"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_url(url)
            assert is_valid is True
            assert reason == "valid"

    # HTTP Status Code Tests
    @patch("requests.Session.head")
    def test_valid_200_response(self, mock_head, validator):
        """Test valid URL with 200 response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is True
        assert reason == "valid"

    @patch("requests.Session.head")
    def test_redirect_same_domain(self, mock_head, validator):
        """Test redirect within same domain is valid"""
        mock_response = Mock()
        mock_response.status_code = 301
        mock_response.url = "https://example.com/careers/new-url"
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://example.com/careers/old-url")
        assert is_valid is True
        assert reason == "valid"

    @patch("requests.Session.head")
    def test_redirect_different_domain(self, mock_head, validator):
        """Test redirect to different domain is invalid"""
        mock_response = Mock()
        mock_response.status_code = 301
        mock_response.url = "https://different-domain.com/jobs/12345"
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "invalid_redirect"

    @patch("requests.Session.head")
    def test_unexpected_status_code(self, mock_head, validator):
        """Test unexpected HTTP status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_response

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "invalid_response"

    # Error Handling Tests
    @patch("requests.Session.head")
    def test_timeout_error(self, mock_head, validator):
        """Test timeout error handling"""
        mock_head.side_effect = requests.Timeout()

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "timeout"

    @patch("requests.Session.head")
    def test_connection_error(self, mock_head, validator):
        """Test connection error handling"""
        mock_head.side_effect = requests.ConnectionError()

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "connection_error"

    @patch("requests.Session.head")
    def test_generic_exception(self, mock_head, validator):
        """Test generic exception handling"""
        mock_head.side_effect = Exception("Unexpected error")

        is_valid, reason = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "validation_error"

    # Batch Validation Tests
    @patch("requests.Session.head")
    def test_validate_batch(self, mock_head, validator):
        """Test batch URL validation"""

        # Mock different responses for different URLs
        def mock_head_side_effect(url, **_kwargs):
            mock_response = Mock()
            if "404" in url:
                mock_response.status_code = 404
            else:
                mock_response.status_code = 200
                mock_response.url = url
            return mock_response

        mock_head.side_effect = mock_head_side_effect

        urls = [
            "https://example.com/jobs/valid",
            "https://example.com/jobs/404",
        ]

        results = validator.validate_batch(urls)

        assert len(results) == 2
        assert results["https://example.com/jobs/valid"] == (True, "valid")
        assert results["https://example.com/jobs/404"] == (False, "404_not_found")

    # Filter Valid Jobs Tests
    @patch("requests.Session.head")
    def test_filter_valid_jobs(self, mock_head, validator):
        """Test filtering jobs by URL validity"""

        def mock_head_side_effect(url, **_kwargs):
            mock_response = Mock()
            if "invalid" in url:
                mock_response.status_code = 404
            else:
                mock_response.status_code = 200
                mock_response.url = url
            return mock_response

        mock_head.side_effect = mock_head_side_effect

        jobs = [
            {"company": "Company A", "title": "Job 1", "link": "https://example.com/jobs/valid1"},
            {"company": "Company B", "title": "Job 2", "link": "https://example.com/jobs/invalid"},
            {"company": "Company C", "title": "Job 3", "link": "https://example.com/jobs/valid2"},
        ]

        valid_jobs, invalid_jobs = validator.filter_valid_jobs(jobs)

        assert len(valid_jobs) == 2
        assert len(invalid_jobs) == 1
        assert invalid_jobs[0]["company"] == "Company B"
        assert invalid_jobs[0]["validation_reason"] == "404_not_found"
