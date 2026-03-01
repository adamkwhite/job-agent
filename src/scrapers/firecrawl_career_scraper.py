"""
Firecrawl-based career page scraper
Uses Firecrawl API to scrape JavaScript-heavy career pages
Supports pagination via sitemap parsing and Firecrawl map fallback
"""

import logging
import os
import signal

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from scrapers.base_career_scraper import BaseCareerScraper

load_dotenv()

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when an operation times out"""

    pass


def timeout_handler(_signum, _frame):
    """Handler for timeout signal"""
    raise TimeoutError("Operation timed out")


class FirecrawlCareerScraper(BaseCareerScraper):
    """Scrape career pages using Firecrawl API with rate limiting"""

    def __init__(
        self,
        requests_per_minute: int = 9,
        enable_llm_extraction: bool = False,
        enable_pagination: bool = True,
        timeout_seconds: int = 60,
        cache_dir: str = "data/firecrawl_cache",
        cache_ttl_hours: int = 24,
    ):
        """
        Initialize Firecrawl-based scraper

        Args:
            requests_per_minute: Max requests per minute (default 9 to stay under 10/min limit)
            enable_llm_extraction: Enable LLM extraction alongside regex (default: False)
            enable_pagination: Enable pagination support via sitemap/map discovery (default: True)
            timeout_seconds: Timeout for each scrape request (default: 60 seconds)
            cache_dir: Directory to store cached markdown files (default: data/firecrawl_cache)
            cache_ttl_hours: Cache time-to-live in hours (default: 24)
        """
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        self.firecrawl = FirecrawlApp(api_key=api_key)

        # Timeout (Firecrawl-specific, uses SIGALRM)
        self.timeout_seconds = timeout_seconds

        super().__init__(
            requests_per_minute=requests_per_minute,
            enable_llm_extraction=enable_llm_extraction,
            enable_pagination=enable_pagination,
            cache_dir=cache_dir,
            cache_ttl_hours=cache_ttl_hours,
        )
        self.name = "firecrawl_career_scraper"

    def _fetch_page_content(self, url: str) -> str | None:
        """Fetch page content via Firecrawl API. Returns markdown string or None."""
        result = self._firecrawl_scrape(url)
        if not result:
            return None
        return result.get("markdown", "")

    def _firecrawl_scrape(self, url: str) -> dict | None:
        """
        Scrape a URL using Firecrawl API with rate limiting and timeout

        Args:
            url: URL to scrape

        Returns:
            Dictionary with 'markdown' key containing scraped content, or None on error
        """
        try:
            # Wait if necessary to respect rate limits
            self._wait_for_rate_limit()

            # Set up timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)

            try:
                # Make the API request
                document = self.firecrawl.scrape(url, formats=["markdown"], wait_for=5000)
                # Convert Document object to dict for compatibility
                return {"markdown": document.markdown if document.markdown else ""}
            finally:
                # Cancel the alarm
                signal.alarm(0)

        except TimeoutError:
            print(f"  ✗ Firecrawl API timeout: Request exceeded {self.timeout_seconds}s")
            return None
        except Exception as e:
            print(f"  ✗ Firecrawl API error: {e}")
            return None

    def _discover_job_urls(self, careers_url: str, company_name: str) -> list[str]:
        """
        Discover job URLs via sitemap (free) with Firecrawl map fallback (paid).

        Overrides base class to add Firecrawl map as a second-tier discovery method.
        """
        if not self.enable_pagination:
            return []

        # Try 1: Free sitemap parsing (from base class)
        logger.info(f"Attempting sitemap discovery for {company_name}")
        job_urls = self._parse_sitemap(careers_url)

        if job_urls:
            print(f"  ✓ Sitemap: Found {len(job_urls)} job URLs (free)")
            logger.info(f"Sitemap discovery found {len(job_urls)} URLs for {company_name}")
            return job_urls[:50]

        # Try 2: Firecrawl map fallback (paid)
        logger.info(f"No sitemap found, attempting Firecrawl map for {company_name}")
        print("  ⚠ No sitemap found, using Firecrawl map (1 credit)...")
        job_urls = self._firecrawl_map(careers_url, company_name)

        if job_urls:
            print(f"  ✓ Firecrawl map: Found {len(job_urls)} job URLs")
            logger.info(f"Firecrawl map found {len(job_urls)} URLs for {company_name}")
            return job_urls[:50]

        print("  ℹ No additional URLs discovered, will scrape main page only")
        logger.info(f"No additional URLs discovered for {company_name}")
        return []

    def _firecrawl_map(self, careers_url: str, company_name: str) -> list[str]:
        """
        Use Firecrawl map API to discover job URLs (PAID ~$0.003/company)

        Fallback when sitemap parsing fails.

        Args:
            careers_url: URL to careers page
            company_name: Company name for logging

        Returns:
            List of job URLs discovered via Firecrawl map
        """
        try:
            # Wait for rate limit before making map request
            self._wait_for_rate_limit()

            # Use Firecrawl map API to discover all URLs on site
            logger.info(f"Calling Firecrawl map API for {careers_url}")

            # Set up timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)

            try:
                # Call map API with search filter for job-related pages
                map_result = self.firecrawl.map(
                    url=careers_url,
                    search="job position career opening",
                    limit=100,
                )
            finally:
                signal.alarm(0)

            # Extract URLs from map result
            if hasattr(map_result, "links"):
                all_urls = [
                    link.url if hasattr(link, "url") else str(link) for link in map_result.links
                ]
            elif isinstance(map_result, dict) and "links" in map_result:
                all_urls = map_result["links"]
            else:
                logger.warning(f"Unexpected map result format: {type(map_result)}")
                return []

            # Filter for job URLs
            job_urls = [url for url in all_urls if self._is_job_url(url)]

            logger.info(f"Firecrawl map found {len(job_urls)} job URLs for {company_name}")
            return job_urls

        except TimeoutError:
            logger.warning(f"Firecrawl map timeout for {careers_url}")
            print(f"  ✗ Firecrawl map timeout after {self.timeout_seconds}s")
            return []
        except AttributeError as e:
            logger.warning(f"Firecrawl SDK method not available: {e}")
            print("  ✗ Firecrawl map not supported by SDK version")
            return []
        except Exception as e:
            logger.warning(f"Firecrawl map failed for {careers_url}: {e}")
            print(f"  ✗ Firecrawl map error: {e}")
            return []
