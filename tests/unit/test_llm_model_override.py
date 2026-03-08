"""
Tests for LLM model override (Issue #345).

Tests the --llm-model CLI flag threading from WeeklyUnifiedScraper
down to LLMExtractor, including model-specific pricing.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.extractors.llm_extractor import LLMExtractor
from src.jobs.company_scraper import CompanyScraper


class TestLLMExtractorModelOverride:
    """Test LLMExtractor model_override parameter."""

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_default_model_from_config(self, _db, _budget, mock_chat):
        """Should use model from config when no override given."""
        extractor = LLMExtractor()
        assert extractor.model == "anthropic/claude-3.5-sonnet"
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-3.5-sonnet"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_model_override(self, _db, _budget, mock_chat):
        """Should use override model instead of config model."""
        extractor = LLMExtractor(model_override="google/gemini-2.5-flash")
        assert extractor.model == "google/gemini-2.5-flash"
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "google/gemini-2.5-flash"

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_none_override_uses_config(self, _db, _budget, _chat):
        """Should use config model when override is None."""
        extractor = LLMExtractor(model_override=None)
        assert extractor.model == "anthropic/claude-3.5-sonnet"


class TestModelPricing:
    """Test _get_model_pricing returns correct rates."""

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_sonnet_pricing(self, _db, _budget, _chat):
        """Sonnet should return $3/$15 per 1M tokens."""
        extractor = LLMExtractor()
        input_rate, output_rate = extractor._get_model_pricing()
        assert input_rate == 3.00
        assert output_rate == 15.00

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_gemini_flash_pricing(self, _db, _budget, _chat):
        """Gemini Flash should be much cheaper than Sonnet."""
        extractor = LLMExtractor(model_override="google/gemini-2.5-flash")
        input_rate, output_rate = extractor._get_model_pricing()
        assert input_rate == 0.30
        assert output_rate == 2.50

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_unknown_model_falls_back_to_sonnet(self, _db, _budget, _chat):
        """Unknown models should use conservative Sonnet pricing."""
        extractor = LLMExtractor(model_override="unknown/model-v1")
        input_rate, output_rate = extractor._get_model_pricing()
        assert input_rate == 3.00
        assert output_rate == 15.00

    @patch("src.extractors.llm_extractor.ChatOpenAI")
    @patch("src.extractors.llm_extractor.LLMBudgetService")
    @patch("src.extractors.llm_extractor.JobDatabase")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_haiku_pricing(self, _db, _budget, _chat):
        """Haiku should be significantly cheaper than Sonnet."""
        extractor = LLMExtractor(model_override="anthropic/claude-3-haiku")
        input_rate, output_rate = extractor._get_model_pricing()
        assert input_rate == 0.25
        assert output_rate == 1.25


class TestCompanyScraperLLMModel:
    """Test llm_model threading through CompanyScraper."""

    def test_passes_llm_model_to_career_scraper(self):
        """Should pass llm_model through _create_career_scraper."""
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch.object(
                CompanyScraper, "_create_career_scraper", return_value=MagicMock()
            ) as mock_create,
        ):
            CompanyScraper(llm_model="google/gemini-2.5-flash")
            mock_create.assert_called_once_with(
                "playwright",
                False,
                True,
                llm_model="google/gemini-2.5-flash",
            )

    def test_stores_llm_model_for_fallback(self):
        """Should store llm_model so fallback scraper gets it too."""
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch.object(CompanyScraper, "_create_career_scraper", return_value=MagicMock()),
        ):
            scraper = CompanyScraper(llm_model="meta-llama/llama-3.3-70b-instruct")
            assert scraper.llm_model == "meta-llama/llama-3.3-70b-instruct"

    def test_fallback_scraper_gets_llm_model(self):
        """Fallback Firecrawl scraper should get same llm_model."""
        with (
            patch("src.jobs.company_scraper.CompanyService"),
            patch("src.jobs.company_scraper.JobFilter"),
            patch("src.jobs.company_scraper.ProfileScorer"),
            patch("src.jobs.company_scraper.JobDatabase"),
            patch("src.jobs.company_scraper.JobNotifier"),
            patch.object(CompanyScraper, "_create_career_scraper", return_value=MagicMock()),
        ):
            scraper = CompanyScraper(llm_model="google/gemini-2.5-flash")
            scraper.backend = "crawl4ai"
            scraper._fallback_scraper = None

            mock_fallback = MagicMock()
            with patch.object(
                CompanyScraper, "_create_career_scraper", return_value=mock_fallback
            ) as mock_create:
                result = scraper._get_fallback_scraper()

            assert result is mock_fallback
            mock_create.assert_called_once_with(
                "firecrawl",
                False,
                True,
                llm_model="google/gemini-2.5-flash",
            )


class TestWeeklyUnifiedScraperLLMModel:
    """Test llm_model threading through WeeklyUnifiedScraper CLI."""

    def test_cli_parses_llm_model(self):
        """Should parse --llm-model from CLI args."""
        from src.jobs.weekly_unified_scraper import main

        with (
            patch("src.jobs.weekly_unified_scraper.WeeklyUnifiedScraper") as mock_cls,
            patch("src.utils.scraper_monitor.ScraperMonitor") as mock_monitor_cls,
            patch(
                "sys.argv",
                [
                    "weekly_unified_scraper.py",
                    "--companies-only",
                    "--llm-model",
                    "google/gemini-2.5-flash",
                ],
            ),
        ):
            mock_instance = MagicMock()
            mock_instance.run_all.return_value = {
                "email": {},
                "companies": {},
                "ministry": {},
                "testdevjobs": {},
                "total_jobs_found": 0,
                "total_jobs_stored": 0,
                "total_notifications": 0,
            }
            mock_cls.return_value = mock_instance

            mock_monitor = MagicMock()
            mock_monitor.get_exit_code.return_value = 0
            mock_monitor_cls.return_value = mock_monitor

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_cls.assert_called_once_with(
                profile=None,
                scraper_backend=None,
                llm_model="google/gemini-2.5-flash",
            )
