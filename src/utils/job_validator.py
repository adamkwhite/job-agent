"""
Job URL Validator - Validate job posting URLs before sending digest

Checks:
- Job age (>60 days = potentially stale)
- HTTP status code (404 detection)
- Generic career page detection (Ashby, Lever)
- LinkedIn redirect detection (unverifiable but flagged)
- Content-based staleness detection (closure messages)
- 429 rate limit handling with exponential backoff retry
"""

import logging
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobValidator:
    """Validate job posting URLs"""

    # Phrases that indicate a job posting is no longer accepting applications
    STALENESS_INDICATORS = [
        "no longer accepting applications",
        "no longer accepting",
        "applications are closed",
        "this job is closed",
        "position has been filled",
        "this position is no longer available",
        "job posting expired",
        "this posting has expired",
        "posting is no longer active",
        "this job is no longer available",
    ]

    def __init__(
        self,
        timeout: int = 5,
        max_retries: int = 3,
        base_backoff: float = 2.0,
        check_content: bool = True,
        age_threshold_days: int = 60,
    ):
        """
        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts for 429 rate limits
            base_backoff: Base delay in seconds for exponential backoff (2^attempt * base)
            check_content: Whether to fetch and check page content for staleness (slower)
            age_threshold_days: Jobs older than this many days are considered potentially stale
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.check_content = check_content
        self.age_threshold_days = age_threshold_days
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        # Cache for URL validation results (url -> (is_valid, reason, needs_review))
        self._validation_cache: dict[str, tuple[bool, str, bool]] = {}

    def _check_content_for_staleness(self, url: str) -> tuple[bool, str | None]:
        """
        Fetch page content and check for staleness indicators

        Args:
            url: Job posting URL

        Returns:
            (is_stale, matched_phrase) tuple
        """
        try:
            # GET request to fetch full content
            response = self.session.get(url, allow_redirects=True, timeout=self.timeout)

            if response.status_code != 200:
                return (False, None)  # Can't determine from content

            # Parse HTML and extract text
            soup = BeautifulSoup(response.text, "html.parser")

            # LinkedIn-specific context-aware detection
            if "linkedin.com" in url:
                return self._check_linkedin_staleness(soup)

            # Generic staleness check for other platforms
            page_text = soup.get_text().lower()

            # Check for staleness indicators
            for indicator in self.STALENESS_INDICATORS:
                if indicator in page_text:
                    logger.info(f"Job appears stale ('{indicator}'): {url}")
                    return (True, indicator)

            return (False, None)

        except Exception as e:
            logger.debug(f"Could not check content for staleness ({url}): {e}")
            return (False, None)  # Assume not stale if can't verify

    def _check_linkedin_staleness(self, soup: BeautifulSoup) -> tuple[bool, str | None]:
        """
        LinkedIn-specific staleness detection using high-signal page areas

        LinkedIn shows staleness in specific UI elements, not scattered throughout.
        Check only these high-confidence areas to avoid false positives from
        recommendations, footer links, or related jobs sections.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            (is_stale, matched_phrase) tuple
        """
        from bs4 import Tag

        # High-signal areas to check (in priority order)
        check_areas: list = []

        # 1. Alert/banner messages (highest signal)
        alerts = soup.find_all(
            ["div", "section"],
            class_=lambda c: c
            and any(x in c.lower() for x in ["alert", "banner", "message", "notice"]),
        )
        check_areas.extend(alerts)

        # 2. Job header/title area
        job_header = soup.find("h1") or soup.find("h2", class_=lambda c: c and "job" in c.lower())
        if job_header:
            # Check parent container for status messages
            header_container = job_header.find_parent(["div", "section", "header"])
            if header_container and isinstance(header_container, Tag):
                check_areas.append(header_container)

        # 3. Application button area
        apply_sections = soup.find_all(
            ["div", "section", "button"],
            class_=lambda c: c and any(x in c.lower() for x in ["apply", "application"]),
        )
        check_areas.extend(apply_sections)

        # 4. Main content area (but not entire page)
        main_content = soup.find("main") or soup.find("div", {"role": "main"})
        if main_content and isinstance(main_content, Tag):
            # Only check direct text in main, not nested elements
            check_areas.append(main_content)

        # Check each high-signal area
        for area in check_areas:
            if not area:
                continue

            area_text = area.get_text().lower()

            # Check for staleness indicators
            for indicator in self.STALENESS_INDICATORS:
                if indicator in area_text:
                    logger.info(
                        f"LinkedIn job appears stale in {area.name} "
                        f"(class={area.get('class')}, matched: '{indicator}')"
                    )
                    return (True, indicator)

        return (False, None)

    def validate_url(self, url: str) -> tuple[bool, str, bool]:
        """
        Validate job URL is accessible and points to specific job posting

        Args:
            url: Job posting URL to validate

        Returns:
            (is_valid, reason, needs_review) tuple

        Validation States:
            - (True, "valid", False) - URL is accessible and valid
            - (False, "404_not_found", False) - URL returns 404, reject
            - (False, "stale_*", False) - Job no longer accepting applications, reject
            - (False, "timeout", False) - Request timed out, reject
            - (True, "generic_career_page", True) - Career page URL, flag for review
            - (True, "linkedin_unverifiable", True) - LinkedIn requires login, flag for review
            - (True, "rate_limited_assumed_valid", True) - 429 after retries, flag for review
            - (False, "connection_error", False) - Network failed, reject
            - (False, "invalid_response", False) - Unexpected status, reject
        """
        if not url:
            return (False, "empty_url", False)

        # Retry logic for rate limiting (429)
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                # HEAD request first (faster, no body download)
                response = self.session.head(url, allow_redirects=True, timeout=self.timeout)

                # Handle 429 rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < self.max_retries:
                        # Calculate exponential backoff: 2s, 4s, 8s...
                        delay = self.base_backoff * (2**attempt)
                        logger.info(
                            f"Rate limited (429) on attempt {attempt + 1}/{self.max_retries + 1} "
                            f"for {url}, retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        continue  # Retry
                    else:
                        # Max retries reached, assume valid but flag for review
                        logger.warning(
                            f"Rate limited (429) after {self.max_retries + 1} attempts: {url} "
                            f"(assuming valid, flagging for review)"
                        )
                        return (True, "rate_limited_assumed_valid", True)

                # If we got here, we have a non-429 response, break retry loop
                break

            except requests.Timeout:
                logger.error(f"Job URL timeout: {url}")
                return (False, "timeout", False)
            except requests.ConnectionError:
                logger.error(f"Job URL connection error: {url}")
                return (False, "connection_error", False)
            except Exception as e:
                logger.error(f"Job URL validation error ({url}): {e}")
                return (False, "validation_error", False)

        # Process the response (only reached if not 429 or retries exhausted)
        # Check for 404
        if response.status_code == 404:
            logger.warning(f"Job URL 404: {url}")
            return (False, "404_not_found", False)

        # LinkedIn redirects to login page - we can't verify these, flag for review
        if "linkedin.com/login" in response.url or "linkedin.com/authwall" in response.url:
            logger.info(f"LinkedIn job (unverifiable): {url}")
            return (True, "linkedin_unverifiable", True)

        # Generic career page detection for Ashby
        # These might have jobs listed, but we can't verify specific postings
        # Flag for review rather than reject
        if "jobs.ashbyhq.com" in url:
            parts = url.split("/")
            # Should have at least: https://jobs.ashbyhq.com/company/job-id
            if len(parts) < 5:  # scheme, empty, domain, company, job-id
                logger.info(f"Generic Ashby URL (flagged for review): {url}")
                return (True, "generic_career_page", True)

        # Generic career page detection for Lever
        # Flag for review rather than reject
        if "jobs.lever.co" in url:
            parts = url.split("/")
            if len(parts) < 5:
                logger.info(f"Generic Lever URL (flagged for review): {url}")
                return (True, "generic_career_page", True)

        # Generic career page detection for Greenhouse
        # Flag for review rather than reject
        if "greenhouse.io" in url and "/jobs/" not in url and "/job/" not in url:
            logger.info(f"Generic Greenhouse URL (flagged for review): {url}")
            return (True, "generic_career_page", True)

        # Check for successful response
        if response.status_code == 200:
            # Check page content for staleness indicators (if enabled)
            if self.check_content:
                is_stale, matched_phrase = self._check_content_for_staleness(url)
                if is_stale and matched_phrase:
                    logger.warning(f"Job appears stale: {url} (matched: '{matched_phrase}')")
                    return (False, f"stale_{matched_phrase.replace(' ', '_')}", False)

            return (True, "valid", False)

        # Check for redirects that might indicate moved/deleted jobs
        if response.status_code in (301, 302, 307, 308):
            # If redirect is to same domain, likely OK
            if response.url.split("/")[2] == url.split("/")[2]:
                return (True, "valid", False)
            logger.warning(f"Job URL redirects to different domain: {url} -> {response.url}")
            return (False, "invalid_redirect", False)

        # Other status codes are suspicious
        logger.warning(f"Job URL returned {response.status_code}: {url}")
        return (False, "invalid_response", False)

    def validate_batch(self, urls: list[str]) -> dict[str, tuple[bool, str, bool]]:
        """
        Validate multiple job URLs

        Args:
            urls: List of job URLs

        Returns:
            Dictionary mapping url -> (is_valid, reason, needs_review)
        """
        return {url: self.validate_url(url) for url in urls}

    def filter_valid_jobs(self, jobs: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
        """
        Filter jobs list into valid, invalid, and needs-review based on URL validation

        Args:
            jobs: List of job dictionaries with 'link' key

        Returns:
            (valid_jobs, flagged_jobs, invalid_jobs) tuple
            - valid_jobs: Jobs with verified URLs
            - flagged_jobs: Jobs that need manual review (generic URLs, LinkedIn, etc.)
            - invalid_jobs: Jobs with broken URLs (404, timeout, etc.)
        """
        valid_jobs = []
        flagged_jobs = []
        invalid_jobs = []

        for job in jobs:
            url = job.get("link", "")
            is_valid, reason, needs_review = self.validate_url(url)

            # Add validation metadata to job
            job["validation_reason"] = reason
            job["needs_review"] = needs_review

            if not is_valid:
                invalid_jobs.append(job)
            elif needs_review:
                flagged_jobs.append(job)
            else:
                valid_jobs.append(job)

        return (valid_jobs, flagged_jobs, invalid_jobs)

    def validate_for_digest(self, job: dict, use_cache: bool = True) -> tuple[bool, str | None]:
        """
        Validate job is fresh and URL is accessible before adding to digest.

        Combines age checking and URL validation with caching for performance.

        Args:
            job: Job dict with 'received_at' and 'link' fields
            use_cache: Whether to use cached URL validation results (default: True)

        Returns:
            (is_valid, stale_reason) tuple:
                - (True, None) = Fresh job, ready for digest
                - (False, "stale_job_age") = Job too old (>threshold days)
                - (False, "stale_*") = Job URL closed/invalid
                - (False, "url_validation_failed") = URL check failed

        Examples:
            >>> validator = JobValidator(age_threshold_days=60)
            >>> job = {"received_at": "2024-01-01", "link": "https://..."}
            >>> is_valid, reason = validator.validate_for_digest(job)
            >>> if not is_valid:
            ...     print(f"Job rejected: {reason}")
        """
        # Check 1: Job age
        received_at = job.get("received_at")
        if received_at:
            try:
                # Parse timestamp (supports ISO format)
                if isinstance(received_at, str):
                    received_date = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                else:
                    received_date = received_at

                # Calculate age
                age_days = (datetime.now(received_date.tzinfo) - received_date).days

                if age_days > self.age_threshold_days:
                    logger.info(
                        f"Job too old ({age_days} days, threshold: {self.age_threshold_days}): "
                        f"{job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"
                    )
                    return (False, "stale_job_age")

            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse received_at date: {received_at} ({e})")
                # Don't filter on parse error, just log and continue to URL check

        # Check 2: URL validation (with caching)
        url = job.get("link", "")
        if not url:
            return (False, "missing_url")

        # Check cache first
        if use_cache and url in self._validation_cache:
            is_valid, reason, _needs_review = self._validation_cache[url]
            if not is_valid and reason.startswith("stale"):
                return (False, reason)
            return (is_valid, None if is_valid else reason)

        # Not in cache, validate and cache result
        is_valid, reason, needs_review = self.validate_url(url)

        # Store in cache
        if use_cache:
            self._validation_cache[url] = (is_valid, reason, needs_review)

        # Return result
        if not is_valid:
            # Job URL is invalid/stale
            return (False, reason)

        # URL is valid (may need review, but not filtered)
        return (True, None)

    def clear_cache(self) -> None:
        """Clear the URL validation cache"""
        self._validation_cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring"""
        return {
            "total_cached": len(self._validation_cache),
            "valid_count": sum(1 for v, _, _ in self._validation_cache.values() if v),
            "invalid_count": sum(1 for v, _, _ in self._validation_cache.values() if not v),
        }
