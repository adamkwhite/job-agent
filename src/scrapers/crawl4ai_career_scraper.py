"""
Crawl4AI-based career page scraper

Uses Crawl4AI (Playwright + built-in stealth + smart markdown extraction)
for sites that block vanilla Playwright. Returns LLM-friendly markdown
with nav/footer noise removed via fit_markdown.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from scrapers.base_career_scraper import BaseCareerScraper

if TYPE_CHECKING:
    from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)


class Crawl4AICareerScraper(BaseCareerScraper):
    """Scrape career pages using Crawl4AI (async Playwright with stealth)"""

    def __init__(
        self,
        requests_per_minute: int = 5,
        enable_llm_extraction: bool = False,
        enable_pagination: bool = True,
        cache_dir: str = "data/firecrawl_cache",
        cache_ttl_hours: int = 24,
    ) -> None:
        super().__init__(
            requests_per_minute=requests_per_minute,
            enable_llm_extraction=enable_llm_extraction,
            enable_pagination=enable_pagination,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
        )
        self.name = "crawl4ai_career_scraper"

        # Lazy init — don't start browser until first cache miss
        self._crawler: AsyncWebCrawler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _ensure_crawler(self) -> None:
        """Lazy-init Crawl4AI AsyncWebCrawler on first cache miss."""
        if self._crawler is not None:
            return

        from crawl4ai import AsyncWebCrawler, BrowserConfig

        logger.info("Starting Crawl4AI crawler")
        self._loop = asyncio.new_event_loop()

        browser_config = BrowserConfig(
            headless=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        self._crawler = AsyncWebCrawler(config=browser_config)
        self._loop.run_until_complete(self._crawler.start())
        logger.info("Crawl4AI crawler started")

    async def _async_fetch(self, url: str) -> str | None:
        """Async fetch via Crawl4AI crawler."""
        from crawl4ai import CrawlerRunConfig

        config = CrawlerRunConfig(
            wait_until="networkidle",
            page_timeout=60000,
        )

        # Guaranteed non-None by _ensure_crawler in _fetch_page_content
        assert self._crawler is not None
        result = await self._crawler.arun(url=url, config=config)

        if not result.success:
            logger.error("Crawl4AI failed for %s: %s", url, result.error_message)
            print(f"  ✗ Crawl4AI error: {result.error_message}")
            return None

        # Prefer fit_markdown (nav/footer stripped) over raw_markdown
        markdown = ""
        if hasattr(result, "markdown"):
            md = result.markdown
            if hasattr(md, "fit_markdown") and md.fit_markdown:
                markdown = md.fit_markdown
            elif hasattr(md, "raw_markdown") and md.raw_markdown:
                markdown = md.raw_markdown

        if not markdown or not markdown.strip():
            logger.warning("Empty markdown from Crawl4AI for %s", url)
            return None

        return markdown

    def _fetch_page_content(self, url: str) -> str | None:
        """Fetch page content via Crawl4AI (sync wrapper around async API)."""
        try:
            self._wait_for_rate_limit()
            self._ensure_crawler()
            return self._loop.run_until_complete(self._async_fetch(url))  # type: ignore[union-attr]
        except Exception as e:
            logger.error("Crawl4AI error fetching %s: %s", url, e)
            print(f"  ✗ Crawl4AI error: {e}")
            return None

    def close(self) -> None:
        """Clean up crawler and event loop."""
        if self._crawler is not None and self._loop is not None:
            try:
                self._loop.run_until_complete(self._crawler.close())
            except Exception as e:
                logger.warning("Error closing Crawl4AI crawler: %s", e)
            self._crawler = None

        if self._loop is not None:
            try:
                self._loop.close()
            except Exception as e:
                logger.warning("Error closing event loop: %s", e)
            self._loop = None

    def __del__(self) -> None:
        """Ensure cleanup on garbage collection."""
        self.close()
