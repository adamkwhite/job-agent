"""
BuiltIn job board scraper
Uses direct search URLs for specific roles
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time

from models import OpportunityData
from job_filter import JobFilter


class BuiltInScraper:
    """Scrape jobs from BuiltIn job boards"""

    def __init__(self, city: str = "toronto"):
        self.city = city.lower()
        self.base_url = f"https://builtin{self.city}.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.filter = JobFilter()

        # Direct search URLs for target roles
        self.search_urls = {
            'product_manager': f"{self.base_url}/jobs/product/search/product-manager",
            'engineering_manager': f"{self.base_url}/jobs/dev-engineering/search/engineering-manager",
            'engineering_director': f"{self.base_url}/jobs/dev-engineering/search/engineering-director",
            'vp_engineering': f"{self.base_url}/jobs/dev-engineering/search/vp-engineering",
        }

    def scrape_all_roles(self, max_pages: int = 5) -> List[OpportunityData]:
        """
        Scrape all configured role types

        Args:
            max_pages: Maximum pages to scrape per role type

        Returns:
            List of job opportunities
        """
        all_jobs = []

        for role_name, url in self.search_urls.items():
            print(f"\nScraping {role_name.replace('_', ' ').title()}...")
            jobs = self.scrape_role(url, max_pages=max_pages)
            all_jobs.extend(jobs)
            print(f"  Found {len(jobs)} jobs")

            # Be polite - don't hammer the server
            time.sleep(2)

        # Deduplicate by link
        unique_jobs = {}
        for job in all_jobs:
            if job.link not in unique_jobs:
                unique_jobs[job.link] = job

        print(f"\nTotal unique jobs: {len(unique_jobs)}")
        return list(unique_jobs.values())

    def scrape_role(self, url: str, max_pages: int = 5) -> List[OpportunityData]:
        """
        Scrape a specific role search URL

        Args:
            url: Search URL
            max_pages: Maximum pages to scrape

        Returns:
            List of job opportunities
        """
        jobs = []

        for page in range(1, max_pages + 1):
            page_url = f"{url}?page={page}" if page > 1 else url

            try:
                print(f"  Page {page}...", end=" ")
                response = self.session.get(page_url, timeout=10)

                if response.status_code != 200:
                    print(f"Failed (HTTP {response.status_code})")
                    break

                page_jobs = self._parse_page(response.text)
                jobs.extend(page_jobs)
                print(f"{len(page_jobs)} jobs")

                # If we got no jobs, we've reached the end
                if not page_jobs:
                    break

                time.sleep(1)  # Be polite

            except Exception as e:
                print(f"Error: {e}")
                break

        return jobs

    def _parse_page(self, html: str) -> List[OpportunityData]:
        """
        Parse jobs from HTML page

        Note: BuiltIn uses JavaScript to load jobs, so this may not work
        with simple requests. Returns instructions for manual export if needed.
        """
        soup = BeautifulSoup(html, 'lxml')
        jobs = []

        # Try to find job cards
        # Note: This is a best-effort parser since the site uses JS heavily
        # For production, would need to use Playwright

        # Look for job links
        job_links = soup.find_all('a', href=lambda x: x and '/job/' in x)

        seen_links = set()

        for link in job_links:
            href = link.get('href', '')

            # Skip duplicates
            if href in seen_links:
                continue

            # Make absolute URL
            if not href.startswith('http'):
                href = f"{self.base_url}{href}"

            seen_links.add(href)

            # Extract title
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # Try to find company (usually in parent or nearby elements)
            company = self._extract_company(link)

            # Try to find location
            location = self._extract_location(link)

            job = OpportunityData(
                source=f"builtin_{self.city}",
                source_email="",
                type="direct_job",
                company=company or "Unknown",
                title=title,
                location=location,
                link=href,
                needs_research=False
            )

            jobs.append(job)

        return jobs

    def _extract_company(self, link_element) -> str:
        """Extract company name from link context"""
        # Try parent elements
        parent = link_element.parent
        for _ in range(5):  # Search up to 5 levels
            if parent:
                # Look for company links
                company_link = parent.find('a', href=lambda x: x and '/company/' in x)
                if company_link:
                    return company_link.get_text(strip=True)
                parent = parent.parent

        return ""

    def _extract_location(self, link_element) -> str:
        """Extract location from link context"""
        parent = link_element.parent
        if parent:
            text = parent.get_text()
            # Look for "Toronto, ON" pattern
            import re
            match = re.search(r'Toronto,\s*ON|Remote|Hybrid|In-Office', text)
            if match:
                return match.group(0)

        return ""

    def scrape_and_filter(self, max_pages: int = 5) -> tuple:
        """
        Scrape jobs and apply filters

        Returns:
            Tuple of (included_jobs, excluded_jobs)
        """
        print(f"\n{'='*70}")
        print(f"Scraping BuiltIn {self.city.title()} Job Board")
        print(f"{'='*70}")

        all_jobs = self.scrape_all_roles(max_pages=max_pages)

        if not all_jobs:
            print("\n⚠️  No jobs found!")
            print("\nNOTE: BuiltIn uses JavaScript to load jobs.")
            print("For best results, use direct URLs:")
            for role, url in self.search_urls.items():
                print(f"  - {role.replace('_', ' ').title()}: {url}")
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
            'title': opp.title or '',
            'company': opp.company or '',
            'location': opp.location or '',
            'link': opp.link or '',
            'description': '',
            'salary': '',
            'job_type': '',
            'source': opp.source,
        }


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape BuiltIn job boards')
    parser.add_argument('--city', default='toronto', help='City (toronto, montreal, vancouver, etc.)')
    parser.add_argument('--pages', type=int, default=3, help='Max pages per role to scrape')

    args = parser.parse_args()

    scraper = BuiltInScraper(city=args.city)
    included, excluded = scraper.scrape_and_filter(max_pages=args.pages)

    if included:
        print(f"\n{'='*70}")
        print(f"MATCHING JOBS ({len(included)})")
        print(f"{'='*70}")

        for job in included:
            print(f"\n→ {job['title']}")
            print(f"  Company: {job['company']}")
            print(f"  Location: {job['location']}")
            print(f"  Keywords: {', '.join(job.get('keywords_matched', []))}")
            print(f"  Link: {job['link']}")


if __name__ == "__main__":
    main()
