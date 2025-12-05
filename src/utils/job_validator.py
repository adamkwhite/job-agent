"""
Job URL Validator - Validate job posting URLs before sending digest

Checks:
- HTTP status code (404 detection)
- Generic career page detection (Ashby, Lever)
- LinkedIn redirect detection (unverifiable but flagged)
- 429 rate limit handling with exponential backoff retry
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)


class JobValidator:
    """Validate job posting URLs"""

    def __init__(self, timeout: int = 5, max_retries: int = 3, base_backoff: float = 2.0):
        """
        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts for 429 rate limits
            base_backoff: Base delay in seconds for exponential backoff (2^attempt * base)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

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
