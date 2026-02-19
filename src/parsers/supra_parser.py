"""
Supra Product Leadership Jobs parser
Parses Substack newsletter with curated PM job listings
"""

import re
from email.message import Message

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class SupraParser(BaseEmailParser):
    """Parse Supra's Product Leadership Jobs newsletter"""

    def __init__(self):
        super().__init__()
        self.from_patterns = ["suprainsights@substack.com", "substack.com"]
        self.subject_keywords = ["supra", "product leadership", "product jobs"]

    def can_handle(self, email_message: Message) -> bool:
        """
        Identify Supra newsletter emails

        Checks:
        - From address contains suprainsights or substack
        - Subject contains supra/product leadership keywords
        """
        from_addr = self.extract_email_address(email_message.get("From", ""))
        subject = email_message.get("Subject", "").lower()

        is_from_supra = any(pattern in from_addr.lower() for pattern in self.from_patterns)
        is_supra_subject = any(keyword in subject for keyword in self.subject_keywords)

        # Also check body for Supra branding (handles forwarded emails)
        html_body, text_body = self.extract_email_body(email_message)
        body_text = (html_body + " " + text_body).lower()
        is_supra_content = "suprainsights" in body_text or "supra's product leadership" in body_text

        return is_from_supra or is_supra_subject or is_supra_content

    def parse(self, email_message: Message) -> ParserResult:
        """
        Parse job listings from Supra newsletter

        Extracts:
        - Job application links (handling Substack redirects)
        - Company names from link context
        - Job titles from link text
        """
        html_body, _ = self.extract_email_body(email_message)

        if not html_body:
            return ParserResult(
                parser_name=self.name, success=False, error="No HTML body found in email"
            )

        soup = BeautifulSoup(html_body, "lxml")
        opportunities: list[OpportunityData] = []

        # Supra emails have jobs in <li> tags with structure:
        # <li><p><strong>Company</strong> is hiring a Title - <a>actual-url-in-text</a></p></li>

        job_list_items = soup.find_all("li")

        for li in job_list_items:
            # Find company name (in <strong> tag)
            company_elem = li.find("strong")
            if not company_elem:
                continue

            company = company_elem.get_text(strip=True)

            # Find job link
            job_link = li.find("a", href=True)
            if not job_link:
                continue

            # The actual job URL is in the link TEXT (not href which is Substack redirect)
            link_text = job_link.get_text(strip=True)

            # Check if link text is a URL
            if not link_text.startswith("http"):
                continue

            actual_url = link_text

            # Extract job title from the <p> text
            # Format: "<strong>Company</strong> is hiring a Job Title - <a>url</a>"
            p_elem = li.find("p")
            title = "Product Leadership Role"  # Default

            if p_elem:
                # Get all text
                full_text = p_elem.get_text(separator=" ", strip=True)

                # Remove company name and URL from text
                # Pattern: "Company is hiring a Title - url"
                text_without_company = full_text.replace(company, "", 1).strip()
                text_without_url = text_without_company.replace(actual_url, "").strip()

                # Extract title between "is hiring a" or "hiring a" and " - "
                title_match = re.search(
                    r"(?:is\s+)?hiring\s+a?\s+(.+?)\s*-\s*$", text_without_url, re.IGNORECASE
                )
                if title_match:
                    title = title_match.group(1).strip()
                elif " - " in text_without_url:
                    # Try simpler pattern: everything before " - "
                    title_part = text_without_url.split(" - ")[0].strip()
                    # Remove "is hiring a" prefix
                    title_part = re.sub(
                        r"^(?:is\s+)?hiring\s+a?\s+", "", title_part, flags=re.IGNORECASE
                    ).strip()
                    if title_part and len(title_part) > 3:
                        title = title_part

            # Skip duplicates
            if any(opp.link == actual_url for opp in opportunities):
                continue

            opportunity = OpportunityData(
                source="supra_newsletter",
                source_email=self.extract_email_address(email_message.get("From", "")),
                type="direct_job",
                company=company,
                title=title,
                location="",  # Supra doesn't include location
                link=actual_url,
                needs_research=False,
            )

            opportunities.append(opportunity)

        if not opportunities:
            return ParserResult(
                parser_name=self.name, success=False, error="No job links found in Supra newsletter"
            )

        return ParserResult(
            parser_name=self.name,
            success=True,
            opportunities=opportunities,
            metadata={"jobs_found": len(opportunities), "source": "supra_newsletter"},
        )

    def _is_job_link(self, href: str, text: str) -> bool:
        """Check if link is a job application link"""
        href_lower = href.lower()
        text_lower = text.lower()

        # Common job board/ATS patterns
        job_domains = [
            "lever.co",
            "greenhouse.io",
            "ashbyhq.com",
            "workable.com",
            "bamboohr.com",
            "jobvite.com",
            "smartrecruiters.com",
            "rippling.com",
            "breezy.hr",
            "recruitee.com",
            "personio.com",
            "careers",
            "jobs",
            "apply",
        ]

        job_keywords = ["job", "career", "position", "opening", "apply", "role", "vacancy"]

        # Check if URL contains job-related domains
        has_job_domain = any(domain in href_lower for domain in job_domains)

        # Check if URL or text contains job keywords
        has_job_keyword = any(
            keyword in href_lower or keyword in text_lower for keyword in job_keywords
        )

        return has_job_domain or has_job_keyword

    def _extract_actual_url(self, href: str) -> str:
        """
        Extract actual job URL from Substack redirect

        Substack wraps links like: https://substack.com/redirect/...?r=<encoded>
        Or direct URLs: https://jobs.lever.co/...
        """
        if "substack.com/redirect" in href:
            # Try to extract URL from redirect parameter
            # This is a simplified version - may need adjustment
            import urllib.parse

            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)

            # Common redirect params: r, u, url
            for param in ["r", "u", "url"]:
                if param in params:
                    return params[param][0]

            # If can't extract, return original
            return href
        else:
            # Direct URL
            return href

    def _extract_company(self, url: str, link_element, _text: str) -> str:
        """
        Extract company name from URL or context

        Priority:
        1. Company name in URL (e.g., jobs.lever.co/perforce)
        2. Nearby text in parent elements
        3. Link text itself
        4. Domain name
        """
        # Try to extract from URL path
        url_lower = url.lower()

        # Pattern: jobs.lever.co/COMPANY or greenhouse.io/COMPANY
        patterns = [
            r"lever\.co/([^/\?]+)",
            r"greenhouse\.io/([^/\?]+)",
            r"ashbyhq\.com/([^/\?]+)",
            r"rippling\.com/[^/]+/([^/\?]+)",
            r"/careers/([^/\?]+)",
            r"/jobs/([^/\?]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url_lower)
            if match:
                company_slug = match.group(1)
                # Clean up slug: perforce-careers -> Perforce
                company = (
                    company_slug.replace("-careers", "")
                    .replace("-jobs", "")
                    .replace("-", " ")
                    .title()
                )
                return company

        # Try parent elements for company name
        parent = link_element.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            # Look for "at COMPANY" or "COMPANY is hiring"
            at_match = re.search(r"at\s+([A-Z][a-zA-Z\s]+)", parent_text)
            if at_match:
                return at_match.group(1).strip()

        # Try to extract from domain
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        # Remove common prefixes
        domain = domain.replace("jobs.", "").replace("careers.", "").replace("www.", "")
        domain = domain.split(".")[0]  # Get first part
        return domain.title()

    def _extract_title(self, link_element, text: str) -> str:
        """
        Extract job title from link text or context

        Priority:
        1. Link text itself (if it looks like a job title)
        2. Nearby heading or bold text
        3. Generic "Product Leadership Role"
        """
        # Check if link text is a job title (not just "Apply" or "Learn More")
        generic_texts = [
            "apply",
            "learn more",
            "view job",
            "click here",
            "read more",
            "see details",
        ]

        if (
            text
            and len(text) > 10
            and not any(generic in text.lower() for generic in generic_texts)
        ):
            return text

        # Look for nearby headings
        parent = link_element.parent
        for _ in range(3):  # Search up to 3 levels
            if parent:
                # Check for heading tags
                heading = parent.find(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"])
                if heading:
                    heading_text = heading.get_text(strip=True)
                    if heading_text and len(heading_text) > 10:
                        return heading_text
                parent = parent.parent

        # Default
        return "Product Leadership Role"

    def _extract_location(self, link_element) -> str:
        """Extract location from link context"""
        parent = link_element.parent
        if parent:
            text = parent.get_text()
            # Look for common location patterns
            patterns = [
                r"(Remote|Hybrid|In-Office)",
                r"([A-Z][a-z]+,\s*[A-Z]{2})",  # City, ST
                r"([A-Z][a-z]+,\s*[A-Z][a-z]+)",  # City, Country
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(0)

        return ""


def main():
    """CLI entry point for testing"""
    import argparse
    import email

    parser = argparse.ArgumentParser(description="Test Supra parser with email file")
    parser.add_argument("email_file", help="Path to .eml file")

    args = parser.parse_args()

    # Load email
    with open(args.email_file) as f:
        msg = email.message_from_file(f)

    # Parse
    supra_parser = SupraParser()

    if not supra_parser.can_handle(msg):
        print("❌ This doesn't look like a Supra email")
        return

    print("✓ Identified as Supra newsletter")
    print("\nParsing jobs...")

    result = supra_parser.parse(msg)

    if result.success:
        print(f"\n✓ Found {len(result.opportunities)} jobs:\n")
        for opp in result.opportunities:
            print(f"→ {opp.title}")
            print(f"  Company: {opp.company}")
            print(f"  Location: {opp.location or 'Not specified'}")
            print(f"  Link: {opp.link}\n")
    else:
        print(f"\n❌ Parsing failed: {result.error}")


if __name__ == "__main__":
    main()
