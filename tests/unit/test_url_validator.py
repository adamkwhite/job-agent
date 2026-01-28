"""
Tests for URL validation utilities
Ensures job URLs are validated correctly before storage
"""

from unittest.mock import MagicMock, patch

import requests

from src.utils.url_validator import validate_job_url


class TestValidateJobUrl:
    """Tests for validate_job_url function"""

    @patch("src.utils.url_validator.requests.head")
    def test_valid_url_returns_true(self, mock_head):
        """Valid URL (200 OK) should return (True, 'valid')"""
        mock_head.return_value = MagicMock(status_code=200)

        is_valid, reason = validate_job_url("https://example.com/careers")

        assert is_valid is True
        assert reason == "valid"
        mock_head.assert_called_once_with(
            "https://example.com/careers", timeout=5, allow_redirects=True
        )

    @patch("src.utils.url_validator.requests.head")
    def test_404_url_returns_false(self, mock_head):
        """404 Not Found should return (False, 'not_found')"""
        mock_head.return_value = MagicMock(status_code=404)

        is_valid, reason = validate_job_url("https://example.com/missing-page")

        assert is_valid is False
        assert reason == "not_found"

    @patch("src.utils.url_validator.requests.head")
    def test_timeout_handling(self, mock_head):
        """Request timeout should return (False, 'timeout')"""
        mock_head.side_effect = requests.Timeout("Request timed out")

        is_valid, reason = validate_job_url("https://slow-site.com/careers", timeout=5)

        assert is_valid is False
        assert reason == "timeout"

    @patch("src.utils.url_validator.requests.head")
    def test_server_error_retry_logic(self, mock_head):
        """Server error (500) should trigger retry, then succeed"""
        # First call returns 500, second call returns 200
        mock_head.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=200),
        ]

        is_valid, reason = validate_job_url("https://example.com/careers")

        assert is_valid is True
        assert reason == "valid_after_retry"
        assert mock_head.call_count == 2

    @patch("src.utils.url_validator.requests.head")
    def test_server_error_retry_fails(self, mock_head):
        """Server error that persists after retry should return False"""
        # Both calls return 500
        mock_head.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=503),
        ]

        is_valid, reason = validate_job_url("https://example.com/careers")

        assert is_valid is False
        assert reason == "server_error_503"
        assert mock_head.call_count == 2

    @patch("src.utils.url_validator.requests.head")
    def test_connection_error_handling(self, mock_head):
        """Connection error should return (False, 'connection_error')"""
        mock_head.side_effect = requests.ConnectionError("Failed to establish connection")

        is_valid, reason = validate_job_url("https://unreachable-site.com/careers")

        assert is_valid is False
        assert reason == "connection_error"

    @patch("src.utils.url_validator.requests.head")
    def test_other_http_status_codes(self, mock_head):
        """Non-200/404/500 status codes should return appropriate reason"""
        # Test 403 Forbidden
        mock_head.return_value = MagicMock(status_code=403)

        is_valid, reason = validate_job_url("https://example.com/restricted")

        assert is_valid is False
        assert reason == "http_403"

    @patch("src.utils.url_validator.requests.head")
    def test_custom_timeout(self, mock_head):
        """Should respect custom timeout parameter"""
        mock_head.return_value = MagicMock(status_code=200)

        validate_job_url("https://example.com/careers", timeout=10)

        mock_head.assert_called_once_with(
            "https://example.com/careers", timeout=10, allow_redirects=True
        )

    @patch("src.utils.url_validator.requests.head")
    def test_unexpected_exception_handling(self, mock_head):
        """Unexpected exceptions should be caught and logged"""
        mock_head.side_effect = ValueError("Unexpected error occurred")

        is_valid, reason = validate_job_url("https://example.com/careers")

        assert is_valid is False
        assert reason.startswith("error:")
        assert "Unexpected error" in reason

    @patch("src.utils.url_validator.requests.head")
    def test_redirects_followed(self, mock_head):
        """Redirects should be followed automatically"""
        # Simulate redirect (requests handles this automatically with allow_redirects=True)
        mock_head.return_value = MagicMock(status_code=200)

        is_valid, reason = validate_job_url("https://example.com/old-url")

        assert is_valid is True
        assert reason == "valid"
        # Verify allow_redirects=True is set
        _, kwargs = mock_head.call_args
        assert kwargs["allow_redirects"] is True
