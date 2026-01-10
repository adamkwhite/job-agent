"""
Parser for Welcome to the Jungle job alert emails

Handles subject line format:
- "New match: [Job Title] at [Company]"

Examples:
- New match: Staff Product Manager at Harvey
- New match: Senior Product Manager at Honeycomb
- New match: Director of Product Management at Qventus

Email from: help@welcometothejungle.com
"""

import re

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class WelcomeToTheJungleParser(BaseEmailParser):
    """Parser for Welcome to the Jungle job alert emails"""

    def can_handle(self, email_message) -> bool:
        """Check if this parser can handle the email"""
        subject = email_message.get("Subject", "")

        # Match pattern: "New match: [Job Title] at [Company]"
        return bool(re.match(r"^New match:\s+.+\s+at\s+.+$", subject, re.IGNORECASE))

    def parse(self, email_message) -> ParserResult:
        """Parse 'New match:' job alert email"""
        try:
            subject = email_message.get("Subject", "")
            from_email = self.extract_email_address(email_message.get("From", ""))

            # Parse subject line: "New match: [Job Title] at [Company]"
            match = re.match(r"^New match:\s+(.+)\s+at\s+(.+)$", subject, re.IGNORECASE)

            if not match:
                return self._parse_error("Could not parse subject line format")

            title = match.group(1).strip()
            company = match.group(2).strip()

            # Extract HTML body to find job link
            html_body, text_body = self.extract_email_body(email_message)
            job_link = self._extract_job_link(html_body, text_body)

            if not job_link:
                # If no link found, create opportunity without link (needs_research=True)
                opportunity = OpportunityData(
                    source="welcometothejungle",
                    source_email=from_email,
                    type="direct_job",
                    company=company,
                    title=title,
                    location="",
                    link="",
                    needs_research=True,
                )
            else:
                opportunity = OpportunityData(
                    source="welcometothejungle",
                    source_email=from_email,
                    type="direct_job",
                    company=company,
                    title=title,
                    location="",
                    link=job_link,
                    needs_research=False,
                )

            return ParserResult(
                success=True, opportunities=[opportunity], parser_name=self.name, error=None
            )

        except Exception as e:
            return self._parse_error(f"Parse error: {str(e)}")

    def _extract_job_link(self, html_body: str, text_body: str) -> str:
        """Extract job application link from email body"""
        # Try HTML first
        if html_body:
            soup = BeautifulSoup(html_body, "lxml")

            # Find all links
            links = soup.find_all("a", href=True)

            for link in links:
                href = link.get("href", "")

                # Filter for job-related links
                if self.is_job_link(href):
                    return href

        # Fallback to text body
        if text_body:
            # Extract URLs from plain text
            urls = re.findall(r"https?://[^\s]+", text_body)

            for url in urls:
                if self.is_job_link(url):
                    return url

        return ""

    def _parse_error(self, message: str) -> ParserResult:
        """Return error result"""
        return ParserResult(success=False, opportunities=[], parser_name=self.name, error=message)
