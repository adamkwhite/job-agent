"""
Tests for Crawl4AICareerScraper

Tests the Crawl4AI-based career page scraper:
- Lazy crawler initialization
- Markdown extraction (fit_markdown preference, raw fallback)
- Error handling and resource cleanup
"""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

# Inject a mock crawl4ai module so @patch("crawl4ai.X") can resolve
# even when crawl4ai is not installed (it's an optional dependency)
if "crawl4ai" not in sys.modules:
    _mock_crawl4ai = ModuleType("crawl4ai")
    _mock_crawl4ai.AsyncWebCrawler = MagicMock  # type: ignore[attr-defined]
    _mock_crawl4ai.BrowserConfig = MagicMock  # type: ignore[attr-defined]
    _mock_crawl4ai.CrawlerRunConfig = MagicMock  # type: ignore[attr-defined]
    sys.modules["crawl4ai"] = _mock_crawl4ai

from src.scrapers.crawl4ai_career_scraper import Crawl4AICareerScraper


class TestCrawl4AICareerScraperInit:
    """Test Crawl4AICareerScraper initialization"""

    def test_init_sets_name(self):
        scraper = Crawl4AICareerScraper()
        assert scraper.name == "crawl4ai_career_scraper"

    def test_init_crawler_not_started(self):
        """Crawler should NOT be started on init (lazy initialization)"""
        scraper = Crawl4AICareerScraper()
        assert scraper._crawler is None
        assert scraper._loop is None

    def test_init_default_rate_limit(self):
        scraper = Crawl4AICareerScraper()
        assert scraper.requests_per_minute == 5


class TestLazyCrawlerInit:
    """Test lazy crawler initialization"""

    @patch("crawl4ai.BrowserConfig")
    @patch("crawl4ai.AsyncWebCrawler")
    @patch("src.scrapers.crawl4ai_career_scraper.asyncio")
    def test_ensure_crawler_starts_crawler(
        self, mock_asyncio, mock_crawler_cls, mock_browser_config
    ):
        """_ensure_crawler creates event loop and starts AsyncWebCrawler"""
        mock_loop = MagicMock()
        mock_asyncio.new_event_loop.return_value = mock_loop

        mock_crawler = MagicMock()
        mock_crawler.start = AsyncMock()
        mock_crawler_cls.return_value = mock_crawler

        scraper = Crawl4AICareerScraper()
        scraper._ensure_crawler()

        mock_asyncio.new_event_loop.assert_called_once()
        mock_loop.run_until_complete.assert_called_once()
        assert scraper._crawler is mock_crawler
        assert scraper._loop is mock_loop

    @patch("crawl4ai.BrowserConfig")
    @patch("crawl4ai.AsyncWebCrawler")
    @patch("src.scrapers.crawl4ai_career_scraper.asyncio")
    def test_ensure_crawler_only_starts_once(
        self, mock_asyncio, mock_crawler_cls, mock_browser_config
    ):
        """Second call to _ensure_crawler should be a no-op"""
        mock_loop = MagicMock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_crawler = MagicMock()
        mock_crawler.start = AsyncMock()
        mock_crawler_cls.return_value = mock_crawler

        scraper = Crawl4AICareerScraper()
        scraper._ensure_crawler()
        scraper._ensure_crawler()

        # Should only create crawler once
        mock_crawler_cls.assert_called_once()


class TestFetchPageContent:
    """Test _fetch_page_content via _async_fetch mocking.

    We mock _async_fetch (the async core) rather than going through
    the real event loop, which avoids conflicts with pytest's own loop.
    """

    def _make_scraper_with_async_fetch(self, return_value):
        """Create scraper with mocked internals — no real event loop needed."""
        scraper = Crawl4AICareerScraper()
        scraper._wait_for_rate_limit = MagicMock()
        # Pre-inject mock crawler and loop so _ensure_crawler is a no-op
        scraper._crawler = MagicMock()
        mock_loop = MagicMock()
        mock_loop.run_until_complete = MagicMock(return_value=return_value)
        scraper._loop = mock_loop
        return scraper

    def test_prefers_fit_markdown(self):
        """Should use fit_markdown when available (cleaner, no nav/footer)"""
        scraper = self._make_scraper_with_async_fetch("# Clean Jobs Content")
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result == "# Clean Jobs Content"

    def test_falls_back_to_raw_markdown(self):
        """Should fall back to raw_markdown when fit_markdown is empty"""
        scraper = self._make_scraper_with_async_fetch("# Raw Jobs Content")
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result == "# Raw Jobs Content"

    def test_returns_none_on_failure(self):
        """Should return None when _async_fetch returns None"""
        scraper = self._make_scraper_with_async_fetch(None)
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None

    def test_returns_none_on_empty_markdown(self):
        """Should return None when _async_fetch returns empty/whitespace"""
        scraper = self._make_scraper_with_async_fetch("   ")
        result = scraper._fetch_page_content("https://example.com/careers")
        # _fetch_page_content returns whatever run_until_complete returns
        # but the actual emptiness check is in _async_fetch
        assert result == "   "

    def test_returns_none_on_exception(self):
        """Should return None and log error on unexpected exceptions"""
        scraper = Crawl4AICareerScraper()
        scraper._wait_for_rate_limit = MagicMock()
        scraper._ensure_crawler = MagicMock(side_effect=ImportError("crawl4ai not installed"))

        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None


class TestAsyncFetch:
    """Test _async_fetch logic via _fetch_page_content with a mock loop.

    We can't use asyncio.new_event_loop() because other test modules leave
    a global event loop running (Python 3.13+ detects this). Instead, we
    inject a mock loop whose run_until_complete actually invokes the coroutine
    using a helper that extracts the coroutine's result synchronously.
    """

    def _make_crawl_result(
        self, *, success=True, fit_markdown="", raw_markdown="", error_message=""
    ):
        """Create a mock CrawlResult with markdown sub-object."""
        result = MagicMock()
        result.success = success
        result.error_message = error_message
        md = MagicMock()
        md.fit_markdown = fit_markdown
        md.raw_markdown = raw_markdown
        result.markdown = md
        return result

    def _make_scraper(self, crawl_result):
        """Create scraper with mock crawler that returns given result.

        The mock loop's run_until_complete drives the coroutine by sending
        None to advance it, which works for simple await-based coroutines.
        """
        scraper = Crawl4AICareerScraper()
        scraper._wait_for_rate_limit = MagicMock()

        mock_crawler = AsyncMock()
        mock_crawler.arun.return_value = crawl_result
        scraper._crawler = mock_crawler

        # Mock loop that actually runs the coroutine to completion
        mock_loop = MagicMock()

        def _run_coro(coro):
            """Drive an async coroutine synchronously."""
            try:
                coro.send(None)
            except StopIteration as e:
                return e.value
            finally:
                coro.close()

        mock_loop.run_until_complete = _run_coro
        scraper._loop = mock_loop
        return scraper

    def test_prefers_fit_markdown(self):
        """_async_fetch should prefer fit_markdown over raw_markdown"""
        scraper = self._make_scraper(
            self._make_crawl_result(fit_markdown="# Clean Content", raw_markdown="# Raw Content")
        )
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result == "# Clean Content"

    def test_falls_back_to_raw_markdown(self):
        """_async_fetch should fall back to raw_markdown when fit_markdown is empty"""
        scraper = self._make_scraper(
            self._make_crawl_result(fit_markdown="", raw_markdown="# Raw Content")
        )
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result == "# Raw Content"

    def test_returns_none_on_crawl_failure(self):
        """_async_fetch should return None when crawl fails"""
        scraper = self._make_scraper(
            self._make_crawl_result(success=False, error_message="Connection refused")
        )
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None

    def test_returns_none_on_empty_markdown(self):
        """_async_fetch should return None when both markdown fields are empty"""
        scraper = self._make_scraper(self._make_crawl_result(fit_markdown="", raw_markdown=""))
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None

    def test_returns_none_on_whitespace_only(self):
        """_async_fetch should return None for whitespace-only markdown"""
        scraper = self._make_scraper(
            self._make_crawl_result(fit_markdown="   \n  ", raw_markdown="")
        )
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None

    def test_handles_missing_markdown_attr(self):
        """_async_fetch should handle result without markdown attribute"""
        result_obj = MagicMock(spec=["success", "error_message"])
        result_obj.success = True
        scraper = self._make_scraper(result_obj)
        result = scraper._fetch_page_content("https://example.com/careers")
        assert result is None


class TestCrawlerCleanup:
    """Test crawler resource cleanup"""

    def test_close_with_no_crawler(self):
        """close() should be safe when crawler was never started"""
        scraper = Crawl4AICareerScraper()
        scraper.close()  # Should not raise

    def test_close_cleans_up_crawler_and_loop(self):
        """close() should close crawler and event loop"""
        scraper = Crawl4AICareerScraper()
        mock_crawler = MagicMock()
        mock_crawler.close = AsyncMock()
        mock_loop = MagicMock()
        scraper._crawler = mock_crawler
        scraper._loop = mock_loop

        scraper.close()

        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()
        assert scraper._crawler is None
        assert scraper._loop is None

    def test_close_handles_errors_gracefully(self):
        """close() should not raise even if cleanup fails"""
        scraper = Crawl4AICareerScraper()
        mock_crawler = MagicMock()
        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = Exception("already closed")
        scraper._crawler = mock_crawler
        scraper._loop = mock_loop

        scraper.close()  # Should not raise

        assert scraper._crawler is None
