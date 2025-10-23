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
                return ParserResult(
                    success=False,
                    opportunities=[],
                    parser_name=self.name,
                    error="No HTML content found in email",
                )

            # Parse HTML
            soup = BeautifulSoup(html_body, "lxml")

            # Extract all job links (URLs are URL-encoded in AWS tracking links)
            job_links = soup.find_all("a", href=re.compile(r"builtin\.com(%2F|/)job(%2F|/)"))

            opportunities = []
            seen_urls = set()

            for link in job_links:
                try:
                    # Extract the clean URL from the tracking URL
                    href = link.get("href", "")
                    clean_url = self._extract_clean_url(href)

                    if not clean_url or clean_url in seen_urls:
                        continue

                    seen_urls.add(clean_url)

                    # Extract job details from the link structure
                    # Built In structure:
                    # <a href="...">
                    #   <div>Company Name (16px)</div>
                    #   <div>Job Title (20px, bold)</div>
                    #   <div>Location/Remote info (12px)</div>
                    #   <div>Salary (12px, optional)</div>
                    # </a>

                    # Get all divs inside the link
                    divs = link.find_all("div", recursive=True)

                    company = ""
                    title = ""
                    location = ""
                    salary = ""

                    for div in divs:
                        style = div.get("style", "")
                        text = div.get_text(strip=True)

                        # Company name: font-size:16px, margin-bottom:8px
                        if "font-size:16px" in style and "margin-bottom:8px" in style:
                            company = text

                        # Job title: font-size:20px, font-weight:700
                        elif "font-size:20px" in style and "font-weight:700" in style:
                            title = text

                        # Location: contains location text or remote info
                        elif "LocationIcon" in str(div):
                            # Look for the span with location text
                            location_span = div.find("span", style=re.compile("vertical-align"))
                            if location_span:
                                location = location_span.get_text(strip=True)

                        # Salary: contains SalaryIcon
                        elif "SalaryIcon" in str(div):
                            salary_span = div.find("span", style=re.compile("vertical-align"))
                            if salary_span:
                                salary = salary_span.get_text(strip=True)

                    # Only add if we found at least title and company
                    if title and company:
                        opportunity = OpportunityData(
                            type="direct_job",
                            title=title,
                            company=company,
                            location=location or "",
                            link=clean_url,
                            description="",
                            salary=salary,
                            job_type="",
                            posted_date="",
                            source=self.name,
                            source_email="support@builtin.com",
                            received_at=datetime.now().isoformat(),
                            keywords_matched=[],
                            raw_content=link.get_text(strip=True)[:500],
                        )

                        opportunities.append(opportunity)

                except Exception as e:
                    # Skip this job but continue parsing others
                    print(f"Error parsing Built In job link: {e}")
                    continue

            if not opportunities:
                return ParserResult(
                    success=False,
                    opportunities=[],
                    parser_name=self.name,
                    error="No job opportunities found in email",
                )

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
