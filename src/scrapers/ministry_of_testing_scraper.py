"""
Ministry of Testing Job Board Scraper

Scrapes QA/testing jobs from ministryoftesting.com/jobs
Targets: Senior/Lead QA, Test Automation, SDET, Quality roles
Primary beneficiary: Mario's profile (QA/testing focus)
"""

import re
from datetime import datetime

from models import OpportunityData


class MinistryOfTestingScraper:
    """Scraper for Ministry of Testing job board"""

    BASE_URL = "https://www.ministryoftesting.com/jobs"

    def __init__(self):
        """Initialize scraper"""
        pass

    def parse_jobs_from_page(
        self,
        markdown: str,
        target_locations: list[str] | None = None,
    ) -> list[OpportunityData]:
        """
        Parse jobs from a single page of Ministry of Testing markdown

        Args:
            markdown: Page markdown from Firecrawl
            target_locations: List of locations to filter (e.g., ["Canada", "Remote", "Toronto"])

        Returns:
            List of OpportunityData objects
        """
        if target_locations is None:
            target_locations = ["Canada", "Remote", "United States"]

        return self._parse_jobs_from_markdown(markdown, target_locations)

    def _parse_jobs_from_markdown(
        self, markdown: str, target_locations: list[str]
    ) -> list[OpportunityData]:
        """
        Parse jobs from Ministry of Testing markdown

        Expected format:
        [Job Title](https://www.ministryoftesting.com/jobs/job-slug)
        Location
        Date

        Args:
            markdown: Page markdown from Firecrawl
            target_locations: Locations to filter for

        Returns:
            List of OpportunityData
        """
        jobs = []

        # Split into job blocks (each starts with a job title link)
        # Pattern: [Title](URL)\n\nLocation\n\nDate
        job_pattern = r"\[([^\]]+)\]\((https://www\.ministryoftesting\.com/jobs/[^\)]+)\)\n\n([^\n]+)\n\n(\d{1,2}\s+\w+)"

        matches = re.finditer(job_pattern, markdown)

        for match in matches:
            title = match.group(1).strip()
            link = match.group(2).strip()
            location = match.group(3).strip()
            date_str = match.group(4).strip()

            # Filter by location
            if not self._matches_location(location, target_locations):
                continue

            # Parse date (e.g., "16 Jan", "13 Jan")
            posted_date = self._parse_date(date_str)

            # Extract company from title if present (some jobs have "Company - Title" format)
            company = self._extract_company(title, location)

            jobs.append(
                OpportunityData(
                    source="ministry_of_testing",
                    source_email="ministry_of_testing_scraper",
                    type="direct_job",
                    company=company,
                    title=title,
                    location=location,
                    link=link,
                    posted_date=posted_date,
                    needs_research=False,
                )
            )

        return jobs

    def _matches_location(self, location: str, target_locations: list[str]) -> bool:
        """
        Check if job location matches target locations

        Args:
            location: Job location string (e.g., "Toronto, Ontario", "United States", "Remote")
            target_locations: List of acceptable locations

        Returns:
            True if location matches any target
        """
        location_lower = location.lower()

        # Province/state → country mapping
        province_country_map = {
            # Canadian provinces
            "ontario": "canada",
            "quebec": "canada",
            "british columbia": "canada",
            "bc": "canada",
            "alberta": "canada",
            "manitoba": "canada",
            "saskatchewan": "canada",
            "nova scotia": "canada",
            "new brunswick": "canada",
            "newfoundland": "canada",
            "prince edward island": "canada",
            "pei": "canada",
            # UK regions
            "england": "united kingdom",
            "scotland": "united kingdom",
            "wales": "united kingdom",
            "northern ireland": "united kingdom",
        }

        for target in target_locations:
            target_lower = target.lower()

            # Exact match or contains
            if target_lower in location_lower:
                return True

            # Handle "remote" specially (matches "Remote", "CA (Remote)", etc.)
            if target_lower == "remote" and "remote" in location_lower:
                return True

            # Check province/state mapping (e.g., "Ontario" → "Canada")
            if target_lower in province_country_map.values():
                # Target is a country, check if location contains a province/state
                for province, country in province_country_map.items():
                    if country == target_lower and province in location_lower:
                        return True

        return False

    def _parse_date(self, date_str: str) -> str:
        """
        Parse relative date from Ministry of Testing format

        Args:
            date_str: Date string like "16 Jan", "13 Jan"

        Returns:
            ISO format date string (YYYY-MM-DD)
        """
        try:
            # Parse "DD Mon" format (assumes current year)
            current_year = datetime.now().year
            date_with_year = f"{date_str} {current_year}"

            parsed_date = datetime.strptime(date_with_year, "%d %b %Y")

            # If parsed date is in the future, it's from last year
            if parsed_date > datetime.now():
                parsed_date = parsed_date.replace(year=current_year - 1)

            return parsed_date.strftime("%Y-%m-%d")

        except Exception:
            # Fallback to today's date
            return datetime.now().strftime("%Y-%m-%d")

    def _extract_company(self, title: str, location: str) -> str:
        """
        Extract company name from job title or location

        Some jobs have format: "Company - Job Title"
        Otherwise, use "Unknown" or extract from location if possible

        Args:
            title: Job title
            location: Job location

        Returns:
            Company name
        """
        # Check for "Company - Title" format
        if " - " in title:
            parts = title.split(" - ", 1)
            if len(parts[0]) < 50:  # Reasonable company name length
                return parts[0].strip()

        # Common city names that should NOT be extracted as companies
        common_cities = {
            # US cities
            "Austin",
            "San Francisco",
            "Los Angeles",
            "New York",
            "Seattle",
            "Portland",
            "Boston",
            "Chicago",
            "Denver",
            "Atlanta",
            "Phoenix",
            "San Diego",
            "Dallas",
            "Houston",
            "Philadelphia",
            "Washington",
            "Miami",
            "Minneapolis",
            "Detroit",
            "Nashville",
            "Charlotte",
            "San Jose",
            "Jacksonville",
            "Indianapolis",
            "Columbus",
            "Fort Worth",
            "North Carolina",
            "South Carolina",
            # Canadian cities
            "Toronto",
            "Montreal",
            "Vancouver",
            "Ottawa",
            "Calgary",
            "Edmonton",
            "Quebec",
            "Winnipeg",
            "Hamilton",
            "Kitchener",
            "London",
            "Victoria",
            "Halifax",
            "Saskatoon",
            "Regina",
            "Mississauga",
            "Brampton",
            "Markham",
            "Vaughan",
            "Richmond Hill",
            # UK cities
            "Birmingham",
            "Manchester",
            "Leeds",
            "Liverpool",
            "Newcastle",
            "Sheffield",
            "Bristol",
            "Leicester",
            "Coventry",
            "Bradford",
            "Northampton",
            "Knutsford",
            "Newcastle Upon Tyne",
            "Richmond",
            "Tewkesbury",
            "City Of London",
            "Wideopen",
            "Didcot",
            "Bournemouth",
            # European cities
            "Limburg",
            "Brussels",
            "Aarhus",
            # Indian cities
            "Pune",
            "Bangalore",
            "Mumbai",
            "Delhi",
            "Hyderabad",
        }

        # Check for company in location (e.g., "Acme Corp, Toronto, ON")
        if "," in location:
            parts = location.split(",")
            first_part = parts[0].strip()

            # Check if first part is a known city
            if first_part in common_cities:
                return "Unknown Company"

            # Check if first part is a known country/region
            if first_part in ["Remote", "United States", "Canada", "United Kingdom"]:
                return "Unknown Company"

            # Check if first part matches US state pattern (2 letters)
            if re.match(r"^[A-Z]{2}$", first_part):
                return "Unknown Company"

            # Check if first part looks like a city (ends with region info)
            # e.g., "Flemish Region", "Brussels Region", "England"
            if "Region" in first_part or first_part in ["England", "Scotland", "Wales"]:
                return "Unknown Company"

            # If first part is reasonably sized and not a city/state, might be company
            if len(first_part) < 50:
                # Could be a company, but we're being conservative
                # In Ministry of Testing format, first part is usually city
                return "Unknown Company"

        # Default: Unknown (company will be researched later)
        return "Unknown Company"


def main():
    """
    Test scraper

    Note: This requires manually passing markdown from Firecrawl MCP tool.
    See scripts/run_ministry_scraper.py for automated version.
    """
    # Example markdown (you would get this from Firecrawl MCP tool)
    test_markdown = """
[Quality Assurance (QA) Analyst](https://www.ministryoftesting.com/jobs/qa-analyst)

Toronto, Ontario

16 Jan

[Senior QA Engineer](https://www.ministryoftesting.com/jobs/senior-qa-engineer)

Remote

15 Jan
"""

    scraper = MinistryOfTestingScraper()

    # Parse jobs from markdown
    jobs = scraper.parse_jobs_from_page(
        markdown=test_markdown,
        target_locations=["Canada", "Remote", "Toronto"],
    )

    print(f"\n\n{'=' * 80}")
    print(f"RESULTS: {len(jobs)} jobs found")
    print(f"{'=' * 80}\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job.title}")
        print(f"   Company: {job.company}")
        print(f"   Location: {job.location}")
        print(f"   Posted: {job.posted_date}")
        print(f"   Link: {job.link}")
        print()


if __name__ == "__main__":
    main()
