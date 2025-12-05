"""
Job URL Validator - Validate job posting URLs before sending digest

Checks:
- HTTP status code (404 detection)
- Generic career page detection (Ashby, Lever)
- LinkedIn redirect detection (unverifiable but flagged)
"""

import logging

import requests

logger = logging.getLogger(__name__)


class JobValidator:
    """Validate job posting URLs"""

    def __init__(self, timeout: int = 5):
        """
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        Validate job URL is accessible and points to specific job posting

        Args:
            url: Job posting URL to validate

        Returns:
            (is_valid, reason) tuple

        Reasons:
            - "valid" - URL is accessible and valid
            - "404_not_found" - URL returns 404
            - "timeout" - Request timed out
            - "generic_career_page" - URL points to career page, not specific job
            - "linkedin_unverifiable" - LinkedIn requires login (cannot verify)
            - "connection_error" - Network connection failed
            - "invalid_response" - Unexpected HTTP status code
        """
        if not url:
            return (False, "empty_url")

        try:
            # HEAD request first (faster, no body download)
            response = self.session.head(url, allow_redirects=True, timeout=self.timeout)

            # Check for 404
            if response.status_code == 404:
                logger.warning(f"Job URL 404: {url}")
                return (False, "404_not_found")

            # LinkedIn redirects to login page - we can't verify these
            if "linkedin.com/login" in response.url or "linkedin.com/authwall" in response.url:
                logger.info(f"LinkedIn job (unverifiable): {url}")
                return (True, "linkedin_unverifiable")

            # Generic career page detection for Ashby
            # Valid: https://jobs.ashbyhq.com/company/uuid-format
            # Invalid: https://jobs.ashbyhq.com/company (no job ID)
            if "jobs.ashbyhq.com" in url:
                parts = url.split("/")
                # Should have at least: https://jobs.ashbyhq.com/company/job-id
                if len(parts) < 5:  # scheme, empty, domain, company, job-id
                    logger.warning(f"Generic Ashby URL: {url}")
                    return (False, "generic_career_page")

            # Generic career page detection for Lever
            # Valid: https://jobs.lever.co/company/uuid-format
            # Invalid: https://jobs.lever.co/company (no job ID)
            if "jobs.lever.co" in url:
                parts = url.split("/")
                if len(parts) < 5:
                    logger.warning(f"Generic Lever URL: {url}")
                    return (False, "generic_career_page")

            # Generic career page detection for Greenhouse
            # Valid: https://job-boards.greenhouse.io/company/jobs/12345
            # Invalid: https://job-boards.greenhouse.io/company
            if "greenhouse.io" in url and "/jobs/" not in url and "/job/" not in url:
                logger.warning(f"Generic Greenhouse URL: {url}")
                return (False, "generic_career_page")

            # Check for successful response
            if response.status_code == 200:
                return (True, "valid")

            # Check for redirects that might indicate moved/deleted jobs
            if response.status_code in (301, 302, 307, 308):
                # If redirect is to same domain, likely OK
                if response.url.split("/")[2] == url.split("/")[2]:
                    return (True, "valid")
                logger.warning(f"Job URL redirects to different domain: {url} -> {response.url}")
                return (False, "invalid_redirect")

            # Other status codes are suspicious
            logger.warning(f"Job URL returned {response.status_code}: {url}")
            return (False, "invalid_response")

        except requests.Timeout:
            logger.error(f"Job URL timeout: {url}")
            return (False, "timeout")
        except requests.ConnectionError:
            logger.error(f"Job URL connection error: {url}")
            return (False, "connection_error")
        except Exception as e:
            logger.error(f"Job URL validation error ({url}): {e}")
            return (False, "validation_error")

    def validate_batch(self, urls: list[str]) -> dict[str, tuple[bool, str]]:
        """
        Validate multiple job URLs

        Args:
            urls: List of job URLs

        Returns:
            Dictionary mapping url -> (is_valid, reason)
        """
        return {url: self.validate_url(url) for url in urls}

    def filter_valid_jobs(self, jobs: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filter jobs list into valid and invalid based on URL validation

        Args:
            jobs: List of job dictionaries with 'link' key

        Returns:
            (valid_jobs, invalid_jobs) tuple
        """
        valid_jobs = []
        invalid_jobs = []

        for job in jobs:
            url = job.get("link", "")
            is_valid, reason = self.validate_url(url)

            if is_valid:
                valid_jobs.append(job)
            else:
                # Add validation reason to job dict for logging
                job["validation_reason"] = reason
                invalid_jobs.append(job)

        return (valid_jobs, invalid_jobs)
