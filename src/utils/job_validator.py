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

# ATS platforms requiring a minimum number of URL path segments to be specific
_ATS_MIN_PARTS: dict[str, int] = {
    "jobs.ashbyhq.com": 5,
    "jobs.lever.co": 5,
    "careers.smartrecruiters.com": 5,
    "jobs.smartrecruiters.com": 5,
}


def _is_ats_generic_url(url: str, url_clean: str) -> bool:
    """Check if URL matches a known ATS domain but lacks enough path segments."""
    for domain, min_parts in _ATS_MIN_PARTS.items():
        if domain in url:
            parts = url_clean.split("/")
            if len(parts) < min_parts:
                logger.info(f"Generic {domain} URL (flagged for review): {url}")
                return True
    return False


def _is_keyword_generic_url(url: str, url_clean: str) -> bool:
    """Check for Greenhouse/Workday patterns and catch-all career paths."""
    if "greenhouse.io" in url and "/jobs/" not in url and "/job/" not in url:
        logger.info(f"Generic Greenhouse URL (flagged for review): {url}")
        return True

    if "myworkdayjobs.com" in url and "/job/" not in url:
        logger.info(f"Generic Workday URL (flagged for review): {url}")
        return True

    if url_clean.endswith("/careers") or url_clean.endswith("/jobs"):
        logger.info(f"Generic career path (flagged for review): {url}")
        return True

    return False


def _is_generic_career_subdomain(url_clean: str) -> bool:
    """Check for subdomain-only career/jobs sites with no path."""
    if url_clean.startswith("https://jobs.") or url_clean.startswith("https://careers."):
        parts = url_clean.split("/")
        if len(parts) <= 3:
            logger.info(f"Generic career subdomain (flagged for review): {url_clean}")
            return True
    return False


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
                    logger.debug(f"Job appears stale ('{indicator}'): {url}")
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
        check_areas = self._find_linkedin_check_areas(soup)

        # Check each high-signal area
        for area in check_areas:
            if not area:
                continue

            area_text = area.get_text().lower()

            for indicator in self.STALENESS_INDICATORS:
                if indicator in area_text:
                    logger.debug(
                        f"LinkedIn job appears stale in {area.name} "
                        f"(class={area.get('class')}, matched: '{indicator}')"
                    )
                    return (True, indicator)

        return (False, None)

    @staticmethod
    def _find_linkedin_check_areas(soup: BeautifulSoup) -> list:
        """Build list of high-signal HTML areas to check for LinkedIn staleness."""
        from bs4 import Tag

        check_areas: list = []

        # 1. Alert/banner messages (highest signal)
        alerts = soup.find_all(
            ["div", "section"],
            class_=lambda c: (
                c and any(x in c.lower() for x in ["alert", "banner", "message", "notice"])
            ),
        )
        check_areas.extend(alerts)

        # 2. Job header/title area
        job_header = soup.find("h1") or soup.find("h2", class_=lambda c: c and "job" in c.lower())
        if job_header:
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
            check_areas.append(main_content)

        return check_areas

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

        # Step 1: URL pattern-based detection (no HTTP request needed)
        career_page_result = self._check_generic_career_page(url)
        if career_page_result is not None:
            return career_page_result

        # Step 2: HTTP-based validation with retry logic
        result = self._make_http_request_with_retries(url)
        if isinstance(result, tuple):
            return result  # Error tuple from request failure

        # Step 3: Classify the HTTP response
        return self._classify_http_response(url, result)

    @staticmethod
    def _check_generic_career_page(url: str) -> tuple[bool, str, bool] | None:
        """
        Check if URL is a generic career page (ATS pattern detection).

        Returns:
            (is_valid, reason, needs_review) tuple if generic page detected,
            None if URL should proceed to HTTP validation.
        """
        generic_result = (True, "generic_career_page", True)
        url_clean = url.rstrip("/")

        if _is_ats_generic_url(url, url_clean):
            return generic_result

        if _is_keyword_generic_url(url, url_clean):
            return generic_result

        if _is_generic_career_subdomain(url_clean):
            return generic_result

        return None

    def _make_http_request_with_retries(
        self, url: str
    ) -> "requests.Response | tuple[bool, str, bool]":
        """
        Make HEAD request with exponential backoff retry on 429.

        Returns:
            Response object on success, or error tuple on failure.
        """
        response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.head(url, allow_redirects=True, timeout=self.timeout)

                if response.status_code != 429:
                    return response

                if attempt < self.max_retries:
                    delay = self.base_backoff * (2**attempt)
                    logger.info(
                        f"Rate limited (429) on attempt {attempt + 1}/{self.max_retries + 1} "
                        f"for {url}, retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue

                logger.warning(
                    f"Rate limited (429) after {self.max_retries + 1} attempts: {url} "
                    f"(assuming valid, flagging for review)"
                )
                return (True, "rate_limited_assumed_valid", True)

            except requests.Timeout:
                logger.error(f"Job URL timeout: {url}")
                return (False, "timeout", False)
            except requests.ConnectionError:
                logger.error(f"Job URL connection error: {url}")
                return (False, "connection_error", False)
            except Exception as e:
                logger.error(f"Job URL validation error ({url}): {e}")
                return (False, "validation_error", False)

        # Should not reach here, but satisfy type checker
        assert response is not None  # noqa: S101
        return response

    def _classify_http_response(
        self, url: str, response: "requests.Response"
    ) -> tuple[bool, str, bool]:
        """
        Classify an HTTP response into a validation result.

        Handles 404, LinkedIn redirects, 200 (with optional staleness check),
        same-domain redirects, and unexpected status codes.
        """
        if response.status_code == 404:
            logger.warning(f"Job URL 404: {url}")
            return (False, "404_not_found", False)

        if "linkedin.com/login" in response.url or "linkedin.com/authwall" in response.url:
            logger.info(f"LinkedIn job (unverifiable): {url}")
            return (True, "linkedin_unverifiable", True)

        if response.status_code == 200:
            return self._classify_success_response(url)

        if response.status_code in (301, 302, 307, 308):
            if response.url.split("/")[2] == url.split("/")[2]:
                return (True, "valid", False)
            logger.warning(f"Job URL redirects to different domain: {url} -> {response.url}")
            return (False, "invalid_redirect", False)

        logger.warning(f"Job URL returned {response.status_code}: {url}")
        return (False, "invalid_response", False)

    def _classify_success_response(self, url: str) -> tuple[bool, str, bool]:
        """Check page content for staleness on a 200 response."""
        if self.check_content:
            is_stale, matched_phrase = self._check_content_for_staleness(url)
            if is_stale and matched_phrase:
                logger.debug(f"Job appears stale: {url} (matched: '{matched_phrase}')")
                return (False, f"stale_{matched_phrase.replace(' ', '_')}", False)
        return (True, "valid", False)

    def validate_batch(self, urls: list[str]) -> dict[str, tuple[bool, str, bool]]:
        """
        Validate multiple job URLs

        Args:
            urls: List of job URLs

        Returns:
            Dictionary mapping url -> (is_valid, reason, needs_review)
        """
        return {url: self.validate_url(url) for url in urls}

    def filter_valid_jobs(
        self, jobs: list[dict], show_progress: bool = True
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """
        Filter jobs list into valid, invalid, and needs-review based on URL validation

        Args:
            jobs: List of job dictionaries with 'link' key
            show_progress: Whether to print progress indicators (default: True)

        Returns:
            (valid_jobs, flagged_jobs, invalid_jobs) tuple
            - valid_jobs: Jobs with verified URLs
            - flagged_jobs: Jobs that need manual review (generic URLs, LinkedIn, etc.)
            - invalid_jobs: Jobs with broken URLs (404, timeout, etc.)
        """
        valid_jobs: list[dict] = []
        flagged_jobs: list[dict] = []
        invalid_jobs: list[dict] = []
        total = len(jobs)

        for idx, job in enumerate(jobs, 1):
            url = job.get("link", "")
            is_valid, reason, needs_review = self.validate_url(url)
            self._categorize_validation_result(
                job,
                is_valid,
                reason,
                needs_review,
                valid_jobs,
                flagged_jobs,
                invalid_jobs,
                idx,
                total,
                show_progress,
            )

        return (valid_jobs, flagged_jobs, invalid_jobs)

    @staticmethod
    def _categorize_validation_result(
        job: dict,
        is_valid: bool,
        reason: str,
        needs_review: bool,
        valid_jobs: list[dict],
        flagged_jobs: list[dict],
        invalid_jobs: list[dict],
        idx: int,
        total: int,
        show_progress: bool,
    ) -> None:
        """Categorize a single job's validation result and optionally print progress."""
        if show_progress:
            company = job.get("company", "Unknown")[:20]
            title = job.get("title", "Unknown")[:30]
            print(f"  [{idx}/{total}] {company} - {title}...", end="", flush=True)

        job["validation_reason"] = reason
        job["needs_review"] = needs_review

        if not is_valid:
            invalid_jobs.append(job)
            if show_progress:
                status_emoji = "⛔" if reason.startswith("stale") else "❌"
                print(f" {status_emoji} {reason}")
        elif needs_review:
            flagged_jobs.append(job)
            if show_progress:
                print(f" ⚠️  {reason}")
        else:
            valid_jobs.append(job)
            if show_progress:
                print(" ✓")

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
        age_result = self._check_job_age(job)
        if age_result is not None:
            return age_result

        # Check 2: URL validation (with caching)
        url = job.get("link", "")
        if not url:
            return (False, "missing_url")

        return self._check_url_with_cache(url, use_cache)

    def _check_job_age(self, job: dict) -> tuple[bool, str | None] | None:
        """
        Check if job is too old based on received_at timestamp.

        Returns:
            (False, "stale_job_age") if too old, None to continue validation.
        """
        received_at = job.get("received_at")
        if not received_at:
            return None

        try:
            if isinstance(received_at, str):
                received_date = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            else:
                received_date = received_at

            age_days = (datetime.now(received_date.tzinfo) - received_date).days

            if age_days > self.age_threshold_days:
                logger.info(
                    f"Job too old ({age_days} days, threshold: {self.age_threshold_days}): "
                    f"{job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"
                )
                return (False, "stale_job_age")

        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse received_at date: {received_at} ({e})")

        return None

    def _check_url_with_cache(self, url: str, use_cache: bool) -> tuple[bool, str | None]:
        """Validate URL with optional caching of results."""
        # Check cache first
        if use_cache and url in self._validation_cache:
            is_valid, reason, _needs_review = self._validation_cache[url]
            if not is_valid and reason.startswith("stale"):
                return (False, reason)
            return (is_valid, None if is_valid else reason)

        # Not in cache, validate and cache result
        is_valid, reason, needs_review = self.validate_url(url)

        if use_cache:
            self._validation_cache[url] = (is_valid, reason, needs_review)

        if not is_valid:
            return (False, reason)

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
