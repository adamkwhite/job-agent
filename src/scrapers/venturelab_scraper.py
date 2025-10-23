"""
VentureLab job board scraper
Scrapes https://www.venturelab.ca/job-board
"""

import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from job_filter import JobFilter
from models import OpportunityData


class VentureLabScraper:
    """Scrape jobs from VentureLab job board"""

    def __init__(self):
        self.base_url = "https://www.venturelab.ca"
        self.job_board_url = f"{self.base_url}/job-board"
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        self.filter = JobFilter()

    def scrape_jobs(self) -> list[OpportunityData]:
        """
        Scrape all jobs from VentureLab job board

        Returns:
            List of job opportunities
        """
        print(f"\n{'=' * 70}")
        print("Scraping VentureLab Job Board")
        print(f"{'=' * 70}")

        try:
            response = self.session.get(self.job_board_url, timeout=10)

            if response.status_code != 200:
                print(f"Failed to fetch job board (HTTP {response.status_code})")
                return []

            jobs = self._parse_page(response.text)
            print(f"  ✓ Found {len(jobs)} jobs")

            return jobs

        except Exception as e:
            print(f"Error scraping VentureLab: {e}")
            return []

    def _parse_page(self, html: str) -> list[OpportunityData]:
        """
        Parse jobs from HTML page

        VentureLab uses static HTML with job listings containing:
        - Job title (link to detail page)
        - Company name
        - Description
        """
        soup = BeautifulSoup(html, "lxml")
        jobs = []

        # Find all job listings
        # Look for links that go to job detail pages (/job-board-items/)
        job_links = soup.find_all("a", href=lambda x: x and "/job-board-items/" in x)

        seen_links = set()

        for link in job_links:
            href = link.get("href", "")

            # Skip duplicates
            if href in seen_links:
                continue

            # Make absolute URL
            if not href.startswith("http"):
                if href.startswith("/"):
                    href = f"{self.base_url}{href}"
                else:
                    href = f"{self.base_url}/{href}"

            seen_links.add(href)

            # Extract job details from link context
            title = self._extract_title(link)
            company = self._extract_company(link)
            description = self._extract_description(link)

            # Only add if we have at least title or company
            if not title and not company:
                continue

            job = OpportunityData(
                source="venturelab",
                source_email="",
                type="direct_job",
                company=company or "Unknown",
                title=title or "Job Opportunity",
                location="",  # VentureLab doesn't show location in listings
                link=href,
                description=description,
                needs_research=False,
            )

            jobs.append(job)

        return jobs

    def _extract_title(self, link_element) -> str:
        """Extract job title from link or nearby elements"""
        # Try link text first
        title = link_element.get_text(strip=True)

        if title and len(title) > 5 and title.lower() not in ["learn more", "read more", "apply"]:
            return title

        # Try nearby heading tags
        parent = link_element.parent
        for _ in range(3):  # Search up to 3 levels
            if parent:
                heading = parent.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
                if heading:
                    title = heading.get_text(strip=True)
                    if title and len(title) > 5:
                        return title
                parent = parent.parent

        return title

    def _extract_company(self, link_element) -> str:
        """Extract company name from link context"""
        # Look for company name in parent or sibling elements
        parent = link_element.parent

        if parent:
            # Try to find company name
            # Usually appears near the job title
            for _ in range(5):  # Search up to 5 levels
                if parent:
                    # Look for text that might be company name
                    text = parent.get_text(separator="|", strip=True)
                    parts = text.split("|")

                    # Company name is often the second item after title
                    if len(parts) >= 2:
                        potential_company = parts[1].strip()
                        # Filter out common non-company text
                        if (
                            potential_company
                            and len(potential_company) > 2
                            and potential_company.lower()
                            not in [
                                "learn more",
                                "apply",
                                "full-time",
                                "part-time",
                                "remote",
                                "hybrid",
                            ]
                        ):
                            return potential_company

                    parent = parent.parent

        return ""

    def _extract_description(self, link_element) -> str:
        """Extract job description from link context"""
        parent = link_element.parent

        if parent:
            # Look for paragraph or description text
            for _ in range(5):
                if parent:
                    # Find paragraph tags
                    description_elem = parent.find("p")
                    if description_elem:
                        desc = description_elem.get_text(strip=True)
                        # Filter out short text and common phrases
                        if desc and len(desc) > 20 and "learn more" not in desc.lower():
                            return desc

                    parent = parent.parent

        return ""

    def scrape_and_filter(self) -> tuple:
        """
        Scrape jobs and apply filters

        Returns:
            Tuple of (included_jobs, excluded_jobs)
        """
        all_jobs = self.scrape_jobs()

        if not all_jobs:
            print("\n⚠️  No jobs found!")
            return [], []

        # Convert to dicts for filtering
        jobs_as_dicts = [self._opportunity_to_dict(job) for job in all_jobs]

        # Filter
        print(f"\nFiltering {len(jobs_as_dicts)} jobs...")
        included, excluded = self.filter.filter_jobs(jobs_as_dicts)

        print(f"  ✓ Passed filter: {len(included)}")
        print(f"  ✗ Excluded: {len(excluded)}")

        return included, excluded

    def _opportunity_to_dict(self, opp: OpportunityData) -> dict:
        """Convert OpportunityData to dict for filtering"""
        return {
            "title": opp.title or "",
            "company": opp.company or "",
            "location": opp.location or "",
            "link": opp.link or "",
            "description": opp.description or "",
            "salary": "",
            "job_type": "",
            "source": opp.source,
        }


def main():
    """CLI entry point"""
    scraper = VentureLabScraper()
    included, excluded = scraper.scrape_and_filter()

    if included:
        print(f"\n{'=' * 70}")
        print(f"MATCHING JOBS ({len(included)})")
        print(f"{'=' * 70}")

        for job in included:
            print(f"\n→ {job['title']}")
            print(f"  Company: {job['company']}")
            print(f"  Keywords: {', '.join(job.get('keywords_matched', []))}")
            print(f"  Link: {job['link']}")
            if job.get("description"):
                print(f"  Description: {job['description'][:100]}...")


if __name__ == "__main__":
    main()
