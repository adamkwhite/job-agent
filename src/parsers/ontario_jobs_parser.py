"""
Parser for "Ontario engineering jobs" emails (likely Indeed or similar aggregator)

Handles subject line format:
- "[Job Title] at [Company] and 29 more engineering jobs in Ontario for you!"
- "[Job Title] at [Company] and X more engineering jobs in Ontario for you!"

Examples:
- Specialist, Performance & Engineering at Vale and 29 more engineering jobs in Ontario for you!
- Utilities Lead at Unilever and 29 more engineering jobs in Ontario for you!
- Project Manager at Landmark Structures Co and 29 more engineering jobs in Ontario for you!

Note: This parser only extracts the primary job from the subject line.
Additional jobs mentioned in "and X more" are not parsed.
"""

import re

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class OntarioJobsParser(BaseEmailParser):
    """Parser for Ontario engineering jobs alert emails"""

    def can_handle(self, email_message) -> bool:
        """Check if this parser can handle the email"""
        subject = email_message.get("Subject", "")

        # Match pattern: "[Job Title] at [Company] and X more engineering jobs in Ontario for you!"
        return bool(
            re.match(
                r"^.+\s+at\s+.+\s+and\s+\d+\s+more\s+engineering\s+jobs\s+in\s+Ontario",
                subject,
                re.IGNORECASE,
            )
        )

    def parse(self, email_message) -> ParserResult:
        """Parse Ontario engineering jobs alert email"""
        try:
            subject = email_message.get("Subject", "")
            from_email = self.extract_email_address(email_message.get("From", ""))

            # Parse subject line: "[Job Title] at [Company] and X more..."
            match = re.match(
                r"^(.+?)\s+at\s+(.+?)\s+and\s+\d+\s+more\s+engineering\s+jobs",
                subject,
                re.IGNORECASE,
            )

            if not match:
                return self._parse_error("Could not parse subject line format")

            title = match.group(1).strip()
            company = match.group(2).strip()

            # Extract HTML body to find job links
            html_body, text_body = self.extract_email_body(email_message)
            opportunities = self._extract_opportunities(
                html_body, text_body, from_email, title, company
            )

            if not opportunities:
                # If no links found in body, create opportunity from subject line
                opportunities = [
                    OpportunityData(
                        source="ontario_jobs",
                        source_email=from_email,
                        type="direct_job",
                        company=company,
                        title=title,
                        location="Ontario",  # We know it's Ontario from subject
                        link="",
                        needs_research=True,
                    )
                ]

            return ParserResult(
                success=True, opportunities=opportunities, parser_name=self.name, error=None
            )

        except Exception as e:
            return self._parse_error(f"Parse error: {str(e)}")

    def _extract_opportunities(
        self,
        html_body: str,
        text_body: str,
        from_email: str,
        primary_title: str,
        primary_company: str,
    ) -> list[OpportunityData]:
        """
        Extract job opportunities from email body.

        Attempts to find multiple job links in the email.
        Falls back to subject line job if no links found.
        """
        opportunities = []
        seen_urls = set()

        # Try HTML first
        if html_body:
            soup = BeautifulSoup(html_body, "lxml")

            # Find all links that look like job postings
            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "")

                if not self.is_job_link(href) or href in seen_urls:
                    continue

                seen_urls.add(href)

                # Try to extract job details from link context
                link_text = self.clean_text(link.get_text())

                # Check if link has company/title info nearby
                parent = link.parent
                parent_text = parent.get_text() if parent else ""

                # Use link text as title if available, otherwise use subject title
                title = link_text if link_text and len(link_text) > 5 else primary_title

                # Try to find company in parent text, fallback to subject company
                company = self._extract_company_from_context(parent_text) or primary_company

                # Try to find location in parent text
                location = self._extract_location_from_context(parent_text) or "Ontario"

                opportunities.append(
                    OpportunityData(
                        source="ontario_jobs",
                        source_email=from_email,
                        type="direct_job",
                        company=company,
                        title=title,
                        location=location,
                        link=href,
                        needs_research=False,
                    )
                )

        # Fallback to text body URLs
        if not opportunities and text_body:
            urls = re.findall(r"https?://[^\s]+", text_body)

            for url in urls:
                if self.is_job_link(url) and url not in seen_urls:
                    seen_urls.add(url)

                    opportunities.append(
                        OpportunityData(
                            source="ontario_jobs",
                            source_email=from_email,
                            type="direct_job",
                            company=primary_company,
                            title=primary_title,
                            location="Ontario",
                            link=url,
                            needs_research=False,
                        )
                    )

        return opportunities

    def _extract_company_from_context(self, text: str) -> str:
        """Try to extract company name from link context"""
        # Look for patterns like "Company: X" or "at X"
        match = re.search(r"(?:Company|at):\s*([^\n\|,]+)", text, re.IGNORECASE)
        if match:
            return self.clean_text(match.group(1))
        return ""

    def _extract_location_from_context(self, text: str) -> str:
        """Try to extract location from link context"""
        # Look for city names in Ontario
        ontario_cities = [
            "Toronto",
            "Ottawa",
            "Mississauga",
            "Hamilton",
            "Brampton",
            "London",
            "Markham",
            "Vaughan",
            "Kitchener",
            "Windsor",
            "Richmond Hill",
            "Oakville",
            "Burlington",
            "Barrie",
            "Oshawa",
            "St. Catharines",
            "Cambridge",
            "Kingston",
            "Guelph",
            "Whitby",
            "Waterloo",
            "Sudbury",
            "Thunder Bay",
        ]

        for city in ontario_cities:
            if city in text:
                # Check if "Ontario" or "ON" is also present
                if "ontario" in text.lower() or ", on" in text.lower():
                    return f"{city}, Ontario"
                return city

        # Look for "Location: X" pattern
        match = re.search(r"Location:\s*([^\n\|]+)", text, re.IGNORECASE)
        if match:
            return self.clean_text(match.group(1))

        return ""

    def _parse_error(self, message: str) -> ParserResult:
        """Return error result"""
        return ParserResult(success=False, opportunities=[], parser_name=self.name, error=message)
