"""
Parser for Wellfound (formerly AngelList Talent) job alert emails

Handles subject line format:
- "New jobs: [Job Title] at [Company] and X more jobs"

Examples:
- New jobs: Head of Engineering (Hands-On, Player-Coach) at NewVue.ai and 9 more jobs
- New jobs: Sr Engineering Manager, Replication and Storage at Redpanda Data and 7 more jobs

Note: This parser only extracts the primary job from the subject line.
Additional jobs mentioned in "and X more jobs" are not parsed.

Email from: team@hi.wellfound.com
"""

import re

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class WellfoundParser(BaseEmailParser):
    """Parser for Wellfound job alert emails"""

    def can_handle(self, email_message) -> bool:
        """Check if this parser can handle the email"""
        subject = email_message.get("Subject", "")

        # Match pattern: "New jobs: [Job Title] at [Company] and X more jobs"
        return bool(
            re.match(
                r"^New jobs:\s+.+\s+at\s+.+\s+and\s+\d+\s+more\s+jobs?", subject, re.IGNORECASE
            )
        )

    def parse(self, email_message) -> ParserResult:
        """Parse 'New jobs:' job alert email"""
        try:
            subject = email_message.get("Subject", "")
            from_email = self.extract_email_address(email_message.get("From", ""))

            # Parse subject line: "New jobs: [Job Title] at [Company] and X more jobs"
            match = re.match(
                r"^New jobs:\s+(.+?)\s+at\s+(.+?)\s+and\s+\d+\s+more\s+jobs?",
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
                        source="wellfound",
                        source_email=from_email,
                        type="direct_job",
                        company=company,
                        title=title,
                        location="",
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
        seen_urls: set[str] = set()

        # Try HTML first
        opportunities = self._extract_html_opportunities(
            html_body, from_email, primary_title, primary_company, seen_urls
        )

        # Fallback to text body URLs
        if not opportunities:
            opportunities = self._extract_text_opportunities(
                text_body, from_email, primary_title, primary_company, seen_urls
            )

        return opportunities

    def _extract_html_opportunities(
        self,
        html_body: str,
        from_email: str,
        primary_title: str,
        primary_company: str,
        seen_urls: set[str],
    ) -> list[OpportunityData]:
        """Extract job opportunities from HTML body by parsing links"""
        opportunities: list[OpportunityData] = []

        if not html_body:
            return opportunities

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

            # Use link text as title if available, otherwise use subject title
            title = link_text if link_text and len(link_text) > 5 else primary_title

            opportunities.append(
                OpportunityData(
                    source="wellfound",
                    source_email=from_email,
                    type="direct_job",
                    company=primary_company,  # Use company from subject
                    title=title,
                    location="",
                    link=href,
                    needs_research=False,
                )
            )

        return opportunities

    def _extract_text_opportunities(
        self,
        text_body: str,
        from_email: str,
        primary_title: str,
        primary_company: str,
        seen_urls: set[str],
    ) -> list[OpportunityData]:
        """Extract job opportunities from text body by finding URLs"""
        opportunities: list[OpportunityData] = []

        if not text_body:
            return opportunities

        urls = re.findall(r"https?://[^\s]+", text_body)

        for url in urls:
            if self.is_job_link(url) and url not in seen_urls:
                seen_urls.add(url)

                opportunities.append(
                    OpportunityData(
                        source="wellfound",
                        source_email=from_email,
                        type="direct_job",
                        company=primary_company,
                        title=primary_title,
                        location="",
                        link=url,
                        needs_research=False,
                    )
                )

        return opportunities

    def _parse_error(self, message: str) -> ParserResult:
        """Return error result"""
        return ParserResult(success=False, opportunities=[], parser_name=self.name, error=message)
