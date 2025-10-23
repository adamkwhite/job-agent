"""
Parser for Built In job alert emails
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class BuiltInParser(BaseEmailParser):
    """Parser for Built In job alert emails"""

    def can_handle(self, email_message) -> bool:
        """Check if this parser can handle the email"""
        from_addr = email_message.get("From", "").lower()
        subject = email_message.get("Subject", "").lower()

        return (
            "builtin" in from_addr
            or "support@builtin.com" in from_addr
            or ("job" in subject and "match" in subject and "product" in subject)
        )

    def parse(self, email_message) -> ParserResult:
        """Parse Built In job alert email"""
        try:
            html_body, _text_body = self.extract_email_body(email_message)

            if not html_body:
                return self._no_html_error()

            soup = BeautifulSoup(html_body, "lxml")
            job_links = soup.find_all("a", href=re.compile(r"builtin\.com(%2F|/)job(%2F|/)"))

            opportunities = self._extract_opportunities_from_links(job_links)

            if not opportunities:
                return self._no_jobs_error()

            return ParserResult(
                success=True, opportunities=opportunities, parser_name=self.name, error=None
            )

        except Exception as e:
            return ParserResult(
                success=False,
                opportunities=[],
                parser_name=self.name,
                error=f"Parse error: {str(e)}",
            )

    def _extract_opportunities_from_links(self, job_links) -> list[OpportunityData]:
        """Extract job opportunities from HTML link elements"""
        opportunities: list[OpportunityData] = []
        seen_urls: set[str] = set()

        for link in job_links:
            opportunity = self._parse_job_link(link, seen_urls)
            if opportunity:
                opportunities.append(opportunity)

        return opportunities

    def _parse_job_link(self, link, seen_urls: set[str]) -> OpportunityData | None:
        """Parse a single job link element and return OpportunityData if valid"""
        try:
            href = link.get("href", "")
            clean_url = self._extract_clean_url(href)

            if not clean_url or clean_url in seen_urls:
                return None

            seen_urls.add(clean_url)

            # Extract job details from divs
            job_details = self._extract_job_details(link)

            if not job_details["title"] or not job_details["company"]:
                return None

            return self._create_opportunity(job_details, clean_url, link)

        except Exception as e:
            print(f"Error parsing Built In job link: {e}")
            return None

    def _extract_job_details(self, link) -> dict[str, str]:
        """Extract job details (title, company, location, salary) from link divs"""
        divs = link.find_all("div", recursive=True)

        details = {"company": "", "title": "", "location": "", "salary": ""}

        for div in divs:
            style = div.get("style", "")
            text = div.get_text(strip=True)

            # Company name: font-size:16px, margin-bottom:8px
            if "font-size:16px" in style and "margin-bottom:8px" in style:
                details["company"] = text

            # Job title: font-size:20px, font-weight:700
            elif "font-size:20px" in style and "font-weight:700" in style:
                details["title"] = text

            # Location: identified by LocationIcon
            elif "LocationIcon" in str(div):
                location_span = div.find("span", style=re.compile("vertical-align"))
                if location_span:
                    details["location"] = location_span.get_text(strip=True)

            # Salary: identified by SalaryIcon
            elif "SalaryIcon" in str(div):
                salary_span = div.find("span", style=re.compile("vertical-align"))
                if salary_span:
                    details["salary"] = salary_span.get_text(strip=True)

        return details

    def _create_opportunity(
        self, job_details: dict[str, str], clean_url: str, link
    ) -> OpportunityData:
        """Create OpportunityData object from parsed job details"""
        return OpportunityData(
            type="direct_job",
            title=job_details["title"],
            company=job_details["company"],
            location=job_details["location"] or "",
            link=clean_url,
            description="",
            salary=job_details["salary"],
            job_type="",
            posted_date="",
            source=self.name,
            source_email="support@builtin.com",
            received_at=datetime.now().isoformat(),
            keywords_matched=[],
            raw_content=link.get_text(strip=True)[:500],
        )

    def _no_html_error(self) -> ParserResult:
        """Return error result for missing HTML content"""
        return ParserResult(
            success=False,
            opportunities=[],
            parser_name=self.name,
            error="No HTML content found in email",
        )

    def _no_jobs_error(self) -> ParserResult:
        """Return error result for no jobs found"""
        return ParserResult(
            success=False,
            opportunities=[],
            parser_name=self.name,
            error="No job opportunities found in email",
        )

    def _extract_clean_url(self, tracking_url: str) -> str:
        """Extract clean builtin.com URL from AWS tracking URL"""
        # Example tracking URL:
        # https://cb4sdw3d.r.us-west-2.awstrack.me/L0/https:%2F%2Fbuiltin.com%2Fjob%2Fsenior-product-manager...

        # Look for builtin.com URL pattern
        match = re.search(r"builtin\.com[^?\"'&\s]+", tracking_url)
        if match:
            # URL encode entities might be present, decode them
            url = match.group(0)
            url = url.replace("%2F", "/")
            url = url.replace("%3F", "?")
            url = url.replace("%3D", "=")
            url = url.replace("%26", "&")

            # Ensure it starts with https://
            if not url.startswith("http"):
                url = "https://" + url

            # Remove any query parameters for deduplication
            if "?" in url:
                url = url.split("?")[0]

            return url

        return ""
