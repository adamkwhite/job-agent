"""
Firecrawl-based career page scraper
Uses Firecrawl MCP to scrape JavaScript-heavy career pages
"""

import re

from models import OpportunityData


class FirecrawlCareerScraper:
    """Scrape career pages using Firecrawl MCP"""

    def __init__(self):
        self.name = "firecrawl_career_scraper"

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
            return jobs

        except Exception as e:
            print(f"  ✗ Error scraping page: {e}")
            return []

    def _firecrawl_scrape(self, url: str) -> dict | None:
        """
        Placeholder for Firecrawl MCP scraping

        Note: This cannot be called directly from Python scripts.
        Instead, use the manual scraping workflow:
        1. Run company_scraper.py to get list of companies
        2. Use Firecrawl MCP tool for each company manually or via Claude Code
        3. Pass results to process_scraped_jobs()

        Args:
            url: URL to scrape

        Returns:
            None (placeholder)
        """
        print("  ℹ️  Firecrawl scraping cannot be automated from Python")
        print("  → Manual workflow:")
        print("     1. Use Firecrawl MCP tool: mcp__firecrawl-mcp__firecrawl_scrape")
        print(f"     2. URL: {url}")
        print("     3. Formats: ['markdown']")
        print("     4. Process results via process_scraped_jobs()")
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
        # Example: "Senior Engineer\n\nToronto, Canada"
        pattern1 = re.compile(
            r"\[([\w\s,\-\(\)]+?)\s*(?:\\<br>\\<br>|\\n\\n|\n\n)(.+?)\]" r"\((https?://[^\)]+)\)",
            re.MULTILINE,
        )

        # Pattern 2: Job title in headers
        # Example: "## Senior Software Engineer"
        pattern2 = re.compile(r"^#{2,4}\s+(.+?)$", re.MULTILINE)

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
            # Look for job count indicators like "7 jobs"
            job_count_match = re.search(r"(\d+)\s+jobs?", markdown, re.IGNORECASE)

            if job_count_match:
                # Find all headers that might be job titles
                headers = pattern2.findall(markdown)

                for header in headers:
                    header = header.strip()

                    if self._is_likely_job_title(header) and len(header) > 10:
                        # Try to find location near this header
                        header_idx = markdown.find(header)
                        context = markdown[header_idx : header_idx + 200]

                        location_match = re.search(
                            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2,})", context
                        )
                        location = location_match.group(1) if location_match else ""

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
