"""
Career URL Parser - Extract career page URLs from job posting URLs

This module parses job posting URLs to derive the career page URL.
Supports major ATS platforms: Workday, Greenhouse, Lever, and generic patterns.

Examples:
    Workday:
        Input:  https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/12345
        Output: https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics

    Greenhouse:
        Input:  https://job-boards.greenhouse.io/figureai/jobs/4123456
        Output: https://job-boards.greenhouse.io/figureai

    Lever:
        Input:  https://jobs.lever.co/kuka/abc-123-xyz
        Output: https://jobs.lever.co/kuka
"""

import re
from urllib.parse import urlparse


class CareerURLParser:
    """
    Parse career page URLs from job posting URLs.

    This parser extracts base career page URLs from specific job posting URLs
    by recognizing patterns from major Applicant Tracking Systems (ATS).
    """

    # URL patterns for major ATS platforms
    # Each pattern captures the base career page URL before the job-specific path
    PATTERNS = {
        # Workday: https://company.wd1.myworkdayjobs.com/CompanyName/job/Location/JobID
        # Extract: https://company.wd1.myworkdayjobs.com/CompanyName
        "workday": r"(https?://[^/]+\.myworkdayjobs\.com/[^/]+)(?=/job/|$)",
        # Greenhouse: https://job-boards.greenhouse.io/company/jobs/12345 or https://boards.greenhouse.io/company/jobs/12345
        # Extract: https://job-boards.greenhouse.io/company or https://boards.greenhouse.io/company
        "greenhouse": r"(https?://(?:job-boards\.|boards\.)?greenhouse\.io/[^/]+)(?=/jobs?/|$)",
        # Lever: https://jobs.lever.co/company/abc-123-xyz
        # Extract: https://jobs.lever.co/company
        "lever": r"(https?://jobs\.lever\.co/[^/]+)(?=/[^/]+$|$)",
        # Ashby: https://jobs.ashbyhq.com/company/abc-123-xyz
        # Extract: https://jobs.ashbyhq.com/company
        "ashby": r"(https?://jobs\.ashbyhq\.com/[^/]+)(?=/[^/]+$|$)",
        # SmartRecruiters: https://jobs.smartrecruiters.com/Company/12345
        # Extract: https://jobs.smartrecruiters.com/Company
        "smartrecruiters": r"(https?://jobs\.smartrecruiters\.com/[^/]+)(?=/\d+|$)",
        # iCIMS: https://careers.company.com/jobs/12345 (often custom domain)
        # This is a generic fallback - might need manual verification
        "icims": r"(https?://[^/]+/jobs?)(?=/\d+|$)",
    }

    def parse(self, job_url: str) -> str | None:
        """
        Extract career page URL from a job posting URL.

        Args:
            job_url: Full URL of a specific job posting

        Returns:
            Career page base URL or None if pattern not recognized

        Examples:
            >>> parser = CareerURLParser()
            >>> parser.parse("https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/12345")
            'https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics'
        """
        if not job_url:
            return None

        # Normalize URL (remove fragments, trailing slashes)
        job_url = job_url.split("#")[0].rstrip("/")

        # Try each pattern in order
        for _platform_name, pattern in self.PATTERNS.items():
            match = re.search(pattern, job_url, re.IGNORECASE)
            if match:
                career_url = match.group(1)
                # Validate the extracted URL
                if self._is_valid_url(career_url):
                    return career_url

        # No pattern matched - try generic fallback
        return self._generic_fallback(job_url)

    def _is_valid_url(self, url: str) -> bool:
        """
        Validate that extracted URL is well-formed.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    def _generic_fallback(self, job_url: str) -> str | None:
        """
        Generic fallback for unrecognized URLs.

        Attempts to extract base URL by removing job-specific paths like:
        - /job/12345
        - /jobs/12345
        - /careers/12345
        - /posting/12345

        Args:
            job_url: Full job posting URL

        Returns:
            Base career page URL or None
        """
        # Try to remove common job-specific path patterns
        generic_patterns = [
            r"(/jobs?/[^/]+(?:/[^/]+)*)",  # /job/12345 or /jobs/12345/details
            r"(/careers?/[^/]+(?:/[^/]+)*)",  # /career/12345 or /careers/12345/apply
            r"(/posting/[^/]+(?:/[^/]+)*)",  # /posting/12345
            r"(/openings?/[^/]+(?:/[^/]+)*)",  # /opening/12345
        ]

        for pattern in generic_patterns:
            # Try to remove the job-specific path
            career_url = re.sub(pattern, "", job_url)
            if career_url != job_url and self._is_valid_url(career_url):
                # Ensure we end with /jobs or /careers
                if not career_url.endswith(("/jobs", "/careers")):
                    # Add /jobs if the URL doesn't already have a careers path
                    career_url = career_url.rstrip("/") + "/jobs"
                return career_url

        # Last resort: return domain + /jobs (but only if URL is valid)
        try:
            parsed = urlparse(job_url)
            # Check that we have both scheme and netloc (valid URL structure)
            if parsed.scheme and parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                return f"{base_url}/jobs"
            # Invalid URL structure - return None
            return None
        except Exception:
            return None

    def validate_url(self, url: str, timeout: int = 5) -> bool:
        """
        Validate that a career URL is accessible.

        This method performs a HEAD request to check if the URL returns a 200 status.
        Note: This is optional and should be used sparingly to avoid rate limiting.

        Args:
            url: Career page URL to validate
            timeout: Request timeout in seconds (default: 5)

        Returns:
            True if URL is accessible (HTTP 200), False otherwise
        """
        import requests

        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False

    def parse_batch(self, job_urls: list[str]) -> dict[str, str | None]:
        """
        Parse multiple job URLs at once.

        Args:
            job_urls: List of job posting URLs

        Returns:
            Dictionary mapping job_url -> career_url (or None if unparseable)

        Examples:
            >>> parser = CareerURLParser()
            >>> urls = [
            ...     "https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/12345",
            ...     "https://job-boards.greenhouse.io/figureai/jobs/4123456"
            ... ]
            >>> parser.parse_batch(urls)
            {
                'https://bostondynamics.wd1.myworkdayjobs.com/...': 'https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics',
                'https://job-boards.greenhouse.io/figureai/jobs/4123456': 'https://job-boards.greenhouse.io/figureai'
            }
        """
        return {job_url: self.parse(job_url) for job_url in job_urls}
