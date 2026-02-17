"""
Unit tests for weekly_unified_scraper.py --all-inboxes functionality
Tests aggregation functions, error handling, and CLI validation
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from jobs.weekly_unified_scraper import (
    _aggregate_email_stats,
    _calculate_grand_totals,
    run_all_inboxes,
)


class TestAggregateEmailStats:
    """Test email stats aggregation across multiple profiles"""

    def test_aggregate_all_successful_profiles(self):
        """Should sum stats from all successful profiles"""
        profile_results = {
            "wes": {
                "name": "Wesley van Ooyen",
                "status": "success",
                "email_stats": {
                    "emails_processed": 10,
                    "opportunities_found": 8,
                    "jobs_stored": 5,
                    "notifications_sent": 2,
                },
            },
            "adam": {
                "name": "Adam White",
                "status": "success",
                "email_stats": {
                    "emails_processed": 15,
                    "opportunities_found": 12,
                    "jobs_stored": 7,
                    "notifications_sent": 3,
                },
            },
        }

        totals = _aggregate_email_stats(profile_results)

        assert totals["total_emails_processed"] == 25
        assert totals["total_jobs_found"] == 20
        assert totals["total_jobs_stored"] == 12
        assert totals["total_notifications"] == 5
        assert totals["successful_profiles"] == 2
        assert totals["failed_profiles"] == 0

    def test_aggregate_with_failed_profiles(self):
        """Should skip failed profiles and count them separately"""
        profile_results = {
            "wes": {
                "name": "Wesley van Ooyen",
                "status": "success",
                "email_stats": {
                    "emails_processed": 10,
                    "opportunities_found": 8,
                    "jobs_stored": 5,
                    "notifications_sent": 2,
                },
            },
            "adam": {
                "name": "Adam White",
                "status": "error",
                "error": "IMAP connection failed",
            },
        }

        totals = _aggregate_email_stats(profile_results)

        assert totals["total_emails_processed"] == 10
        assert totals["total_jobs_found"] == 8
        assert totals["total_jobs_stored"] == 5
        assert totals["total_notifications"] == 2
        assert totals["successful_profiles"] == 1
        assert totals["failed_profiles"] == 1

    def test_aggregate_all_failed_profiles(self):
        """Should return zeros when all profiles fail"""
        profile_results = {
            "wes": {
                "name": "Wesley van Ooyen",
                "status": "error",
                "error": "IMAP connection failed",
            },
            "adam": {
                "name": "Adam White",
                "status": "error",
                "error": "Authentication failed",
            },
        }

        totals = _aggregate_email_stats(profile_results)

        assert totals["total_emails_processed"] == 0
        assert totals["total_jobs_found"] == 0
        assert totals["total_jobs_stored"] == 0
        assert totals["total_notifications"] == 0
        assert totals["successful_profiles"] == 0
        assert totals["failed_profiles"] == 2

    def test_aggregate_empty_results(self):
        """Should handle empty results dict"""
        profile_results = {}

        totals = _aggregate_email_stats(profile_results)

        assert totals["total_emails_processed"] == 0
        assert totals["total_jobs_found"] == 0
        assert totals["total_jobs_stored"] == 0
        assert totals["total_notifications"] == 0
        assert totals["successful_profiles"] == 0
        assert totals["failed_profiles"] == 0

    def test_aggregate_missing_stats_keys(self):
        """Should handle missing keys in email_stats gracefully"""
        profile_results = {
            "wes": {
                "name": "Wesley van Ooyen",
                "status": "success",
                "email_stats": {
                    "emails_processed": 10,
                    # Missing other keys
                },
            },
        }

        totals = _aggregate_email_stats(profile_results)

        assert totals["total_emails_processed"] == 10
        assert totals["total_jobs_found"] == 0  # Default to 0
        assert totals["total_jobs_stored"] == 0  # Default to 0
        assert totals["total_notifications"] == 0  # Default to 0
        assert totals["successful_profiles"] == 1


class TestCalculateGrandTotals:
    """Test grand totals calculation across all sources"""

    def test_calculate_with_all_sources(self):
        """Should sum totals from emails, companies, and ministry"""
        aggregated_stats = {
            "email_totals": {
                "total_jobs_found": 20,
                "total_jobs_stored": 12,
                "total_notifications": 5,
            },
            "companies": {
                "jobs_scraped": 30,
                "jobs_stored": 15,
                "notifications_sent": 8,
            },
            "ministry": {
                "jobs_found": 10,
                "jobs_stored": 6,
            },
        }

        grand_totals = _calculate_grand_totals(aggregated_stats)

        assert grand_totals["total_jobs_found"] == 60  # 20 + 30 + 10
        assert grand_totals["total_jobs_stored"] == 33  # 12 + 15 + 6
        assert grand_totals["total_notifications"] == 13  # 5 + 8 (ministry doesn't send)

    def test_calculate_with_missing_sections(self):
        """Should handle missing sections gracefully"""
        aggregated_stats = {
            "email_totals": {
                "total_jobs_found": 20,
                "total_jobs_stored": 12,
                "total_notifications": 5,
            },
            # Missing companies and ministry
        }

        grand_totals = _calculate_grand_totals(aggregated_stats)

        assert grand_totals["total_jobs_found"] == 20
        assert grand_totals["total_jobs_stored"] == 12
        assert grand_totals["total_notifications"] == 5

    def test_calculate_with_missing_keys(self):
        """Should default to 0 for missing keys"""
        aggregated_stats = {
            "email_totals": {
                "total_jobs_found": 20,
                # Missing total_jobs_stored
            },
            "companies": {
                # Missing all keys
            },
            "ministry": {
                "jobs_found": 10,
            },
        }

        grand_totals = _calculate_grand_totals(aggregated_stats)

        assert grand_totals["total_jobs_found"] == 30  # 20 + 0 + 10
        assert grand_totals["total_jobs_stored"] == 0
        assert grand_totals["total_notifications"] == 0

    def test_calculate_with_empty_stats(self):
        """Should return zeros for empty stats"""
        aggregated_stats = {}

        grand_totals = _calculate_grand_totals(aggregated_stats)

        assert grand_totals["total_jobs_found"] == 0
        assert grand_totals["total_jobs_stored"] == 0
        assert grand_totals["total_notifications"] == 0

    def test_calculate_with_error_dicts(self):
        """Should handle error dicts that contain 'error' key"""
        aggregated_stats = {
            "email_totals": {
                "total_jobs_found": 20,
                "total_jobs_stored": 12,
                "total_notifications": 5,
            },
            "companies": {
                "error": "Firecrawl API failed",
                "jobs_scraped": 0,
                "jobs_stored": 0,
            },
            "ministry": {
                "error": "Page scraping failed",
                "jobs_found": 0,
                "jobs_stored": 0,
            },
        }

        grand_totals = _calculate_grand_totals(aggregated_stats)

        assert grand_totals["total_jobs_found"] == 20  # Only emails succeeded
        assert grand_totals["total_jobs_stored"] == 12
        assert grand_totals["total_notifications"] == 5


class TestRunAllInboxes:
    """Test run_all_inboxes orchestration function"""

    @patch("utils.profile_manager.get_profile_manager")
    def test_no_profiles_with_email_credentials(self, mock_get_manager):
        """Should return error dict when no profiles have email credentials"""
        # Mock profile manager to return profiles without email creds
        mock_manager = Mock()
        mock_profile = Mock()
        mock_profile.email_username = None
        mock_profile.email_app_password = None
        mock_manager.get_enabled_profiles.return_value = [mock_profile]
        mock_get_manager.return_value = mock_manager

        result = run_all_inboxes(run_emails=True, run_companies=False)

        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "No profiles with email credentials" in result["errors"]
        assert result["profiles"] == {}

    @patch("jobs.weekly_unified_scraper._scrape_shared_ministry")
    @patch("jobs.weekly_unified_scraper._scrape_shared_companies")
    @patch("jobs.weekly_unified_scraper._process_all_inboxes")
    @patch("utils.profile_manager.get_profile_manager")
    def test_skip_emails_when_run_emails_false(
        self,
        mock_get_manager,
        mock_process_inboxes,
        mock_scrape_companies,
        mock_scrape_ministry,
    ):
        """Should skip email processing when run_emails=False"""
        # Setup mocks
        mock_manager = Mock()
        mock_profile = Mock()
        mock_profile.email_username = "wes.jobalerts@gmail.com"
        mock_profile.email_app_password = "app_password_123"
        mock_profile.name = "Wes"
        mock_profile.id = "wes"
        mock_manager.get_enabled_profiles.return_value = [mock_profile]
        mock_get_manager.return_value = mock_manager

        mock_scrape_companies.return_value = {
            "companies_checked": 68,
            "jobs_stored": 10,
        }
        mock_scrape_ministry.return_value = {
            "pages_scraped": 3,
            "jobs_stored": 5,
        }

        # Run with run_emails=False
        result = run_all_inboxes(run_emails=False, run_companies=True)

        # Email processing should NOT be called
        mock_process_inboxes.assert_not_called()

        # Companies and ministry should be called
        mock_scrape_companies.assert_called_once()
        mock_scrape_ministry.assert_called_once()

        # Result should not have email stats
        assert result["email_totals"] == {}

    @patch("jobs.weekly_unified_scraper._scrape_shared_ministry")
    @patch("jobs.weekly_unified_scraper._scrape_shared_companies")
    @patch("jobs.weekly_unified_scraper._process_all_inboxes")
    @patch("utils.profile_manager.get_profile_manager")
    def test_skip_companies_when_run_companies_false(
        self,
        mock_get_manager,
        mock_process_inboxes,
        mock_scrape_companies,
        mock_scrape_ministry,
    ):
        """Should skip company/ministry scraping when run_companies=False"""
        # Setup mocks
        mock_manager = Mock()
        mock_profile = Mock()
        mock_profile.email_username = "wes.jobalerts@gmail.com"
        mock_profile.email_app_password = "app_password_123"
        mock_profile.name = "Wes"
        mock_profile.id = "wes"
        mock_manager.get_enabled_profiles.return_value = [mock_profile]
        mock_get_manager.return_value = mock_manager

        mock_process_inboxes.return_value = {
            "wes": {
                "name": "Wes",
                "status": "success",
                "email_stats": {"emails_processed": 10},
            }
        }

        # Run with run_companies=False
        result = run_all_inboxes(run_emails=True, run_companies=False)

        # Email processing should be called
        mock_process_inboxes.assert_called_once()

        # Companies and ministry should NOT be called
        mock_scrape_companies.assert_not_called()
        mock_scrape_ministry.assert_not_called()

        # Result should not have company/ministry stats
        assert result["companies"] == {}
        assert result["ministry"] == {}

    @patch("jobs.weekly_unified_scraper._scrape_shared_testdevjobs")
    @patch("jobs.weekly_unified_scraper._scrape_shared_ministry")
    @patch("jobs.weekly_unified_scraper._scrape_shared_companies")
    @patch("jobs.weekly_unified_scraper._process_all_inboxes")
    @patch("utils.profile_manager.get_profile_manager")
    def test_aggregates_multiple_profiles(
        self,
        mock_get_manager,
        mock_process_inboxes,
        mock_scrape_companies,
        mock_scrape_ministry,
        mock_scrape_testdevjobs,
    ):
        """Should aggregate stats from multiple profiles correctly"""
        # Setup mocks
        mock_manager = Mock()

        mock_wes = Mock()
        mock_wes.email_username = "wes.jobalerts@gmail.com"
        mock_wes.email_app_password = "app_password_123"
        mock_wes.name = "Wes"
        mock_wes.id = "wes"

        mock_adam = Mock()
        mock_adam.email_username = "adam.jobalerts@gmail.com"
        mock_adam.email_app_password = "app_password_456"
        mock_adam.name = "Adam"
        mock_adam.id = "adam"

        mock_manager.get_enabled_profiles.return_value = [mock_wes, mock_adam]
        mock_get_manager.return_value = mock_manager

        mock_process_inboxes.return_value = {
            "wes": {
                "name": "Wes",
                "status": "success",
                "email_stats": {
                    "emails_processed": 10,
                    "opportunities_found": 8,
                    "jobs_stored": 5,
                    "notifications_sent": 2,
                },
            },
            "adam": {
                "name": "Adam",
                "status": "success",
                "email_stats": {
                    "emails_processed": 15,
                    "opportunities_found": 12,
                    "jobs_stored": 7,
                    "notifications_sent": 3,
                },
            },
        }

        mock_scrape_companies.return_value = {
            "companies_checked": 68,
            "jobs_scraped": 30,
            "jobs_stored": 10,
            "notifications_sent": 5,
        }

        mock_scrape_ministry.return_value = {
            "pages_scraped": 3,
            "jobs_found": 8,
            "jobs_stored": 4,
        }

        mock_scrape_testdevjobs.return_value = {
            "jobs_found": 6,
            "jobs_stored": 3,
        }

        # Run with both flags
        result = run_all_inboxes(run_emails=True, run_companies=True)

        # Check aggregated email totals
        assert result["email_totals"]["total_emails_processed"] == 25  # 10 + 15
        assert result["email_totals"]["total_jobs_found"] == 20  # 8 + 12
        assert result["email_totals"]["total_jobs_stored"] == 12  # 5 + 7
        assert result["email_totals"]["total_notifications"] == 5  # 2 + 3

        # Check grand totals (email + companies + ministry + testdevjobs)
        assert result["grand_totals"]["total_jobs_found"] == 64  # 20 + 30 + 8 + 6
        assert result["grand_totals"]["total_jobs_stored"] == 29  # 12 + 10 + 4 + 3
        assert result["grand_totals"]["total_notifications"] == 10  # 5 + 5


class TestCLIMutualExclusivity:
    """Test CLI argument validation"""

    def test_all_inboxes_and_profile_mutually_exclusive(self):
        """Should reject both --all-inboxes and --profile"""
        from argparse import ArgumentParser

        # Simulate the argparse setup from main()
        parser = ArgumentParser()
        parser.add_argument("--profile", type=str, choices=["wes", "adam"])
        parser.add_argument("--all-inboxes", action="store_true")

        # Test mutual exclusivity (should raise SystemExit via parser.error)
        with pytest.raises(SystemExit):
            args = parser.parse_args(["--all-inboxes", "--profile", "wes"])

            # Simulate the validation in main()
            if args.all_inboxes and args.profile:
                parser.error("Cannot specify both --all-inboxes and --profile")

    def test_all_inboxes_alone_is_valid(self):
        """Should accept --all-inboxes without --profile"""
        from argparse import ArgumentParser

        parser = ArgumentParser()
        parser.add_argument("--profile", type=str, choices=["wes", "adam"])
        parser.add_argument("--all-inboxes", action="store_true")

        args = parser.parse_args(["--all-inboxes"])

        assert args.all_inboxes is True
        assert args.profile is None

    def test_profile_alone_is_valid(self):
        """Should accept --profile without --all-inboxes"""
        from argparse import ArgumentParser

        parser = ArgumentParser()
        parser.add_argument("--profile", type=str, choices=["wes", "adam"])
        parser.add_argument("--all-inboxes", action="store_true")

        args = parser.parse_args(["--profile", "wes"])

        assert args.profile == "wes"
        assert args.all_inboxes is False


class TestErrorHandling:
    """Test error handling in multi-inbox mode"""

    @patch("jobs.weekly_unified_scraper._scrape_shared_ministry")
    @patch("jobs.weekly_unified_scraper._scrape_shared_companies")
    @patch("jobs.weekly_unified_scraper._process_all_inboxes")
    @patch("utils.profile_manager.get_profile_manager")
    def test_continues_after_company_scraping_error(
        self,
        mock_get_manager,
        mock_process_inboxes,
        mock_scrape_companies,
        mock_scrape_ministry,
    ):
        """Should continue to ministry scraping even if companies fail"""
        # Setup mocks
        mock_manager = Mock()
        mock_profile = Mock()
        mock_profile.email_username = "wes.jobalerts@gmail.com"
        mock_profile.email_app_password = "app_password_123"
        mock_profile.name = "Wes"
        mock_profile.id = "wes"
        mock_manager.get_enabled_profiles.return_value = [mock_profile]
        mock_get_manager.return_value = mock_manager

        mock_process_inboxes.return_value = {
            "wes": {
                "name": "Wes",
                "status": "success",
                "email_stats": {"emails_processed": 10},
            }
        }

        # Company scraping returns error dict
        mock_scrape_companies.return_value = {
            "companies_checked": 0,
            "jobs_scraped": 0,
            "jobs_stored": 0,
            "error": "Firecrawl API rate limit exceeded",
        }

        # Ministry scraping succeeds
        mock_scrape_ministry.return_value = {
            "pages_scraped": 3,
            "jobs_found": 8,
            "jobs_stored": 4,
        }

        result = run_all_inboxes(run_emails=True, run_companies=True)

        # All scraping functions should be called
        mock_process_inboxes.assert_called_once()
        mock_scrape_companies.assert_called_once()
        mock_scrape_ministry.assert_called_once()

        # Result should include error in companies section
        assert "error" in result["companies"]
        assert result["companies"]["error"] == "Firecrawl API rate limit exceeded"

        # Ministry should still have results
        assert result["ministry"]["jobs_stored"] == 4

        # Grand totals should only include successful sources
        assert result["grand_totals"]["total_jobs_stored"] == 4  # Only ministry
