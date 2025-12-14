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
        is_valid, reason, needs_review = validator.validate_url("")
        assert is_valid is False
        assert reason == "empty_url"
        assert needs_review is False

    def test_none_url(self, validator):
        """Test None URL returns invalid"""
        is_valid, reason, needs_review = validator.validate_url(None)
        assert is_valid is False
        assert reason == "empty_url"
        assert needs_review is False

    # 404 Detection Tests
    @patch("requests.Session.head")
    def test_404_detection(self, mock_head, validator):
        """Test 404 URLs are detected as invalid"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://jobs.lever.co/company/fake-job"
        )
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

        is_valid, reason, needs_review = validator.validate_url(
            "https://www.linkedin.com/jobs/view/12345"
        )
        assert is_valid is True  # LinkedIn jobs assumed valid (can't verify)
        assert reason == "linkedin_unverifiable"

    @patch("requests.Session.head")
    def test_linkedin_authwall(self, mock_head, validator):
        """Test LinkedIn authwall redirect"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://www.linkedin.com/authwall?trk=..."
        mock_head.return_value = mock_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://www.linkedin.com/jobs/view/12345"
        )
        assert is_valid is True
        assert reason == "linkedin_unverifiable"

    # Generic Career Page Detection Tests
    def test_ashby_generic_url(self, validator):
        """Test Ashby generic career page URL is flagged for review"""
        # This URL has no job ID, just the company page
        url = "https://jobs.ashbyhq.com/graymatter-robotics"
        # Mock the HTTP request to return 200
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
            assert is_valid is True  # Valid but needs review
            assert reason == "generic_career_page"

    def test_ashby_specific_job_url(self, validator):
        """Test Ashby specific job URL is valid"""
        url = "https://jobs.ashbyhq.com/graymatter-robotics/8f5e099e-4f3f-4d3b-9e27-ed843428b048"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
            assert is_valid is True
            assert reason == "valid"

    def test_lever_generic_url(self, validator):
        """Test Lever generic career page URL is flagged for review"""
        url = "https://jobs.lever.co/company"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
            assert is_valid is True  # Valid but needs review
            assert reason == "generic_career_page"

    def test_lever_specific_job_url(self, validator):
        """Test Lever specific job URL is valid"""
        url = "https://jobs.lever.co/NimbleAI/32fed95d-6209-4215-a120-a6ebcb396467"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
            assert is_valid is True
            assert reason == "valid"

    def test_greenhouse_generic_url(self, validator):
        """Test Greenhouse generic career page URL is flagged for review"""
        url = "https://job-boards.greenhouse.io/company"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
            assert is_valid is True  # Valid but needs review
            assert reason == "generic_career_page"

    def test_greenhouse_specific_job_url(self, validator):
        """Test Greenhouse specific job URL is valid"""
        url = "https://job-boards.greenhouse.io/figureai/jobs/4123456"
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = url
            mock_head.return_value = mock_response

            is_valid, reason, needs_review = validator.validate_url(url)
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

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is True
        assert reason == "valid"

    @patch("requests.Session.head")
    def test_redirect_same_domain(self, mock_head, validator):
        """Test redirect within same domain is valid"""
        mock_response = Mock()
        mock_response.status_code = 301
        mock_response.url = "https://example.com/careers/new-url"
        mock_head.return_value = mock_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://example.com/careers/old-url"
        )
        assert is_valid is True
        assert reason == "valid"

    @patch("requests.Session.head")
    def test_redirect_different_domain(self, mock_head, validator):
        """Test redirect to different domain is invalid"""
        mock_response = Mock()
        mock_response.status_code = 301
        mock_response.url = "https://different-domain.com/jobs/12345"
        mock_head.return_value = mock_response

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "invalid_redirect"

    @patch("requests.Session.head")
    def test_unexpected_status_code(self, mock_head, validator):
        """Test unexpected HTTP status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_response

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "invalid_response"

    # Error Handling Tests
    @patch("requests.Session.head")
    def test_timeout_error(self, mock_head, validator):
        """Test timeout error handling"""
        mock_head.side_effect = requests.Timeout()

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "timeout"

    @patch("requests.Session.head")
    def test_connection_error(self, mock_head, validator):
        """Test connection error handling"""
        mock_head.side_effect = requests.ConnectionError()

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert reason == "connection_error"

    @patch("requests.Session.head")
    def test_generic_exception(self, mock_head, validator):
        """Test generic exception handling"""
        mock_head.side_effect = Exception("Unexpected error")

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
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
        assert results["https://example.com/jobs/valid"] == (True, "valid", False)
        assert results["https://example.com/jobs/404"] == (False, "404_not_found", False)

    # Filter Valid Jobs Tests
    @patch("requests.Session.head")
    def test_filter_valid_jobs(self, mock_head, validator):
        """Test filtering jobs by URL validity"""

        def mock_head_side_effect(url, **_kwargs):
            mock_response = Mock()
            if "invalid" in url:
                mock_response.status_code = 404
            elif "generic" in url:
                # Simulate a generic career page URL
                mock_response.status_code = 200
                mock_response.url = url
            else:
                mock_response.status_code = 200
                mock_response.url = url
            return mock_response

        mock_head.side_effect = mock_head_side_effect

        jobs = [
            {"company": "Company A", "title": "Job 1", "link": "https://example.com/jobs/valid1"},
            {"company": "Company B", "title": "Job 2", "link": "https://example.com/jobs/invalid"},
            {"company": "Company C", "title": "Job 3", "link": "https://example.com/jobs/valid2"},
            {
                "company": "Company D",
                "title": "Job 4",
                "link": "https://jobs.ashbyhq.com/generic",
            },  # Generic URL
        ]

        valid_jobs, flagged_jobs, invalid_jobs = validator.filter_valid_jobs(jobs)

        assert len(valid_jobs) == 2
        assert len(flagged_jobs) == 1
        assert len(invalid_jobs) == 1
        assert invalid_jobs[0]["company"] == "Company B"
        assert invalid_jobs[0]["validation_reason"] == "404_not_found"
        assert flagged_jobs[0]["company"] == "Company D"
        assert flagged_jobs[0]["validation_reason"] == "generic_career_page"

    # Rate Limiting (429) Retry Tests
    @patch("requests.Session.head")
    @patch("time.sleep")
    def test_429_retry_eventually_succeeds(self, mock_sleep, mock_head, validator):
        """Test 429 rate limit with successful retry"""
        # First call returns 429, second call returns 200
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.url = "https://linkedin.com/jobs/12345"

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.url = "https://linkedin.com/jobs/12345"

        mock_head.side_effect = [mock_response_429, mock_response_200]

        is_valid, reason, needs_review = validator.validate_url("https://linkedin.com/jobs/12345")

        # Should retry and succeed
        assert is_valid is True
        assert reason == "valid"
        assert needs_review is False
        assert mock_head.call_count == 2
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(2.0)  # First retry delay: 2^0 * 2.0 = 2.0s

    @patch("requests.Session.head")
    @patch("time.sleep")
    def test_429_retry_exhausts_attempts(self, mock_sleep, mock_head):
        """Test 429 rate limit exhausts all retry attempts"""
        validator = JobValidator(timeout=5, max_retries=3, base_backoff=2.0)

        # All attempts return 429
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.url = "https://linkedin.com/jobs/12345"
        mock_head.return_value = mock_response_429

        is_valid, reason, needs_review = validator.validate_url("https://linkedin.com/jobs/12345")

        # Should exhaust retries and flag for review
        assert is_valid is True
        assert reason == "rate_limited_assumed_valid"
        assert needs_review is True
        assert mock_head.call_count == 4  # Initial + 3 retries
        assert mock_sleep.call_count == 3  # Sleep before each retry

        # Verify exponential backoff: 2s, 4s, 8s
        expected_delays = [2.0, 4.0, 8.0]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @patch("requests.Session.head")
    @patch("time.sleep")
    def test_429_retry_with_custom_backoff(self, mock_sleep, mock_head):
        """Test 429 retry with custom backoff settings"""
        validator = JobValidator(timeout=5, max_retries=2, base_backoff=1.0)

        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.url = "https://linkedin.com/jobs/12345"
        mock_head.return_value = mock_response_429

        is_valid, reason, needs_review = validator.validate_url("https://linkedin.com/jobs/12345")

        # Should exhaust retries with custom backoff
        assert is_valid is True
        assert reason == "rate_limited_assumed_valid"
        assert needs_review is True
        assert mock_head.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2

        # Verify custom backoff: 1s, 2s
        expected_delays = [1.0, 2.0]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @patch("requests.Session.head")
    @patch("time.sleep")
    def test_429_then_404(self, mock_sleep, mock_head, validator):
        """Test 429 followed by 404 on retry"""
        # First call returns 429, second call returns 404
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.url = "https://linkedin.com/jobs/12345"

        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        mock_response_404.url = "https://linkedin.com/jobs/12345"

        mock_head.side_effect = [mock_response_429, mock_response_404]

        is_valid, reason, needs_review = validator.validate_url("https://linkedin.com/jobs/12345")

        # Should detect 404 after retry
        assert is_valid is False
        assert reason == "404_not_found"
        assert needs_review is False
        assert mock_head.call_count == 2
        assert mock_sleep.call_count == 1

    # Staleness Detection Tests
    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_stale_job_no_longer_accepting(self, mock_head, mock_get, validator):
        """Test job marked as stale when page shows 'no longer accepting applications'"""
        # HEAD request succeeds (200)
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_head_response

        # GET request returns page with staleness indicator
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <h1>Senior Engineer</h1>
                <p>We are no longer accepting applications for this position.</p>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert "stale_no_longer_accepting" in reason
        assert needs_review is False

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_stale_job_position_filled(self, mock_head, mock_get, validator):
        """Test job marked as stale when page shows 'position has been filled'"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <div>This position has been filled. Thank you for your interest.</div>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is False
        assert "stale_position_has_been_filled" in reason

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_not_stale_job_active(self, mock_head, mock_get, validator):
        """Test active job not marked as stale"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <h1>Senior Engineer</h1>
                <p>We're excited to review your application!</p>
                <button>Apply Now</button>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is True
        assert reason == "valid"

    @patch("requests.Session.head")
    def test_staleness_check_disabled(self, mock_head):
        """Test that staleness check can be disabled"""
        # Create validator with check_content=False
        validator_no_content = JobValidator(timeout=5, check_content=False)

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_head_response

        # Should not call GET request, return valid immediately
        is_valid, reason, needs_review = validator_no_content.validate_url(
            "https://example.com/jobs/12345"
        )
        assert is_valid is True
        assert reason == "valid"
        # Verify GET was not called
        assert mock_head.call_count == 1

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_staleness_check_get_error(self, mock_head, mock_get, validator):
        """Test that GET errors don't prevent validation"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://example.com/jobs/12345"
        mock_head.return_value = mock_head_response

        # GET request fails
        mock_get.side_effect = requests.Timeout()

        # Should still mark as valid (assumes not stale if can't verify)
        is_valid, reason, needs_review = validator.validate_url("https://example.com/jobs/12345")
        assert is_valid is True
        assert reason == "valid"

    # LinkedIn-Specific Staleness Detection Tests (Issue #115)
    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_linkedin_stale_in_alert_banner(self, mock_head, mock_get, validator):
        """Test LinkedIn job correctly identified as stale from alert banner"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://linkedin.com/jobs/view/12345"
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <div class="alert-banner">
                    <p>This job is no longer accepting applications</p>
                </div>
                <main>
                    <h1>Senior Product Manager</h1>
                    <button class="apply-button">Easy Apply</button>
                </main>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://linkedin.com/jobs/view/12345"
        )
        assert is_valid is False
        assert "stale" in reason
        assert needs_review is False

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_linkedin_false_positive_in_recommendations(self, mock_head, mock_get, validator):
        """Test LinkedIn job NOT marked stale when phrase only in recommendations section"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://linkedin.com/jobs/view/12345"
        mock_head.return_value = mock_head_response

        # Job is ACTIVE, but "no longer accepting" appears in unrelated section
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <main role="main">
                    <h1>Product Manager at Lemurian Labs</h1>
                    <button class="apply-button">Easy Apply</button>
                    <p>Join our team building next-gen robotics!</p>
                </main>
                <aside class="recommendations">
                    <h2>Similar Jobs</h2>
                    <div class="job-card">
                        <p>Product Manager at OtherCo</p>
                        <small>No longer accepting applications</small>
                    </div>
                </aside>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        # Should be valid - staleness indicator only in recommendations, not main job
        is_valid, reason, needs_review = validator.validate_url(
            "https://linkedin.com/jobs/view/12345"
        )
        assert is_valid is True
        assert reason == "valid"
        assert needs_review is False

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_linkedin_stale_in_main_content(self, mock_head, mock_get, validator):
        """Test LinkedIn job correctly identified as stale from main content area"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://linkedin.com/jobs/view/12345"
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <main role="main">
                    <h1>Engineering Manager</h1>
                    <p>Applications are closed for this position.</p>
                </main>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://linkedin.com/jobs/view/12345"
        )
        assert is_valid is False
        assert "stale" in reason

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_linkedin_stale_in_application_section(self, mock_head, mock_get, validator):
        """Test LinkedIn job correctly identified as stale from application section"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://linkedin.com/jobs/view/12345"
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <h1>Director of Engineering</h1>
                <div class="application-section">
                    <p>This position is no longer available.</p>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        is_valid, reason, needs_review = validator.validate_url(
            "https://linkedin.com/jobs/view/12345"
        )
        assert is_valid is False
        assert "stale" in reason

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_linkedin_active_job_with_unrelated_text(self, mock_head, mock_get, validator):
        """Test LinkedIn active job not flagged when staleness phrase in footer/unrelated areas"""
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = "https://linkedin.com/jobs/view/12345"
        mock_head.return_value = mock_head_response

        # Active job, but phrase appears in footer/help text
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <main role="main">
                    <h1>VP of Product</h1>
                    <div class="apply-section">
                        <button class="apply-button">Apply Now</button>
                    </div>
                </main>
                <footer>
                    <p>Help: What if a job is no longer accepting applications?</p>
                </footer>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        # Should be valid - phrase only in footer, not in high-signal areas
        is_valid, reason, needs_review = validator.validate_url(
            "https://linkedin.com/jobs/view/12345"
        )
        assert is_valid is True
        assert reason == "valid"


class TestJobValidatorDigestValidation:
    """Test suite for validate_for_digest() method (Issue #163)"""

    @pytest.fixture
    def validator(self):
        """Create validator with 60-day threshold"""
        return JobValidator(timeout=5, age_threshold_days=60, check_content=True)

    # Age Validation Tests

    def test_fresh_job_passes(self, validator):
        """Test that jobs <60 days old pass validation"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Test Corp",
            "link": "https://example.com/job",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_for_digest(job)

            assert is_valid is True
            assert reason is None

    def test_old_job_filtered_by_age(self, validator):
        """Test that jobs >60 days old are filtered"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Old Corp",
            "link": "https://example.com/job",
            "received_at": (datetime.now() - timedelta(days=70)).isoformat(),
        }

        is_valid, reason = validator.validate_for_digest(job)

        assert is_valid is False
        assert reason == "stale_job_age"

    def test_exactly_threshold_age(self, validator):
        """Test job exactly at threshold age"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Edge Case Corp",
            "link": "https://example.com/job",
            "received_at": (datetime.now() - timedelta(days=60)).isoformat(),
        }

        # Should pass - not >60 days
        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_for_digest(job)

            assert is_valid is True
            assert reason is None

    def test_missing_received_at_skips_age_check(self, validator):
        """Test jobs without received_at skip age validation"""
        job = {
            "title": "VP Engineering",
            "company": "No Date Corp",
            "link": "https://example.com/job",
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_for_digest(job)

            # Should still validate URL
            assert is_valid is True
            assert reason is None

    def test_invalid_date_format_continues_to_url_check(self, validator):
        """Test that invalid date formats don't crash, just skip age check"""
        job = {
            "title": "VP Engineering",
            "company": "Bad Date Corp",
            "link": "https://example.com/job",
            "received_at": "invalid-date-format",
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            is_valid, reason = validator.validate_for_digest(job)

            # Should continue to URL validation
            assert is_valid is True

    # Caching Tests

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_caching_prevents_duplicate_requests(self, mock_head, mock_get, validator):
        """Test that caching prevents duplicate URL fetches"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Cache Corp",
            "link": "https://linkedin.com/jobs/view/12345",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = job["link"]
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = "<html><body>Active job</body></html>"
        mock_get.return_value = mock_get_response

        # First call
        is_valid1, reason1 = validator.validate_for_digest(job, use_cache=True)
        assert is_valid1 is True

        # Second call should use cache (no additional HEAD/GET)
        call_count_before = mock_head.call_count + mock_get.call_count

        is_valid2, reason2 = validator.validate_for_digest(job, use_cache=True)
        assert is_valid2 is True
        assert reason2 is None

        call_count_after = mock_head.call_count + mock_get.call_count

        # No additional calls should have been made
        assert call_count_after == call_count_before

    def test_cache_disabled_makes_requests(self, validator):
        """Test that disabling cache makes fresh requests"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "No Cache Corp",
            "link": "https://example.com/job",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            # First call
            validator.validate_for_digest(job, use_cache=True)
            first_call_count = mock_head.call_count

            # Second call with cache disabled
            validator.validate_for_digest(job, use_cache=False)
            second_call_count = mock_head.call_count

            # Should make additional request
            assert second_call_count > first_call_count

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_stale_url_cached_and_returned(self, mock_head, mock_get, validator):
        """Test that stale URLs are cached correctly"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Stale Corp",
            "link": "https://linkedin.com/jobs/view/stale123",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.url = job["link"]
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.text = """
        <html>
            <body>
                <div class="alert">No longer accepting applications</div>
            </body>
        </html>
        """
        mock_get.return_value = mock_get_response

        # First call - should detect stale and cache
        is_valid1, reason1 = validator.validate_for_digest(job, use_cache=True)
        assert is_valid1 is False
        assert "stale" in reason1

        # Second call - should return cached stale result
        is_valid2, reason2 = validator.validate_for_digest(job, use_cache=True)
        assert is_valid2 is False
        assert reason2 == reason1

    def test_cache_clear(self, validator):
        """Test that clear_cache() empties the cache"""
        from datetime import datetime, timedelta

        job = {
            "title": "VP Engineering",
            "company": "Clear Corp",
            "link": "https://example.com/job",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = job["link"]
            mock_head.return_value = mock_response

            # Validate to populate cache
            validator.validate_for_digest(job, use_cache=True)

            stats_before = validator.get_cache_stats()
            assert stats_before["total_cached"] > 0

            # Clear cache
            validator.clear_cache()

            stats_after = validator.get_cache_stats()
            assert stats_after["total_cached"] == 0

    def test_cache_stats(self, validator):
        """Test cache statistics reporting"""
        from datetime import datetime, timedelta

        # Add valid job to cache
        valid_job = {
            "title": "VP Engineering",
            "company": "Valid Corp",
            "link": "https://example.com/valid",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        with patch("requests.Session.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = valid_job["link"]
            mock_head.return_value = mock_response

            validator.validate_for_digest(valid_job, use_cache=True)

            # Add invalid job to cache
            invalid_job = {
                "title": "Director Engineering",
                "company": "Invalid Corp",
                "link": "https://example.com/invalid",
                "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
            }

            mock_response.status_code = 404
            validator.validate_for_digest(invalid_job, use_cache=True)

            stats = validator.get_cache_stats()

            assert stats["total_cached"] == 2
            assert stats["valid_count"] == 1
            assert stats["invalid_count"] == 1

    # Integration Tests

    def test_regression_issue_163_miovision_example(self, validator):
        """Regression: Miovision stale job should be detected"""
        from datetime import datetime, timedelta

        job = {
            "title": "Director of Engineering",
            "company": "Miovision",
            "link": "https://www.linkedin.com/jobs/view/4336860052",
            "received_at": (datetime.now() - timedelta(days=30)).isoformat(),
        }

        with patch("requests.Session.get") as mock_get, patch("requests.Session.head") as mock_head:
            mock_head_response = Mock()
            mock_head_response.status_code = 200
            mock_head_response.url = job["link"]
            mock_head.return_value = mock_head_response

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.text = """
            <html>
                <body>
                    <div class="alert">No longer accepting applications</div>
                </body>
            </html>
            """
            mock_get.return_value = mock_get_response

            is_valid, reason = validator.validate_for_digest(job)

            assert is_valid is False
            assert "stale" in reason
