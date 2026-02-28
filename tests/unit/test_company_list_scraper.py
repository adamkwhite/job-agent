"""
Unit tests for company_list_scraper batch processing and DB storage
"""

import argparse
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models import OpportunityData
from scrapers.company_list_scraper import _load_urls, _store_to_db


def _make_opportunity(
    company: str, source: str = "company_list:example.com", **kwargs
) -> OpportunityData:
    """Helper to create a minimal OpportunityData for testing."""
    defaults = {
        "type": "funding_lead",
        "title": "",
        "company": company,
        "location": "",
        "link": kwargs.pop("link", ""),
        "description": kwargs.pop("description", "A test company"),
        "salary": "",
        "job_type": "",
        "posted_date": "",
        "source": source,
        "source_email": "",
        "received_at": "2026-01-01T00:00:00",
        "keywords_matched": [],
        "raw_content": "{}",
        "funding_stage": "",
        "company_website": kwargs.pop("company_website", "https://example.com"),
        "company_location": "",
    }
    defaults.update(kwargs)
    return OpportunityData(**defaults)


class TestLoadUrls:
    """Tests for _load_urls helper function."""

    def test_load_urls_from_single_url(self):
        """Verify _load_urls returns URL from positional arg."""
        args = argparse.Namespace(url="https://example.com/list", input_file=None)
        result = _load_urls(args)
        assert result == ["https://example.com/list"]

    def test_load_urls_from_file(self):
        """Verify _load_urls reads file, skips blanks and comments."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("https://site1.com/list\n")
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("  \n")
            f.write("https://site2.com/list\n")
            f.write("  # Another comment\n")
            f.write("https://site3.com/list\n")
            f.flush()
            filepath = f.name

        args = argparse.Namespace(url=None, input_file=filepath)
        result = _load_urls(args)

        assert result == [
            "https://site1.com/list",
            "https://site2.com/list",
            "https://site3.com/list",
        ]

        # Cleanup
        Path(filepath).unlink()

    def test_load_urls_combines_url_and_file(self):
        """Verify both positional URL and file URLs are combined."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("https://file-url.com/list\n")
            f.flush()
            filepath = f.name

        args = argparse.Namespace(url="https://cli-url.com/list", input_file=filepath)
        result = _load_urls(args)

        assert result == ["https://cli-url.com/list", "https://file-url.com/list"]

        Path(filepath).unlink()

    def test_load_urls_requires_input(self):
        """Verify SystemExit when neither URL nor file provided."""
        args = argparse.Namespace(url=None, input_file=None)
        with pytest.raises(SystemExit):
            _load_urls(args)


class TestBatchScrape:
    """Tests for batch scraping behavior in main()."""

    @patch("scrapers.company_list_scraper.CompanyListScraper")
    def test_batch_scrape_aggregates_results(self, mock_scraper_cls):
        """Mock scrape_url for multiple URLs, verify all results combined."""
        opp1 = _make_opportunity("CompanyA")
        opp2 = _make_opportunity("CompanyB")

        mock_instance = MagicMock()
        mock_instance.scrape_url.side_effect = [[opp1], [opp2]]
        mock_scraper_cls.return_value = mock_instance

        from scrapers.company_list_scraper import main

        # Create a temp file with 2 URLs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("https://site1.com\nhttps://site2.com\n")
            f.flush()
            filepath = f.name

        with (
            patch("sys.argv", ["prog", "--input-file", filepath, "--no-ai"]),
            patch("scrapers.company_list_scraper._print_summary"),
            patch("scrapers.company_list_scraper._print_opportunities"),
        ):
            main()

        assert mock_instance.scrape_url.call_count == 2
        Path(filepath).unlink()

    @patch("scrapers.company_list_scraper.CompanyListScraper")
    def test_batch_scrape_continues_on_error(self, mock_scraper_cls):
        """Mock one URL to raise, verify others still processed."""
        opp = _make_opportunity("GoodCompany")

        mock_instance = MagicMock()
        mock_instance.scrape_url.side_effect = [
            Exception("Network error"),
            [opp],
        ]
        mock_scraper_cls.return_value = mock_instance

        from scrapers.company_list_scraper import main

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("https://bad-site.com\nhttps://good-site.com\n")
            f.flush()
            filepath = f.name

        with (
            patch("sys.argv", ["prog", "--input-file", filepath, "--no-ai"]),
            patch("scrapers.company_list_scraper._print_summary"),
            patch("scrapers.company_list_scraper._print_opportunities"),
        ):
            main()

        # Both URLs were attempted
        assert mock_instance.scrape_url.call_count == 2
        Path(filepath).unlink()


class TestStoreDb:
    """Tests for --store-db integration."""

    def test_store_db_converts_opportunities_to_batch_format(self):
        """Verify OpportunityData objects are converted to dicts for add_companies_batch."""
        opp = _make_opportunity(
            "TestCorp",
            source="company_list:example.com",
            company_website="https://testcorp.com",
            description="A robotics company doing cool things",
        )

        with patch("api.company_service.CompanyService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.add_companies_batch.return_value = {
                "added": 1,
                "skipped_duplicates": 0,
                "errors": 0,
                "details": [],
            }
            mock_service_cls.return_value = mock_service

            _store_to_db([opp])

            call_args = mock_service.add_companies_batch.call_args[0][0]
            assert len(call_args) == 1
            assert call_args[0]["name"] == "TestCorp"
            assert call_args[0]["careers_url"] == "https://testcorp.com"
            assert "company_list:example.com" in call_args[0]["notes"]

    def test_store_db_calls_add_companies_batch(self):
        """Verify CompanyService.add_companies_batch is called with correct data."""
        opps = [
            _make_opportunity("AlphaCo", company_website="https://alpha.com"),
            _make_opportunity("BetaCo", company_website="https://beta.com"),
        ]

        with patch("api.company_service.CompanyService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.add_companies_batch.return_value = {
                "added": 2,
                "skipped_duplicates": 0,
                "errors": 0,
                "details": [],
            }
            mock_service_cls.return_value = mock_service

            stats = _store_to_db(opps)

            mock_service.add_companies_batch.assert_called_once()
            batch = mock_service.add_companies_batch.call_args[0][0]
            assert len(batch) == 2
            assert batch[0]["name"] == "AlphaCo"
            assert batch[1]["name"] == "BetaCo"
            assert stats["added"] == 2

    def test_store_db_empty_list_returns_empty_stats(self):
        """Verify empty opportunity list doesn't call add_companies_batch."""
        with patch("api.company_service.CompanyService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            stats = _store_to_db([])

            mock_service.add_companies_batch.assert_not_called()
            assert stats["added"] == 0

    def test_store_db_falls_back_to_link_when_no_website(self):
        """Verify careers_url uses opp.link when company_website is empty."""
        opp = _make_opportunity(
            "NoWebsiteCo",
            company_website="",
            link="https://jobboard.com/company/nowebsite",
        )

        with patch("api.company_service.CompanyService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.add_companies_batch.return_value = {
                "added": 1,
                "skipped_duplicates": 0,
                "errors": 0,
                "details": [],
            }
            mock_service_cls.return_value = mock_service

            _store_to_db([opp])

            batch = mock_service.add_companies_batch.call_args[0][0]
            assert batch[0]["careers_url"] == "https://jobboard.com/company/nowebsite"
