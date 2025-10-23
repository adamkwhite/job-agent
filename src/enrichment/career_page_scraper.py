"""
Career page job scraper
Extracts job listings from company career pages
"""

import re

import requests
from bs4 import BeautifulSoup

from models import OpportunityData


class CareerPageScraper:
    """Scrape job listings from career pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def scrape_jobs(
        self, career_url: str, company_name: str, source_opportunity: OpportunityData
    ) -> list[OpportunityData]:
        """
        Scrape job listings from career page

        Args:
            career_url: URL of the career page
            company_name: Company name
            source_opportunity: Original funding opportunity (for metadata)

        Returns:
            List of OpportunityData objects (one per job)
        """
        print(f"\nScraping jobs from: {career_url}")

        try:
            response = self.session.get(career_url, timeout=10)

            if response.status_code != 200:
                print(f"  ✗ Failed to fetch page: HTTP {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "lxml")

            # Try to find job listings
            jobs = self._extract_jobs(soup, career_url, company_name, source_opportunity)

            print(f"  ✓ Found {len(jobs)} job listings")
            return jobs

        except Exception as e:
            print(f"  ✗ Error scraping page: {e}")
            return []

    def _extract_jobs(
        self,
        soup: BeautifulSoup,
        career_url: str,
        company_name: str,
        source_opportunity: OpportunityData,
    ) -> list[OpportunityData]:
        """Extract job listings from parsed HTML"""
        jobs = []

        # Strategy 1: Look for common job listing patterns
        # Most career pages use:
        # - <a> tags with "job" in href
        # - Div/li with job-related classes
        # - Links containing "apply", "position", etc.

        # Find all potential job links
        job_links = []

        # Method 1: Find links with job-related href patterns
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if self._is_job_link(href, text):
                full_url = self._make_absolute_url(href, career_url)
                job_title = self._extract_job_title(link, soup)

                if job_title and full_url:
                    job_links.append({"title": job_title, "url": full_url, "link_element": link})

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in job_links:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)

        # Convert to OpportunityData objects
        for job in unique_jobs:
            # Extract additional details if available
            location = self._extract_job_location(job["link_element"], soup)

            opportunity = OpportunityData(
                source=f"{source_opportunity.source}_enriched",
                source_email=source_opportunity.source_email,
                type="direct_job",
                company=company_name,
                company_location=source_opportunity.company_location,
                title=job["title"],
                location=location,
                link=job["url"],
                needs_research=False,
                # Preserve funding context
                funding_stage=source_opportunity.funding_stage,
                funding_amount=source_opportunity.funding_amount,
                industry_tags=source_opportunity.industry_tags,
                investors=source_opportunity.investors,
                raw_content=f"Found on career page: {career_url}",
            )

            jobs.append(opportunity)

        return jobs

    def _is_job_link(self, href: str, text: str) -> bool:
        """Check if link is likely a job posting"""
        job_keywords = ["job", "career", "position", "opening", "apply", "role", "vacancy"]
        exclude_keywords = ["linkedin", "indeed", "glassdoor", "twitter", "facebook", "instagram"]

        href_lower = href.lower()
        text_lower = text.lower()

        # Exclude external links and social media
        if any(keyword in href_lower for keyword in exclude_keywords):
            return False

        # Include if href or text contains job keywords
        return any(keyword in href_lower or keyword in text_lower for keyword in job_keywords)

    def _extract_job_title(self, link_element, soup: BeautifulSoup) -> str:
        """Extract job title from link element"""
        # Try link text first
        text = link_element.get_text(strip=True)

        if text and len(text) > 5 and len(text) < 100:
            # Clean up the text
            text = re.sub(r"\s+", " ", text)
            return text

        # Try parent element
        parent = link_element.parent
        if parent:
            # Look for heading tags
            for tag in ["h1", "h2", "h3", "h4", "h5"]:
                heading = parent.find(tag)
                if heading:
                    title = heading.get_text(strip=True)
                    if len(title) > 5:
                        return title

            # Try parent text
            parent_text = parent.get_text(strip=True)
            if len(parent_text) > 5 and len(parent_text) < 100:
                return parent_text

        return text

    def _extract_job_location(self, link_element, soup: BeautifulSoup) -> str:
        """Extract job location if available"""
        parent = link_element.parent

        if parent:
            text = parent.get_text()

            # Look for location patterns
            # Examples: "San Francisco, CA", "Remote", "New York, NY"
            location_match = re.search(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2}|Remote|Hybrid)\b", text
            )
            if location_match:
                return location_match.group(1)

        return ""

    def _make_absolute_url(self, href: str, base_url: str) -> str:
        """Convert relative URL to absolute URL"""
        from urllib.parse import urljoin

        return urljoin(base_url, href)
