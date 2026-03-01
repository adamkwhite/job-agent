"""
Tests for PlaywrightCareerScraper

Tests the Playwright-based career page scraper:
- html2text configuration for regex-compatible markdown
- Lazy browser initialization
- Page fetching and HTML-to-markdown conversion
- Error handling (timeout, connection issues)
- Resource cleanup
"""

from unittest.mock import MagicMock, patch

from src.scrapers.playwright_career_scraper import PlaywrightCareerScraper


class TestPlaywrightCareerScraperInit:
    """Test PlaywrightCareerScraper initialization"""

    def test_init_sets_name(self):
        """Test scraper initializes with correct name"""
        scraper = PlaywrightCareerScraper()
        assert scraper.name == "playwright_career_scraper"

    def test_init_default_rate_limit(self):
        """Default rate limit is 5 rpm (more polite than Firecrawl's 9)"""
        scraper = PlaywrightCareerScraper()
        assert scraper.requests_per_minute == 5

    def test_init_browser_not_started(self):
        """Browser should NOT be started on init (lazy initialization)"""
        scraper = PlaywrightCareerScraper()
        assert scraper._browser is None
        assert scraper._playwright is None

    def test_init_html2text_config(self):
        """html2text should be configured for regex-compatible markdown"""
        scraper = PlaywrightCareerScraper()
        assert scraper._h2t.ignore_links is False  # Keep [text](url) format
        assert scraper._h2t.body_width == 0  # No line wrapping
        assert scraper._h2t.ignore_images is True

    def test_init_custom_rate_limit(self):
        """Custom rate limit is respected"""
        scraper = PlaywrightCareerScraper(requests_per_minute=3)
        assert scraper.requests_per_minute == 3


class TestLazyBrowserInit:
    """Test lazy browser initialization"""

    @patch("playwright.sync_api.sync_playwright")
    def test_ensure_browser_starts_playwright(self, mock_sync_playwright):
        """_ensure_browser starts Playwright and launches Chromium"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser

        scraper = PlaywrightCareerScraper()
        scraper._ensure_browser()

        mock_pw.chromium.launch.assert_called_once_with(headless=True)
        assert scraper._browser is mock_browser
        assert scraper._playwright is mock_pw

    @patch("playwright.sync_api.sync_playwright")
    def test_ensure_browser_only_starts_once(self, mock_sync_playwright):
        """Second call to _ensure_browser should be a no-op"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser

        scraper = PlaywrightCareerScraper()
        scraper._ensure_browser()
        scraper._ensure_browser()

        # Should only launch once
        mock_pw.chromium.launch.assert_called_once()

    @patch("playwright.sync_api.sync_playwright")
    def test_headless_false_mode(self, mock_sync_playwright):
        """headless=False is passed through to Chromium launch"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_pw.chromium.launch.return_value = MagicMock()

        scraper = PlaywrightCareerScraper(headless=False)
        scraper._ensure_browser()

        mock_pw.chromium.launch.assert_called_once_with(headless=False)


class TestFetchPageContent:
    """Test _fetch_page_content method"""

    @patch("playwright.sync_api.sync_playwright")
    def test_fetches_and_converts_html(self, mock_sync_playwright, mocker):
        """HTML content is rendered and converted to markdown"""
        # Set up mock browser chain
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page

        # Mock page.content() to return HTML
        mock_page.content.return_value = (
            "<html><body>"
            "<h1>Careers</h1>"
            '<a href="https://example.com/job/123">Senior Engineer</a>'
            "</body></html>"
        )

        scraper = PlaywrightCareerScraper()
        mocker.patch.object(scraper, "_wait_for_rate_limit")

        result = scraper._fetch_page_content("https://example.com/careers")

        assert result is not None
        assert "Senior Engineer" in result
        # html2text should produce [text](url) format
        assert "https://example.com/job/123" in result

        # Page should be closed after use
        mock_page.close.assert_called_once()

    @patch("playwright.sync_api.sync_playwright")
    def test_returns_none_on_empty_html(self, mock_sync_playwright, mocker):
        """Empty HTML returns None"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body></body></html>"

        scraper = PlaywrightCareerScraper()
        mocker.patch.object(scraper, "_wait_for_rate_limit")

        result = scraper._fetch_page_content("https://example.com/careers")

        # html2text of empty body produces whitespace-only string
        # Our code checks for empty/whitespace-only and returns None
        assert result is None

    @patch("playwright.sync_api.sync_playwright")
    def test_returns_none_on_timeout(self, mock_sync_playwright, mocker, capsys):
        """Timeout during page.goto returns None with error message"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.side_effect = Exception("Timeout 60000ms exceeded")

        scraper = PlaywrightCareerScraper()
        mocker.patch.object(scraper, "_wait_for_rate_limit")

        result = scraper._fetch_page_content("https://slow-site.com/careers")

        assert result is None
        captured = capsys.readouterr()
        assert "Playwright error" in captured.out

        # Page should still be closed
        mock_page.close.assert_called_once()

    @patch("playwright.sync_api.sync_playwright")
    def test_page_uses_realistic_user_agent(self, mock_sync_playwright, mocker):
        """Pages should use a realistic user agent to avoid bot detection"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body><h1>Jobs</h1></body></html>"

        scraper = PlaywrightCareerScraper()
        mocker.patch.object(scraper, "_wait_for_rate_limit")

        scraper._fetch_page_content("https://example.com/careers")

        # Check user_agent was set in new_page
        call_kwargs = mock_browser.new_page.call_args
        assert "user_agent" in call_kwargs.kwargs
        assert "Mozilla" in call_kwargs.kwargs["user_agent"]

    @patch("playwright.sync_api.sync_playwright")
    def test_waits_for_networkidle(self, mock_sync_playwright, mocker):
        """Page navigation waits for network idle to catch JS-rendered content"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body><h1>Jobs</h1></body></html>"

        scraper = PlaywrightCareerScraper()
        mocker.patch.object(scraper, "_wait_for_rate_limit")

        scraper._fetch_page_content("https://example.com/careers")

        mock_page.goto.assert_called_once_with(
            "https://example.com/careers",
            wait_until="networkidle",
            timeout=60000,
        )
        # Should also wait extra 2s for JS rendering
        mock_page.wait_for_timeout.assert_called_once_with(2000)


class TestBrowserCleanup:
    """Test browser resource cleanup"""

    def test_close_with_no_browser(self):
        """close() should be safe when browser was never started"""
        scraper = PlaywrightCareerScraper()
        scraper.close()  # Should not raise

    @patch("playwright.sync_api.sync_playwright")
    def test_close_cleans_up_browser(self, mock_sync_playwright):
        """close() should close browser and stop playwright"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser

        scraper = PlaywrightCareerScraper()
        scraper._ensure_browser()
        scraper.close()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
        assert scraper._browser is None
        assert scraper._playwright is None

    @patch("playwright.sync_api.sync_playwright")
    def test_close_handles_errors_gracefully(self, mock_sync_playwright):
        """close() should not raise even if cleanup fails"""
        mock_pw = MagicMock()
        mock_sync_playwright.return_value.start.return_value = mock_pw
        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.close.side_effect = Exception("already closed")

        scraper = PlaywrightCareerScraper()
        scraper._ensure_browser()
        scraper.close()  # Should not raise

        assert scraper._browser is None


class TestHtml2textMarkdownFormat:
    """Test that html2text output matches the regex patterns used by BaseCareerScraper"""

    def test_links_produce_markdown_format(self):
        """html2text should produce [text](url) format matching pattern1 regex"""
        scraper = PlaywrightCareerScraper()
        html = '<a href="https://example.com/job/123">Senior Engineer</a>'
        markdown = scraper._h2t.handle(html)

        assert "[Senior Engineer]" in markdown
        assert "(https://example.com/job/123)" in markdown

    def test_headers_produce_markdown_format(self):
        """html2text should produce ## Header format matching pattern2 regex"""
        scraper = PlaywrightCareerScraper()
        html = "<h2>Director of Engineering</h2>"
        markdown = scraper._h2t.handle(html)

        assert "##" in markdown
        assert "Director of Engineering" in markdown

    def test_no_line_wrapping(self):
        """Long lines should not be wrapped (body_width=0)"""
        scraper = PlaywrightCareerScraper()
        long_title = "Senior Staff Software Engineer - Robotics Platform Infrastructure"
        html = f"<p>{long_title}</p>"
        markdown = scraper._h2t.handle(html)

        # Title should be on one line (not wrapped)
        assert long_title in markdown
