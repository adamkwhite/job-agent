"""
Playwright-based career page scraper

Uses Playwright Chromium to render JS-heavy career pages locally (free),
converting HTML to markdown via html2text for extraction by BaseCareerScraper.
"""

import logging
from typing import Any

import html2text

from scrapers.base_career_scraper import BaseCareerScraper

logger = logging.getLogger(__name__)


class PlaywrightCareerScraper(BaseCareerScraper):
    """Scrape career pages using local Playwright Chromium browser"""

    def __init__(
        self,
        requests_per_minute: int = 5,
        enable_llm_extraction: bool = False,
        enable_pagination: bool = True,
        cache_dir: str = "data/firecrawl_cache",
        cache_ttl_hours: int = 24,
        headless: bool = True,
    ) -> None:
        """
        Initialize Playwright-based scraper

        Args:
            requests_per_minute: Max requests per minute (default 5 — be polite)
            enable_llm_extraction: Enable LLM extraction alongside regex
            enable_pagination: Enable pagination support via sitemap discovery
            cache_dir: Directory to store cached markdown files
            cache_ttl_hours: Cache time-to-live in hours
            headless: Run browser in headless mode (default: True)
        """
        super().__init__(
            requests_per_minute=requests_per_minute,
            enable_llm_extraction=enable_llm_extraction,
            enable_pagination=enable_pagination,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
        )
        self.name = "playwright_career_scraper"
        self._headless = headless

        # Configure html2text to produce markdown matching extraction regex patterns
        # ignore_links=False keeps [text](url) for pattern1 regex
        # body_width=0 disables line wrapping
        self._h2t = html2text.HTML2Text()
        self._h2t.ignore_links = False
        self._h2t.body_width = 0
        self._h2t.ignore_images = True
        self._h2t.ignore_emphasis = False
        self._h2t.protect_links = False

        # Lazy browser init — don't start Chromium until first cache miss
        self._playwright: Any = None
        self._browser: Any = None

    def _ensure_browser(self) -> None:
        """Lazy-init Playwright Chromium on first cache miss."""
        if self._browser is not None:
            return

        from playwright.sync_api import sync_playwright

        logger.info("Starting Playwright Chromium browser (headless=%s)", self._headless)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        logger.info("Playwright browser started")

    def _fetch_page_content(self, url: str) -> str | None:
        """Render page with Playwright and convert HTML to markdown."""
        try:
            self._wait_for_rate_limit()
            self._ensure_browser()

            page = self._browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                # Extra wait for JS-heavy career pages (React, Angular, etc.)
                page.wait_for_timeout(2000)

                html = page.content()
            finally:
                page.close()

            markdown = self._h2t.handle(html)
            if not markdown or not markdown.strip():
                logger.warning("Empty markdown from %s", url)
                return None

            return markdown

        except Exception as e:
            logger.error("Playwright error fetching %s: %s", url, e)
            print(f"  ✗ Playwright error: {e}")
            return None

    def close(self) -> None:
        """Clean up browser process."""
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
            self._browser = None

        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning("Error stopping playwright: %s", e)
            self._playwright = None

    def __del__(self) -> None:
        """Ensure browser cleanup on garbage collection."""
        self.close()
