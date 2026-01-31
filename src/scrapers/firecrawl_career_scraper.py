"""
Firecrawl-based career page scraper
Uses Firecrawl API to scrape JavaScript-heavy career pages
Supports pagination via sitemap parsing and Firecrawl map fallback
"""

import logging
import os
import re
import signal
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from models import OpportunityData
from utils.url_validator import validate_job_url

load_dotenv()

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when an operation times out"""

    pass


def timeout_handler(_signum, _frame):
    """Handler for timeout signal"""
    raise TimeoutError("Operation timed out")


class FirecrawlCareerScraper:
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
        Initialize scraper with rate limiting and caching

        Args:
            requests_per_minute: Max requests per minute (default 9 to stay under 10/min limit)
            enable_llm_extraction: Enable LLM extraction alongside regex (default: False)
            enable_pagination: Enable pagination support via sitemap/map discovery (default: True)
            timeout_seconds: Timeout for each scrape request (default: 60 seconds)
            cache_dir: Directory to store cached markdown files (default: data/firecrawl_cache)
            cache_ttl_hours: Cache time-to-live in hours (default: 24)
        """
        self.name = "firecrawl_career_scraper"
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        self.firecrawl = FirecrawlApp(api_key=api_key)

        # Rate limiting
        self.requests_per_minute = requests_per_minute
        self.request_times: list[float] = []  # Track timestamps of recent requests
        self.min_delay = 60.0 / requests_per_minute  # Minimum seconds between requests

        # Timeout
        self.timeout_seconds = timeout_seconds

        # Cache configuration
        self.cache_dir = Path(cache_dir)
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)  # Ensure cache dir exists

        # LLM extraction (optional)
        self.enable_llm_extraction = enable_llm_extraction
        self.llm_extractor = None

        if enable_llm_extraction:
            try:
                from extractors.llm_extractor import LLMExtractor

                self.llm_extractor = LLMExtractor()
                logger.info("LLM extraction enabled for FirecrawlCareerScraper")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize LLM extractor: {e}. Continuing with regex only."
                )
                self.enable_llm_extraction = False

        # Pagination support (optional)
        self.enable_pagination = enable_pagination
        if enable_pagination:
            logger.info("Pagination support enabled via sitemap/map discovery")

    def _get_cache_path(self, company_name: str) -> Path:
        """
        Get the cache file path for a company

        Args:
            company_name: Name of the company

        Returns:
            Path to cache file (company_name_YYYYMMDD.md)
        """
        # Normalize company name for filename
        normalized_name = company_name.lower().replace(" ", "_").replace("/", "_")
        today = datetime.now().strftime("%Y%m%d")
        return self.cache_dir / f"{normalized_name}_{today}.md"

    def _check_cache(self, company_name: str) -> str | None:
        """
        Check if cached markdown exists for today

        Args:
            company_name: Name of the company

        Returns:
            Cached markdown content if found and valid, None otherwise
        """
        cache_file = self._get_cache_path(company_name)

        if not cache_file.exists():
            logger.debug(f"Cache miss: {cache_file}")
            return None

        # Check if cache is still valid (within TTL)
        cache_age_hours = (time.time() - cache_file.stat().st_mtime) / 3600

        if cache_age_hours > self.cache_ttl_hours:
            logger.info(f"Cache expired ({cache_age_hours:.1f}h old): {cache_file}")
            return None

        logger.info(f"Cache hit ({cache_age_hours:.1f}h old): {cache_file}")
        print(f"  ✓ Using cached markdown (saved {cache_age_hours:.1f}h ago)")
        return cache_file.read_text(encoding="utf-8")

    def _save_cache(self, company_name: str, markdown: str) -> None:
        """
        Save markdown content to cache

        Args:
            company_name: Name of the company
            markdown: Markdown content to save
        """
        cache_file = self._get_cache_path(company_name)

        try:
            cache_file.write_text(markdown, encoding="utf-8")
            logger.info(f"Saved to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def scrape_jobs(self, careers_url: str, company_name: str) -> list[tuple[OpportunityData, str]]:
        """
        Scrape jobs from a career page using Firecrawl with pagination support

        If pagination is enabled, this will:
        1. Discover additional job URLs via sitemap/Firecrawl map
        2. Scrape the main careers page
        3. Scrape discovered paginated/individual job pages
        4. Deduplicate and merge all results

        Args:
            careers_url: URL to company's career page
            company_name: Name of the company

        Returns:
            List of tuples (OpportunityData, extraction_method) where extraction_method is 'regex' or 'llm'
        """
        print(f"\nScraping jobs from: {careers_url}")

        try:
            # Step 1: Discover additional job URLs (if pagination enabled)
            discovered_urls = self._discover_job_urls(careers_url, company_name)

            # Step 2: Scrape main careers page
            main_page_jobs = self._scrape_single_page(careers_url, company_name, is_main_page=True)

            # Step 3: Scrape discovered pages (if any)
            paginated_jobs = []
            if discovered_urls and self.enable_pagination:
                print(f"  📄 Scraping {len(discovered_urls)} additional pages...")
                for i, url in enumerate(
                    discovered_urls[:10], 1
                ):  # Limit to 10 to avoid cost explosion
                    print(f"    [{i}/{min(len(discovered_urls), 10)}] {url}")
                    page_jobs = self._scrape_single_page(url, company_name, is_main_page=False)
                    paginated_jobs.extend(page_jobs)

            # Step 4: Deduplicate and merge results
            all_jobs = main_page_jobs + paginated_jobs
            deduplicated_jobs = self._deduplicate_jobs(all_jobs)

            # Show summary
            if discovered_urls:
                print(
                    f"  ✓ Total: {len(deduplicated_jobs)} unique jobs "
                    f"({len(main_page_jobs)} from main + {len(paginated_jobs)} from pages, "
                    f"{len(all_jobs) - len(deduplicated_jobs)} duplicates removed)"
                )
            else:
                print(f"  ✓ Total: {len(deduplicated_jobs)} job listings")

            # Show job titles and links for user visibility
            if deduplicated_jobs:
                for i, (job, method) in enumerate(deduplicated_jobs, 1):
                    method_label = "🤖 LLM" if method == "llm" else "📝 Regex"
                    print(f"    {i}. [{method_label}] {job.title}")
                    if job.link:
                        print(f"       Link: {job.link}")

            return deduplicated_jobs

        except Exception as e:
            logger.error(f"Error scraping {careers_url}: {e}", exc_info=True)
            print(f"  ✗ Error scraping page: {e}")
            return []

    def _scrape_single_page(
        self, url: str, company_name: str, is_main_page: bool = False
    ) -> list[tuple[OpportunityData, str]]:
        """
        Scrape jobs from a single page

        Args:
            url: URL to scrape
            company_name: Company name
            is_main_page: Whether this is the main careers page (affects caching)

        Returns:
            List of tuples (OpportunityData, extraction_method)
        """
        try:
            # Check cache first (only for main page to avoid cache pollution)
            cached_markdown = None
            if is_main_page:
                cached_markdown = self._check_cache(company_name)

            if cached_markdown:
                markdown = cached_markdown
            else:
                # Cache miss - fetch via Firecrawl API
                if is_main_page:
                    print("  ⚡ Using Firecrawl API...")
                result = self._firecrawl_scrape(url)

                if not result:
                    if is_main_page:
                        print("  ✗ Failed to scrape page")
                    return []

                markdown = result.get("markdown", "")

                # Save to cache for future use (only main page)
                if markdown and is_main_page:
                    self._save_cache(company_name, markdown)

            # Extract jobs from markdown using regex (primary method)
            regex_jobs = self._extract_jobs_from_markdown(markdown, url, company_name)
            if is_main_page:
                print(f"  📝 Regex extraction: {len(regex_jobs)} job listings found")

            # Validate and tag jobs with extraction method
            jobs_with_method = self._process_extracted_jobs(regex_jobs, company_name, "regex")

            # Run LLM extraction if enabled and budget available (only on main page to save costs)
            if self.enable_llm_extraction and self.llm_extractor and is_main_page:
                if self.llm_extractor.budget_available():
                    try:
                        logger.info(f"Running LLM extraction for {company_name}")
                        llm_jobs = self.llm_extractor.extract_jobs(markdown, company_name)
                        print(f"  🤖 LLM extraction: {len(llm_jobs)} job listings found")

                        # Validate and add LLM jobs
                        jobs_with_method.extend(
                            self._process_extracted_jobs(llm_jobs, company_name, "llm")
                        )
                    except Exception as e:
                        logger.error(f"LLM extraction failed for {company_name}: {e}")
                        print(f"  ✗ LLM extraction failed: {e}")
                else:
                    logger.warning(
                        f"LLM budget exceeded, skipping LLM extraction for {company_name}"
                    )
                    print("  ⚠ LLM budget exceeded, using regex only")

            return jobs_with_method

        except Exception as e:
            logger.error(f"Error scraping single page {url}: {e}")
            return []

    def _wait_for_rate_limit(self):
        """
        Enforce rate limiting by waiting if necessary

        Ensures we don't exceed requests_per_minute by tracking request timestamps
        and adding delays when needed
        """
        now = time.time()

        # Remove timestamps older than 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]

        # If we're at the limit, wait until we can make another request
        if len(self.request_times) >= self.requests_per_minute:
            # Wait until the oldest request is >60 seconds old
            oldest_request = self.request_times[0]
            wait_time = 60 - (now - oldest_request) + 0.5  # Add 0.5s buffer
            if wait_time > 0:
                print(f"  ⏳ Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                now = time.time()
                # Clean up old timestamps again after waiting
                self.request_times = [t for t in self.request_times if now - t < 60]

        # Also enforce minimum delay between consecutive requests
        if self.request_times:
            time_since_last = now - self.request_times[-1]
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                time.sleep(wait_time)
                now = time.time()

        # Record this request timestamp
        self.request_times.append(now)

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
                document = self.firecrawl.scrape(url, formats=["markdown"])
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

    def _extract_jobs_from_markdown(
        self, markdown: str, careers_url: str, company_name: str
    ) -> list[OpportunityData]:
        """
        Extract job listings from markdown content

        Args:
            markdown: Markdown content from Firecrawl
            careers_url: Original careers page URL
            company_name: Company name

        Returns:
            List of OpportunityData objects
        """
        jobs = []

        # Common patterns for job listings
        # Pattern 1: Job title followed by location (Greenhouse, Lever style)
        # Example: "[Senior Engineer\n\nToronto, Canada](https://url)"
        # ReDoS-safe: Negated character classes prevent backtracking
        pattern1 = re.compile(
            r"\["  # Opening bracket
            r"([^\[\]]+?)"  # Title - non-greedy, stops at newlines or ]
            r"(?:\n\n|\\n\\n|\\<br>\\<br>)"  # Separator between title and location
            r"([^\[\]]+?)"  # Location - non-greedy, stops at ]
            r"\]"  # Closing bracket
            r"\(([^\)]+)\)",  # Link in parentheses - cannot backtrack past )
            re.MULTILINE,
        )

        # Pattern 2: Job title in headers
        # Example: "## Senior Software Engineer"
        # ReDoS-safe: Use space instead of \s+ to prevent backtracking with [^\n]+
        pattern2 = re.compile(
            r"^(?:##|###|####) ([^\n]+)$",  # Single space, then capture to end of line
            re.MULTILINE,
        )

        # Try pattern 1 (linked jobs with locations)
        matches = pattern1.findall(markdown)
        for title, location, link in matches:
            title = title.strip()
            location = location.strip()

            # Filter out common non-job links
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

        # If no jobs found with pattern 1, try pattern 2 (headers)
        if not jobs:
            # Look for job indicators like "7 jobs" or "Current Job Openings" or "Open Positions"
            # Use case-insensitive string search to avoid regex complexity
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

            if has_jobs:
                # Find all headers that might be job titles
                headers = pattern2.findall(markdown)

                for header in headers:
                    header = header.strip()

                    if self._is_likely_job_title(header) and len(header) > 10:
                        # Try to find location near this header
                        # Look for text after the header (skip the header line itself)
                        header_idx = markdown.find(header)
                        # Skip past the header and any immediate newlines
                        start_search = header_idx + len(header)
                        context = markdown[start_search : start_search + 100]

                        # Look for city, province/state pattern on its own line
                        # Pattern: newlines, optional "Location: " prefix, then "City Name, XX"
                        # ReDoS-safe: Use {1,5} limits instead of + to prevent backtracking
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
                                link=careers_url,  # Use main careers page as link
                                source="company_monitoring",
                            )
                        )

        return jobs

    def _process_extracted_jobs(
        self, jobs: list[OpportunityData], company_name: str, method: str
    ) -> list[tuple[OpportunityData, str]]:
        """
        Validate job URLs and tag with extraction method

        Args:
            jobs: List of extracted jobs
            company_name: Company name for logging
            method: Extraction method ('regex' or 'llm')

        Returns:
            List of tuples (validated_job, method)
        """
        validated_jobs = self._validate_job_urls(jobs, company_name)
        return [(job, method) for job in validated_jobs]

    def _validate_job_urls(
        self, jobs: list[OpportunityData], company_name: str
    ) -> list[OpportunityData]:
        """
        Validate job URLs and mark invalid ones as stale

        Args:
            jobs: List of job opportunities to validate
            company_name: Company name for logging

        Returns:
            List of jobs with validation metadata added
        """
        validated_jobs = []

        for job in jobs:
            if not job.link:
                # No URL to validate - keep job as-is
                validated_jobs.append(job)
                continue

            # Validate the job URL
            is_valid, reason = validate_job_url(job.link)

            # Add validation metadata to job
            job_dict = job.__dict__.copy()
            job_dict["url_validated"] = is_valid
            job_dict["url_validated_at"] = datetime.now().isoformat()
            job_dict["url_validation_reason"] = reason

            if not is_valid:
                # Mark invalid URLs as stale
                logger.warning(f"Invalid job URL for {company_name}: {job.link} (reason: {reason})")
                job_dict["is_stale"] = True
                job_dict["stale_reason"] = f"url_invalid: {reason}"
            else:
                job_dict["is_stale"] = False

            # Create new OpportunityData with updated fields
            validated_job = OpportunityData(**job_dict)
            validated_jobs.append(validated_job)

        # Log summary
        invalid_count = sum(
            1 for job in validated_jobs if not job.__dict__.get("url_validated", True)
        )
        if invalid_count > 0:
            print(f"  ⚠ {invalid_count} job(s) with invalid URLs marked as stale")

        return validated_jobs

    def _deduplicate_jobs(
        self, jobs_with_methods: list[tuple[OpportunityData, str]]
    ) -> list[tuple[OpportunityData, str]]:
        """
        Deduplicate jobs by title + company combination

        When duplicates exist, prefer:
        1. Jobs with valid URLs over invalid URLs
        2. LLM extraction over regex (higher quality)
        3. First occurrence (if all else equal)

        Args:
            jobs_with_methods: List of (OpportunityData, extraction_method) tuples

        Returns:
            Deduplicated list of jobs
        """
        from collections import defaultdict

        # Group jobs by (title, company) key
        job_groups: dict[tuple[str, str], list[tuple[OpportunityData, str]]] = defaultdict(list)

        for job, method in jobs_with_methods:
            # Normalize title for deduplication (lowercase, strip whitespace)
            title_normalized = " ".join(job.title.lower().split())
            company_normalized = job.company.lower().strip()
            key = (title_normalized, company_normalized)
            job_groups[key].append((job, method))

        # For each group, pick the best job
        deduplicated = []
        for (_title, _company), group in job_groups.items():
            if len(group) == 1:
                # No duplicates, keep as-is
                deduplicated.append(group[0])
            else:
                # Multiple duplicates, pick the best one
                def job_score(item: tuple[OpportunityData, str]) -> tuple[int, int, int]:
                    job, method = item
                    # Score criteria (higher is better):
                    # 1. URL validity (1 if valid, 0 if invalid/missing)
                    has_valid_url = 1 if job.link and job.__dict__.get("url_validated", True) else 0
                    # 2. Extraction method (1 for LLM, 0 for regex)
                    is_llm = 1 if method == "llm" else 0
                    # 3. URL presence (1 if has URL, 0 if not)
                    has_url = 1 if job.link else 0
                    return (has_valid_url, is_llm, has_url)

                # Pick job with highest score
                best_job = max(group, key=job_score)
                deduplicated.append(best_job)

        return deduplicated

    def _is_likely_job_title(self, text: str) -> bool:
        """
        Check if text looks like a job title

        Args:
            text: Text to check

        Returns:
            True if likely a job title
        """
        # Filter out common non-job text
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

        # Check if it contains job-related keywords
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

    def _is_job_url(self, url: str) -> bool:
        """
        Check if URL looks like a job listing page

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a job listing page
        """
        url_lower = url.lower()

        # Strong job indicators (individual job pages or pagination)
        strong_indicators = [
            "/job/",  # /job/123, /job/engineer
            "/jobs/",  # /jobs/123
            "/positions/",  # /positions/engineering
            "/openings/",  # /openings/director
            "?page=",  # ?page=2
            "/page/",  # /page/2
            "/opportunities/",  # /opportunities/
            "-jobs",  # greenhouse.io uses company-name-jobs
        ]

        # Weak indicators (need additional validation)
        weak_indicators = [
            "/careers/",  # Could be guide pages or actual jobs
        ]

        # Check for strong indicators first
        has_strong_indicator = any(indicator in url_lower for indicator in strong_indicators)

        # For weak indicators, require additional job-related terms
        if not has_strong_indicator:
            has_weak_indicator = any(indicator in url_lower for indicator in weak_indicators)
            if has_weak_indicator:
                # Must also have job-related terms in path
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
                    "/en-us/",  # Workday locale indicators
                    "/en-ca/",
                    "/opening",
                    "/position",
                    "/role",
                ]
                has_strong_indicator = any(term in url_lower for term in job_terms)
            else:
                has_strong_indicator = False

        # Exclude common non-job pages
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
            "/guide",  # Candidate guides
            "/faq",
            "/benefits",
            "/culture",
            "/values",
            "/diversity",
            "/inclusion",
            "/location",  # Location pages
            "/office",
            "/team",
            "/search",  # Search pages
            "/filter",
        ]
        has_exclusion = any(pattern in url_lower for pattern in exclude_patterns)

        return has_strong_indicator and not has_exclusion

    def _discover_job_urls(self, careers_url: str, company_name: str) -> list[str]:
        """
        Discover all job listing URLs on careers site

        Uses two-tier approach:
        1. Try sitemap.xml parsing (FREE) - works for ~80% of sites
        2. Fall back to Firecrawl map (PAID ~$0.003) - remaining 20%

        Args:
            careers_url: URL to company's career page
            company_name: Company name for logging

        Returns:
            List of discovered job URLs (limited to 50 to avoid overwhelming)
        """
        if not self.enable_pagination:
            return []

        # Try 1: Free sitemap parsing
        logger.info(f"Attempting sitemap discovery for {company_name}")
        job_urls = self._parse_sitemap(careers_url)

        if job_urls:
            print(f"  ✓ Sitemap: Found {len(job_urls)} job URLs (free)")
            logger.info(f"Sitemap discovery found {len(job_urls)} URLs for {company_name}")
            return job_urls[:50]  # Limit to avoid cost/time explosion

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

    def _parse_sitemap(self, careers_url: str) -> list[str]:
        """
        Parse sitemap.xml to discover job URLs (FREE)

        Most career sites have sitemaps listing all pages:
        - Greenhouse: https://company.greenhouse.io/sitemap.xml
        - Lever: https://company.lever.co/sitemap.xml
        - Custom: https://company.com/sitemap.xml

        Args:
            careers_url: URL to careers page

        Returns:
            List of job URLs found in sitemap, or empty list if no sitemap
        """
        # Extract domain from careers URL
        parsed = urlparse(careers_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        # Try common sitemap locations
        sitemap_candidates = [
            urljoin(domain, "/sitemap.xml"),
            urljoin(domain, "/careers/sitemap.xml"),
            urljoin(domain, "/jobs/sitemap.xml"),
            careers_url.rstrip("/") + "/sitemap.xml",
        ]

        for sitemap_url in sitemap_candidates:
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
                    continue

                # Parse XML sitemap
                root = ET.fromstring(response.content)

                # Handle namespace (sitemaps use http://www.sitemaps.org/schemas/sitemap/0.9)
                ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

                # Extract <loc> tags (URLs)
                urls = []
                for loc in root.findall(".//ns:loc", ns):
                    if loc.text and self._is_job_url(loc.text):
                        urls.append(loc.text)

                # Also try without namespace (some sitemaps don't use it)
                if not urls:
                    for loc in root.findall(".//loc"):
                        if loc.text and self._is_job_url(loc.text):
                            urls.append(loc.text)

                if urls:
                    logger.info(f"Found {len(urls)} job URLs in {sitemap_url}")
                    return urls

            except ET.ParseError as e:
                logger.debug(f"Failed to parse sitemap {sitemap_url}: {e}")
                continue
            except requests.RequestException as e:
                logger.debug(f"Failed to fetch sitemap {sitemap_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error parsing {sitemap_url}: {e}")
                continue

        logger.debug("No sitemap found at any candidate location")
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
                map_result = self.firecrawl.map_url(
                    url=careers_url,
                    params={
                        "search": "job position career opening",
                        "limit": 100,  # Limit to avoid overwhelming
                    },
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
