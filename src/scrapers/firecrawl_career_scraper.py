"""
Firecrawl-based career page scraper
Uses Firecrawl API to scrape JavaScript-heavy career pages
"""

import os
import re
import time

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from models import OpportunityData

load_dotenv()


class FirecrawlCareerScraper:
    """Scrape career pages using Firecrawl API with rate limiting"""

    def __init__(self, requests_per_minute: int = 9):
        """
        Initialize scraper with rate limiting

        Args:
            requests_per_minute: Max requests per minute (default 9 to stay under 10/min limit)
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

    def scrape_jobs(self, careers_url: str, company_name: str) -> list[OpportunityData]:
        """
        Scrape jobs from a career page using Firecrawl

        Args:
            careers_url: URL to company's career page
            company_name: Name of the company

        Returns:
            List of OpportunityData objects
        """
        print(f"\nScraping jobs from: {careers_url}")
        print("Using Firecrawl MCP...")

        try:
            # Use Firecrawl to scrape the page
            result = self._firecrawl_scrape(careers_url)

            if not result:
                print("  ✗ Failed to scrape page")
                return []

            markdown = result.get("markdown", "")

            # Extract jobs from markdown
            jobs = self._extract_jobs_from_markdown(markdown, careers_url, company_name)

            print(f"  ✓ Found {len(jobs)} job listings")

            # Show job titles and links for user visibility
            if jobs:
                for i, job in enumerate(jobs, 1):
                    print(f"    {i}. {job.title}")
                    if job.link:
                        print(f"       Link: {job.link}")

            return jobs

        except Exception as e:
            print(f"  ✗ Error scraping page: {e}")
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
        Scrape a URL using Firecrawl API with rate limiting

        Args:
            url: URL to scrape

        Returns:
            Dictionary with 'markdown' key containing scraped content, or None on error
        """
        try:
            # Wait if necessary to respect rate limits
            self._wait_for_rate_limit()

            # Make the API request
            document = self.firecrawl.scrape(url, formats=["markdown"])
            # Convert Document object to dict for compatibility
            return {"markdown": document.markdown if document.markdown else ""}
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
