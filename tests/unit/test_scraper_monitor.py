"""Tests for scraper monitoring and alerting."""

from unittest.mock import MagicMock, patch

import pytest

from utils.scraper_monitor import ScraperMonitor


@pytest.fixture
def monitor():
    return ScraperMonitor()


class TestCheckSingleProfileStats:
    """Tests for check_single_profile_stats."""

    def test_healthy_stats_returns_true(self, monitor):
        stats = {
            "email": {"emails_processed": 10, "opportunities_found": 5, "jobs_stored": 3},
            "companies": {"companies_checked": 20, "jobs_scraped": 8, "jobs_stored": 4},
            "ministry": {"pages_scraped": 3, "jobs_found": 5, "jobs_stored": 2},
            "testdevjobs": {"jobs_found": 3, "jobs_stored": 1},
            "total_jobs_found": 16,
            "total_jobs_stored": 9,
        }
        assert monitor.check_single_profile_stats(stats) is True
        assert len(monitor.failures) == 0

    def test_email_error_detected(self, monitor):
        stats = {
            "email": {"error": "IMAP connection failed"},
            "companies": {},
            "ministry": {},
            "testdevjobs": {},
        }
        assert monitor.check_single_profile_stats(stats) is False
        assert len(monitor.failures) == 1
        assert "IMAP connection failed" in monitor.failures[0]

    def test_company_error_detected(self, monitor):
        stats = {
            "email": {"emails_processed": 5},
            "companies": {"error": "Firecrawl API timeout"},
            "ministry": {},
            "testdevjobs": {},
        }
        assert monitor.check_single_profile_stats(stats) is False
        assert "Firecrawl API timeout" in monitor.failures[0]

    def test_zero_emails_is_warning(self, monitor):
        stats = {
            "email": {"emails_processed": 0},
            "companies": {"companies_checked": 10},
            "ministry": {},
            "testdevjobs": {},
        }
        assert monitor.check_single_profile_stats(stats) is True
        assert len(monitor.warnings) == 1
        assert "0 emails" in monitor.warnings[0]

    def test_ministry_error_detected(self, monitor):
        stats = {
            "email": {},
            "companies": {},
            "ministry": {"error": "HTTP 503"},
            "testdevjobs": {},
        }
        assert monitor.check_single_profile_stats(stats) is False
        assert "Ministry of Testing" in monitor.failures[0]

    def test_testdevjobs_error_detected(self, monitor):
        stats = {
            "email": {},
            "companies": {},
            "ministry": {},
            "testdevjobs": {"error": "Connection refused"},
        }
        assert monitor.check_single_profile_stats(stats) is False
        assert "TestDevJobs" in monitor.failures[0]

    def test_empty_stats_is_healthy(self, monitor):
        stats = {"email": {}, "companies": {}, "ministry": {}, "testdevjobs": {}}
        assert monitor.check_single_profile_stats(stats) is True

    def test_zero_companies_is_warning(self, monitor):
        stats = {
            "email": {},
            "companies": {"companies_checked": 0},
            "ministry": {},
            "testdevjobs": {},
        }
        assert monitor.check_single_profile_stats(stats) is True
        assert len(monitor.warnings) == 1
        assert "0 companies" in monitor.warnings[0]


class TestCheckAllInboxesStats:
    """Tests for check_all_inboxes_stats."""

    def test_healthy_multi_inbox(self, monitor):
        stats = {
            "profiles": {
                "wes": {"name": "Wes", "status": "success", "email_stats": {"emails_processed": 5}},
                "adam": {
                    "name": "Adam",
                    "status": "success",
                    "email_stats": {"emails_processed": 8},
                },
            },
            "companies": {"companies_checked": 20, "jobs_scraped": 5},
            "ministry": {"pages_scraped": 3},
            "testdevjobs": {"jobs_found": 2},
            "errors": [],
        }
        assert monitor.check_all_inboxes_stats(stats) is True
        assert len(monitor.failures) == 0

    def test_partial_inbox_failure(self, monitor):
        stats = {
            "profiles": {
                "wes": {"name": "Wes", "status": "success", "email_stats": {"emails_processed": 5}},
                "adam": {"name": "Adam", "status": "error", "error": "Auth failed"},
            },
            "companies": {},
            "ministry": {},
            "testdevjobs": {},
            "errors": [],
        }
        assert monitor.check_all_inboxes_stats(stats) is False
        assert len(monitor.failures) == 1
        assert "Adam" in monitor.failures[0]

    def test_all_inboxes_failed(self, monitor):
        stats = {
            "profiles": {
                "wes": {"name": "Wes", "status": "error", "error": "IMAP down"},
                "adam": {"name": "Adam", "status": "error", "error": "Auth failed"},
            },
            "companies": {},
            "ministry": {},
            "testdevjobs": {},
            "errors": [],
        }
        assert monitor.check_all_inboxes_stats(stats) is False
        assert len(monitor.failures) == 2

    def test_top_level_errors_detected(self, monitor):
        stats = {
            "profiles": {},
            "companies": {},
            "ministry": {},
            "testdevjobs": {},
            "errors": ["No profiles with email credentials"],
        }
        assert monitor.check_all_inboxes_stats(stats) is False
        assert "No profiles with email credentials" in monitor.failures[0]


class TestSendAlert:
    """Tests for send_alert."""

    @patch("utils.scraper_monitor.smtplib.SMTP_SSL")
    @patch.dict(
        "os.environ",
        {"ADAMWHITE_GMAIL_USERNAME": "test@gmail.com", "ADAMWHITE_GMAIL_APP_PASSWORD": "secret"},
    )
    def test_send_alert_success(self, mock_smtp, monitor):
        monitor.failures.append("Email processing error: IMAP down")
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = monitor.send_alert("Test Alert")

        assert result is True
        mock_server.login.assert_called_once_with("test@gmail.com", "secret")
        mock_server.send_message.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_send_alert_no_credentials(self, monitor):
        # Ensure the specific env vars are not set
        import os

        os.environ.pop("ADAMWHITE_GMAIL_USERNAME", None)
        os.environ.pop("ADAMWHITE_GMAIL_APP_PASSWORD", None)

        monitor.failures.append("Some failure")
        result = monitor.send_alert("Test Alert")
        assert result is False

    @patch("utils.scraper_monitor.smtplib.SMTP_SSL")
    @patch.dict(
        "os.environ",
        {"ADAMWHITE_GMAIL_USERNAME": "test@gmail.com", "ADAMWHITE_GMAIL_APP_PASSWORD": "secret"},
    )
    def test_alert_email_content(self, mock_smtp, monitor):
        monitor.failures.append("Email processing error: IMAP connection refused")
        monitor.warnings.append("Company scraping checked 0 companies")

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        monitor.send_alert("Weekly Scraper FAILED")

        # Extract the HTML body from the sent message
        sent_msg = mock_server.send_message.call_args[0][0]
        payload = sent_msg.get_payload()
        html_body = payload[0].get_payload()

        assert "IMAP connection refused" in html_body
        assert "0 companies" in html_body
        assert "Failures" in html_body
        assert "Warnings" in html_body

    @patch("utils.scraper_monitor.smtplib.SMTP_SSL")
    @patch.dict(
        "os.environ",
        {"ADAMWHITE_GMAIL_USERNAME": "test@gmail.com", "ADAMWHITE_GMAIL_APP_PASSWORD": "secret"},
    )
    def test_send_alert_smtp_failure(self, mock_smtp, monitor):
        monitor.failures.append("Some failure")
        mock_smtp.return_value.__enter__ = MagicMock(side_effect=Exception("SMTP connection error"))
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = monitor.send_alert("Test Alert")
        assert result is False


class TestGetExitCode:
    """Tests for get_exit_code."""

    def test_exit_code_0_when_healthy(self, monitor):
        assert monitor.get_exit_code() == 0

    def test_exit_code_1_when_failures(self, monitor):
        monitor.failures.append("Something failed")
        assert monitor.get_exit_code() == 1

    def test_exit_code_0_with_only_warnings(self, monitor):
        monitor.warnings.append("Something warned")
        assert monitor.get_exit_code() == 0


class TestBuildAlertHtml:
    """Tests for _build_alert_html."""

    def test_html_contains_failures(self, monitor):
        monitor.failures.append("Test failure message")
        html = monitor._build_alert_html()
        assert "Test failure message" in html
        assert "Failures" in html

    def test_html_contains_warnings(self, monitor):
        monitor.warnings.append("Test warning message")
        html = monitor._build_alert_html()
        assert "Test warning message" in html
        assert "Warnings" in html

    def test_html_empty_when_no_issues(self, monitor):
        html = monitor._build_alert_html()
        assert "Failures" not in html
        assert "Warnings" not in html
        assert "Weekly Scraper Alert" in html
