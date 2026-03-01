"""
Abstract base class for career page scrapers

Provides shared logic for caching, rate limiting, extraction, deduplication,
validation, and sitemap-based pagination. Subclasses only need to implement
_fetch_page_content() to provide their own page-fetching strategy.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from models import OpportunityData
from utils.url_validator import validate_job_url

logger = logging.getLogger(__name__)


class BaseCareerScraper(ABC):
    """Abstract base class for career page scrapers with shared orchestration logic"""

    def __init__(
        self,
        requests_per_minute: int = 9,
        enable_llm_extraction: bool = False,
        enable_pagination: bool = True,
        cache_dir: str = "data/firecrawl_cache",
        cache_ttl_hours: int = 24,
    ) -> None:
        """
        Initialize scraper with rate limiting and caching

        Args:
            requests_per_minute: Max requests per minute
            enable_llm_extraction: Enable LLM extraction alongside regex
            enable_pagination: Enable pagination support via sitemap discovery
            cache_dir: Directory to store cached markdown files
            cache_ttl_hours: Cache time-to-live in hours
        """
        self.name = "base_career_scraper"

        # Rate limiting
        self.requests_per_minute = requests_per_minute
        self.request_times: list[float] = []
        self.min_delay = 60.0 / requests_per_minute

        # Cache configuration
        self.cache_dir = Path(cache_dir)
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # LLM extraction (optional)
        self.enable_llm_extraction = enable_llm_extraction
        self.llm_extractor = None

        if enable_llm_extraction:
            try:
                from extractors.llm_extractor import LLMExtractor

                self.llm_extractor = LLMExtractor()
                logger.info("LLM extraction enabled for %s", type(self).__name__)
            except Exception as e:
                logger.warning(
                    f"Failed to initialize LLM extractor: {e}. Continuing with regex only."
                )
                self.enable_llm_extraction = False

        # Pagination support (optional)
        self.enable_pagination = enable_pagination
        if enable_pagination:
            logger.info("Pagination support enabled via sitemap discovery")

    @abstractmethod
    def _fetch_page_content(self, url: str) -> str | None:
        """Fetch a URL and return its content as markdown. None on failure.

        Subclasses implement the actual page-fetching strategy (e.g., Firecrawl API,
        Playwright browser rendering).
        """

    # ==================== Public API ====================

    def fetch_page_markdown(
        self,
        url: str,
        company_name: str,
        is_main_page: bool = False,
    ) -> str | None:
        """Fetch page markdown with caching and rate limiting.

        Checks cache first (for main pages), then calls _fetch_page_content().
        Saves result to cache for main pages.

        Args:
            url: URL to fetch
            company_name: Company name (used for cache key)
            is_main_page: Whether this is the main careers page (affects caching)

        Returns:
            Markdown content string, or None on failure
        """
        if is_main_page:
            cached = self._check_cache(company_name)
            if cached:
                return cached

        if is_main_page:
            print(f"  ⚡ Using {type(self).__name__}...")

        markdown = self._fetch_page_content(url)

        if not markdown:
            if is_main_page:
                print("  ✗ Failed to scrape page")
            return None

        if markdown and is_main_page:
            self._save_cache(company_name, markdown)
        return markdown

    def scrape_jobs(self, careers_url: str, company_name: str) -> list[tuple[OpportunityData, str]]:
        """
        Scrape jobs from a career page with pagination support

        If pagination is enabled, this will:
        1. Discover additional job URLs via sitemap
        2. Scrape the main careers page
        3. Scrape discovered paginated/individual job pages
        4. Deduplicate and merge all results

        Args:
            careers_url: URL to company's career page
            company_name: Name of the company

        Returns:
            List of tuples (OpportunityData, extraction_method)
        """
        print(f"\nScraping jobs from: {careers_url}")

        try:
            # Step 1: Discover additional job URLs (if pagination enabled)
            discovered_urls = self._discover_job_urls(careers_url, company_name)

            # Step 2: Scrape main careers page
            main_page_jobs = self._scrape_single_page(careers_url, company_name, is_main_page=True)

            # Step 3: Scrape discovered pages (if any)
            paginated_jobs = self._scrape_paginated_jobs(discovered_urls, company_name)

            # Step 4: Deduplicate and merge results
            all_jobs = main_page_jobs + paginated_jobs
            deduplicated_jobs = self._deduplicate_jobs(all_jobs)

            # Show summary
            self._print_scraping_summary(
                deduplicated_jobs, discovered_urls, main_page_jobs, paginated_jobs, all_jobs
            )

            return deduplicated_jobs

        except Exception as e:
            logger.error(f"Error scraping {careers_url}: {e}", exc_info=True)
            print(f"  ✗ Error scraping page: {e}")
            return []

    # ==================== Orchestration ====================

    def _scrape_single_page(
        self, url: str, company_name: str, is_main_page: bool = False
    ) -> list[tuple[OpportunityData, str]]:
        """Scrape jobs from a single page"""
        try:
            markdown = self.fetch_page_markdown(url, company_name, is_main_page)
            if markdown is None:
                return []

            regex_jobs = self._extract_jobs_from_markdown(markdown, url, company_name)
            if is_main_page:
                print(f"  📝 Regex extraction: {len(regex_jobs)} job listings found")

            jobs_with_method = self._process_extracted_jobs(regex_jobs, company_name, "regex")

            if is_main_page:
                jobs_with_method.extend(self._run_llm_extraction(markdown, company_name))

            return jobs_with_method

        except Exception as e:
            logger.error(f"Error scraping single page {url}: {e}")
            return []

    def _scrape_paginated_jobs(
        self, discovered_urls: list[str], company_name: str
    ) -> list[tuple[OpportunityData, str]]:
        """Scrape jobs from discovered paginated URLs"""
        if not discovered_urls or not self.enable_pagination:
            return []

        print(f"  📄 Scraping {len(discovered_urls)} additional pages...")
        paginated_jobs = []
        for i, url in enumerate(discovered_urls[:10], 1):
            print(f"    [{i}/{min(len(discovered_urls), 10)}] {url}")
            page_jobs = self._scrape_single_page(url, company_name, is_main_page=False)
            paginated_jobs.extend(page_jobs)
        return paginated_jobs

    def _run_llm_extraction(
        self,
        markdown: str,
        company_name: str,
    ) -> list[tuple[OpportunityData, str]]:
        """Run LLM extraction if enabled and budget available."""
        if not (self.enable_llm_extraction and self.llm_extractor):
            return []

        if not self.llm_extractor.budget_available():
            logger.warning(f"LLM budget exceeded, skipping LLM extraction for {company_name}")
            print("  ⚠ LLM budget exceeded, using regex only")
            return []

        try:
            logger.info(f"Running LLM extraction for {company_name}")
            llm_jobs = self.llm_extractor.extract_jobs(markdown, company_name)
            print(f"  🤖 LLM extraction: {len(llm_jobs)} job listings found")
            return self._process_extracted_jobs(llm_jobs, company_name, "llm")
        except Exception as e:
            logger.error(f"LLM extraction failed for {company_name}: {e}")
            print(f"  ✗ LLM extraction failed: {e}")
            return []

    def _print_scraping_summary(
        self,
        deduplicated_jobs: list[tuple[OpportunityData, str]],
        discovered_urls: list[str],
        main_page_jobs: list[tuple[OpportunityData, str]],
        paginated_jobs: list[tuple[OpportunityData, str]],
        all_jobs: list[tuple[OpportunityData, str]],
    ) -> None:
        """Print summary of scraping results"""
        if discovered_urls:
            print(
                f"  ✓ Total: {len(deduplicated_jobs)} unique jobs "
                f"({len(main_page_jobs)} from main + {len(paginated_jobs)} from pages, "
                f"{len(all_jobs) - len(deduplicated_jobs)} duplicates removed)"
            )
        else:
            print(f"  ✓ Total: {len(deduplicated_jobs)} job listings")

        if deduplicated_jobs:
            for i, (job, method) in enumerate(deduplicated_jobs, 1):
                method_label = "🤖 LLM" if method == "llm" else "📝 Regex"
                print(f"    {i}. [{method_label}] {job.title}")
                if job.link:
                    print(f"       Link: {job.link}")

    # ==================== Extraction ====================

    def _extract_jobs_from_markdown(
        self, markdown: str, careers_url: str, company_name: str
    ) -> list[OpportunityData]:
        """Extract job listings from markdown content"""
        # Try pattern 1 (linked jobs with locations)
        jobs = self._extract_jobs_from_pattern1(markdown, company_name)

        # If no jobs found with pattern 1, try pattern 2 (headers)
        if not jobs:
            jobs = self._extract_jobs_from_pattern2(markdown, careers_url, company_name)

        return jobs

    def _extract_jobs_from_pattern1(
        self, markdown: str, company_name: str
    ) -> list[OpportunityData]:
        """Extract jobs using pattern 1: linked jobs with locations"""
        jobs = []

        pattern1 = re.compile(
            r"\["
            r"([^\[\]]+?)"
            r"(?:\n\n|\\n\\n|\\<br>\\<br>)"
            r"([^\[\]]+?)"
            r"\]"
            r"\(([^\)]+)\)",
            re.MULTILINE,
        )

        matches = pattern1.findall(markdown)
        for title, location, link in matches:
            title = title.strip()
            location = location.strip()

            if self._is_likely_job_title(title):
                jobs.append(
                    OpportunityData(
                        type="direct_job",
                        title=title,
                        company=company_name,
                        location=location,
                        link=link,
                        source="company_monitoring",
                    )
                )

        return jobs

    def _extract_jobs_from_pattern2(
        self, markdown: str, careers_url: str, company_name: str
    ) -> list[OpportunityData]:
        """Extract jobs using pattern 2: headers without explicit links"""
        jobs: list[OpportunityData] = []

        pattern2 = re.compile(
            r"^(?:##|###|####) ([^\n]+)$",
            re.MULTILINE,
        )

        markdown_lower = markdown.lower()
        has_jobs = (
            " jobs" in markdown_lower
            or " job" in markdown_lower
            or "current" in markdown_lower
            and "job" in markdown_lower
            or "open" in markdown_lower
            and "position" in markdown_lower
            or "hiring" in markdown_lower
            or "recruiting" in markdown_lower
        )

        if not has_jobs:
            return jobs

        headers = pattern2.findall(markdown)
        for header in headers:
            header = header.strip()

            if self._is_likely_job_title(header) and len(header) > 10:
                header_idx = markdown.find(header)
                start_search = header_idx + len(header)
                context = markdown[start_search : start_search + 100]

                location_match = re.search(
                    r"\n{1,5}(?:Location:\s{0,5})?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?,\s{0,2}[A-Z]{2})",
                    context,
                )
                location = location_match.group(1).strip() if location_match else ""

                jobs.append(
                    OpportunityData(
                        type="direct_job",
                        title=header,
                        company=company_name,
                        location=location,
                        link=careers_url,
                        source="company_monitoring",
                    )
                )

        return jobs

    def _process_extracted_jobs(
        self, jobs: list[OpportunityData], company_name: str, method: str
    ) -> list[tuple[OpportunityData, str]]:
        """Validate job URLs and tag with extraction method"""
        validated_jobs = self._validate_job_urls(jobs, company_name)
        return [(job, method) for job in validated_jobs]

    # ==================== Validation ====================

    def _validate_job_urls(
        self, jobs: list[OpportunityData], company_name: str
    ) -> list[OpportunityData]:
        """Validate job URLs and mark invalid ones as stale"""
        validated_jobs = []

        for job in jobs:
            if not job.link:
                validated_jobs.append(job)
                continue

            is_valid, reason = validate_job_url(job.link)

            job_dict = job.__dict__.copy()
            job_dict["url_validated"] = is_valid
            job_dict["url_validated_at"] = datetime.now().isoformat()
            job_dict["url_validation_reason"] = reason

            if not is_valid:
                logger.warning(f"Invalid job URL for {company_name}: {job.link} (reason: {reason})")
                job_dict["is_stale"] = True
                job_dict["stale_reason"] = f"url_invalid: {reason}"
            else:
                job_dict["is_stale"] = False

            validated_job = OpportunityData(**job_dict)
            validated_jobs.append(validated_job)

        invalid_count = sum(
            1 for job in validated_jobs if not job.__dict__.get("url_validated", True)
        )
        if invalid_count > 0:
            print(f"  ⚠ {invalid_count} job(s) with invalid URLs marked as stale")

        return validated_jobs

    @staticmethod
    def _is_likely_job_title(text: str) -> bool:
        """Check if text looks like a job title"""
        exclude_patterns = [
            r"^(view|learn|see|click|apply|read|about|home|contact)",
            r"(page|site|website|logo|icon|menu|navigation)",
            r"^(current|openings?|jobs?|careers?|opportunities)$",
            r"^(department|location|type|filter|search|sort)",
        ]

        text_lower = text.lower()

        for pattern in exclude_patterns:
            if re.search(pattern, text_lower):
                return False

        job_keywords = [
            "engineer",
            "developer",
            "manager",
            "director",
            "lead",
            "architect",
            "designer",
            "analyst",
            "scientist",
            "specialist",
            "coordinator",
            "technician",
            "administrator",
            "officer",
            "associate",
            "consultant",
        ]

        return any(keyword in text_lower for keyword in job_keywords)

    @staticmethod
    def _is_job_url(url: str) -> bool:
        """Check if URL looks like a job listing page"""
        url_lower = url.lower()

        strong_indicators = [
            "/job/",
            "/jobs/",
            "/positions/",
            "/openings/",
            "?page=",
            "/page/",
            "/opportunities/",
            "-jobs",
        ]

        weak_indicators = [
            "/careers/",
        ]

        has_strong_indicator = any(indicator in url_lower for indicator in strong_indicators)

        if not has_strong_indicator:
            has_weak_indicator = any(indicator in url_lower for indicator in weak_indicators)
            if has_weak_indicator:
                job_terms = [
                    "engineer",
                    "developer",
                    "manager",
                    "director",
                    "lead",
                    "senior",
                    "junior",
                    "staff",
                    "principal",
                    "vp",
                    "architect",
                    "/en-us/",
                    "/en-ca/",
                    "/opening",
                    "/position",
                    "/role",
                ]
                has_strong_indicator = any(term in url_lower for term in job_terms)
            else:
                has_strong_indicator = False

        exclude_patterns = [
            "/login",
            "/apply",
            "/submit",
            "/signup",
            "/sign-up",
            "/privacy",
            "/terms",
            "/contact",
            "/about",
            "/blog",
            "/news",
            "/guide",
            "/faq",
            "/benefits",
            "/culture",
            "/values",
            "/diversity",
            "/inclusion",
            "/location",
            "/office",
            "/team",
            "/search",
            "/filter",
        ]
        has_exclusion = any(pattern in url_lower for pattern in exclude_patterns)

        return has_strong_indicator and not has_exclusion

    # ==================== Deduplication ====================

    @staticmethod
    def _dedup_score(item: tuple[OpportunityData, str]) -> tuple[int, int, int]:
        """Score a job for deduplication ranking (higher is better)."""
        job, method = item
        has_valid_url = 1 if job.link and job.__dict__.get("url_validated", True) else 0
        is_llm = 1 if method == "llm" else 0
        has_url = 1 if job.link else 0
        return has_valid_url, is_llm, has_url

    def _deduplicate_jobs(
        self, jobs_with_methods: list[tuple[OpportunityData, str]]
    ) -> list[tuple[OpportunityData, str]]:
        """Deduplicate jobs by title + company combination"""
        from collections import defaultdict

        job_groups: dict[tuple[str, str], list[tuple[OpportunityData, str]]] = defaultdict(list)

        for job, method in jobs_with_methods:
            title_normalized = " ".join(job.title.lower().split())
            company_normalized = job.company.lower().strip()
            job_groups[(title_normalized, company_normalized)].append((job, method))

        deduplicated = []
        for group in job_groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                deduplicated.append(max(group, key=self._dedup_score))

        return deduplicated

    # ==================== Caching ====================

    def _get_cache_path(self, company_name: str) -> Path:
        """Get the cache file path for a company"""
        normalized_name = company_name.lower().replace(" ", "_").replace("/", "_")
        today = datetime.now().strftime("%Y%m%d")
        return self.cache_dir / f"{normalized_name}_{today}.md"

    def _check_cache(self, company_name: str) -> str | None:
        """Check if cached markdown exists for today"""
        cache_file = self._get_cache_path(company_name)

        if not cache_file.exists():
            logger.debug(f"Cache miss: {cache_file}")
            return None

        cache_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600

        if cache_age_hours > self.cache_ttl_hours:
            logger.info(f"Cache expired ({cache_age_hours:.1f}h old): {cache_file}")
            return None

        logger.info(f"Cache hit ({cache_age_hours:.1f}h old): {cache_file}")
        print(f"  ✓ Using cached markdown (saved {cache_age_hours:.1f}h ago)")
        return cache_file.read_text(encoding="utf-8")

    def _save_cache(self, company_name: str, markdown: str) -> None:
        """Save markdown content to cache"""
        cache_file = self._get_cache_path(company_name)

        try:
            cache_file.write_text(markdown, encoding="utf-8")
            logger.info(f"Saved to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    # ==================== Rate Limiting ====================

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting by waiting if necessary"""
        now = time.time()

        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = self.request_times[0]
            wait_time = 60 - (now - oldest_request) + 0.5
            if wait_time > 0:
                print(f"  ⏳ Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]

        if self.request_times:
            time_since_last = now - self.request_times[-1]
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                time.sleep(wait_time)
                now = time.time()

        self.request_times.append(now)

    # ==================== Sitemap Pagination ====================

    def _discover_job_urls(self, careers_url: str, company_name: str) -> list[str]:
        """Discover job listing URLs via sitemap parsing (free).

        Subclasses may override to add additional discovery methods.
        """
        if not self.enable_pagination:
            return []

        logger.info(f"Attempting sitemap discovery for {company_name}")
        job_urls = self._parse_sitemap(careers_url)

        if job_urls:
            print(f"  ✓ Sitemap: Found {len(job_urls)} job URLs (free)")
            logger.info(f"Sitemap discovery found {len(job_urls)} URLs for {company_name}")
            return job_urls[:50]

        print("  ℹ No additional URLs discovered, will scrape main page only")
        logger.info(f"No additional URLs discovered for {company_name}")
        return []

    def _extract_job_urls_from_xml(self, content: bytes) -> list[str]:
        """Extract job URLs from sitemap XML content, handling namespace variants."""
        root = ET.fromstring(content)

        # XML namespace URI is an identifier, not an HTTP request - official sitemap schema
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}  # NOSONAR

        urls = [
            loc.text
            for loc in root.findall(".//ns:loc", ns)
            if loc.text and self._is_job_url(loc.text)
        ]

        if not urls:
            urls = [
                loc.text
                for loc in root.findall(".//loc")
                if loc.text and self._is_job_url(loc.text)
            ]

        return urls

    def _parse_sitemap(self, careers_url: str) -> list[str]:
        """Parse sitemap.xml to discover job URLs (FREE)"""
        parsed = urlparse(careers_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        sitemap_candidates = [
            urljoin(domain, "/sitemap.xml"),
            urljoin(domain, "/careers/sitemap.xml"),
            urljoin(domain, "/jobs/sitemap.xml"),
            careers_url.rstrip("/") + "/sitemap.xml",
        ]

        for sitemap_url in sitemap_candidates:
            urls = self._try_fetch_sitemap(sitemap_url)
            if urls:
                return urls

        logger.debug("No sitemap found at any candidate location")
        return []

    def _try_fetch_sitemap(self, sitemap_url: str) -> list[str]:
        """Fetch and parse a single sitemap URL, returning job URLs or empty list."""
        try:
            logger.debug(f"Trying sitemap: {sitemap_url}")
            response = requests.get(
                sitemap_url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; JobAgent/1.0; +https://github.com/user/job-agent)"
                },
            )

            if response.status_code != 200:
                logger.debug(f"Sitemap {sitemap_url} returned {response.status_code}")
                return []

            urls = self._extract_job_urls_from_xml(response.content)
            if urls:
                logger.info(f"Found {len(urls)} job URLs in {sitemap_url}")
            return urls

        except ET.ParseError as e:
            logger.debug(f"Failed to parse sitemap {sitemap_url}: {e}")
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error parsing {sitemap_url}: {e}")
        return []
