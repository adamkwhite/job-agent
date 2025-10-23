"""
Artemis Update parser
Parses company growth and executive hiring announcements
"""

import re
from email.message import Message

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class ArtemisParser(BaseEmailParser):
    """Parse Artemis Update emails for growing companies"""

    def __init__(self):
        super().__init__()
        self.from_patterns = ["artemis", "artemis.xyz", "newsletter"]
        self.subject_keywords = ["artemis update", "artemis", "company growth", "executive hire"]

    def can_handle(self, email_message: Message) -> bool:
        """
        Identify Artemis Update emails

        Checks:
        - From address contains artemis
        - Subject contains artemis/update keywords
        - Body contains Artemis branding
        """
        from_addr = self.extract_email_address(email_message.get("From", ""))
        subject = email_message.get("Subject", "").lower()

        is_from_artemis = any(pattern in from_addr.lower() for pattern in self.from_patterns)
        is_artemis_subject = any(keyword in subject for keyword in self.subject_keywords)

        # Also check body for Artemis branding (handles forwarded emails)
        html_body, text_body = self.extract_email_body(email_message)
        body_text = (html_body + " " + text_body).lower()
        is_artemis_content = "artemis" in body_text and (
            "update" in body_text or "growth" in body_text
        )

        return is_from_artemis or is_artemis_subject or is_artemis_content

    def parse(self, email_message: Message) -> ParserResult:
        """
        Parse growing companies from Artemis updates

        Looks for patterns like:
        - "X joins Y as VP/Director/Executive"
        - "Y hires X as Chief..."
        - "Y expands team with X"
        - Company growth announcements

        Returns companies as funding_lead type for career page enrichment
        """
        html_body, text_body = self.extract_email_body(email_message)

        if not html_body and not text_body:
            return ParserResult(parser_name=self.name, success=False, error="No email body found")

        # Use HTML if available, otherwise text
        content = html_body if html_body else text_body
        soup = BeautifulSoup(content, "lxml") if html_body else None

        opportunities = []
        seen_companies = set()

        # Strategy 1: Parse executive hire announcements
        # Pattern: "Person joins Company as Title" or "Company hires Person as Title"
        hire_patterns = [
            r"joins\s+([A-Z][A-Za-z\s&]+?)\s+as\s+(VP|Vice President|Director|Chief|Head|SVP|EVP|President)",
            r"([A-Z][A-Za-z\s&]+?)\s+hires\s+[A-Za-z\s]+\s+as\s+(VP|Vice President|Director|Chief|Head)",
            r"([A-Z][A-Za-z\s&]+?)\s+appoints\s+[A-Za-z\s]+\s+as\s+(VP|Vice President|Director|Chief|Head)",
            r"([A-Z][A-Za-z\s&]+?)\s+adds\s+[A-Za-z\s]+\s+as\s+(VP|Vice President|Director|Chief|Head)",
        ]

        text_content = soup.get_text() if soup else text_body

        for pattern in hire_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            for match in matches:
                company = match.group(1).strip()

                # Clean up company name
                company = self._clean_company_name(company)

                # Skip if already seen or invalid
                if not company or company in seen_companies or len(company) < 2:
                    continue

                # Skip common false positives
                if self._is_false_positive(company):
                    continue

                seen_companies.add(company)

                # Try to find company website from links
                website = self._find_company_website(soup, company) if soup else None

                opportunity = OpportunityData(
                    source="artemis_update",
                    source_email=self.extract_email_address(email_message.get("From", "")),
                    type="funding_lead",
                    company=company,
                    title=None,  # Will be filled during enrichment
                    link=website,
                    description="Executive hire announcement - actively growing team",
                    funding_stage="Growth",  # Assume growth stage if hiring execs
                    funding_amount=None,
                    needs_research=True,  # Needs career page discovery
                )

                opportunities.append(opportunity)

        # Strategy 2: Look for company links in structured lists/sections
        if soup:
            company_opps = self._parse_company_sections(soup, email_message)
            for opp in company_opps:
                if opp.company not in seen_companies:
                    seen_companies.add(opp.company)
                    opportunities.append(opp)

        if not opportunities:
            return ParserResult(
                parser_name=self.name,
                success=False,
                error="No company growth announcements found in Artemis update",
            )

        return ParserResult(
            parser_name=self.name,
            success=True,
            opportunities=opportunities,
            metadata={"companies_found": len(opportunities), "source": "artemis_update"},
        )

    def _clean_company_name(self, company: str) -> str:
        """Clean up extracted company name"""
        # Remove common suffixes
        company = re.sub(
            r"\s+(Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?)$", "", company, flags=re.IGNORECASE
        )

        # Remove trailing punctuation
        company = company.rstrip(".,;:")

        # Remove possessive
        company = company.replace("'s", "")

        # Title case
        company = company.strip()

        return company

    def _is_false_positive(self, company: str) -> bool:
        """Filter out common false positives"""
        false_positives = [
            "the",
            "a",
            "an",
            "this",
            "that",
            "these",
            "those",
            "new",
            "former",
            "current",
            "latest",
            "recent",
            "company",
            "companies",
            "organization",
            "firm",
            "team",
            "group",
            "department",
            "division",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]

        company_lower = company.lower()

        # Check against false positives
        if company_lower in false_positives:
            return True

        # Must have at least one letter
        if not re.search(r"[a-zA-Z]", company):
            return True

        # Too short (single letter companies rare)
        if len(company) < 2:
            return True

        # All caps (likely acronym from middle of sentence)
        if company.isupper() and len(company) < 4:
            return True

        return False

    def _find_company_website(self, soup: BeautifulSoup, company: str) -> str | None:
        """
        Try to find company website from nearby links

        Looks for links near company mention
        """
        # Find all mentions of company name
        company_texts = soup.find_all(string=re.compile(re.escape(company), re.IGNORECASE))

        for text_node in company_texts:
            # Check if text node is inside a link
            parent = text_node.parent
            for _ in range(3):  # Search up 3 levels
                if parent and parent.name == "a":
                    href = parent.get("href", "")
                    # Filter out social media, email, etc.
                    if self._is_company_website(href):
                        return href
                if parent:
                    parent = parent.parent

            # Check for nearby links
            if text_node.parent:
                nearby_links = text_node.parent.find_all("a", href=True, limit=3)
                for link in nearby_links:
                    href = link.get("href", "")
                    if self._is_company_website(href):
                        return href

        return None

    def _is_company_website(self, url: str) -> bool:
        """Check if URL looks like a company website"""
        if not url:
            return False

        url_lower = url.lower()

        # Exclude common non-company sites
        exclude_patterns = [
            "linkedin.com",
            "twitter.com",
            "facebook.com",
            "instagram.com",
            "youtube.com",
            "github.com",
            "medium.com",
            "mailto:",
            "javascript:",
            "#",
            "artemis",
            "unsubscribe",
            "preferences",
        ]

        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Must start with http
        if not url.startswith("http"):
            return False

        return True

    def _parse_company_sections(
        self, soup: BeautifulSoup, email_message: Message
    ) -> list[OpportunityData]:
        """
        Parse structured company sections/lists

        Some Artemis updates have formatted sections like:
        - Featured Companies
        - Growth Leaders
        - Hiring Announcements
        """
        opportunities = []

        # Look for section headings that indicate company lists
        section_keywords = ["featured", "growth", "hiring", "companies", "spotlight", "leaders"]

        for heading in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
            heading_text = heading.get_text(strip=True).lower()

            if any(keyword in heading_text for keyword in section_keywords):
                # Found a relevant section, look for company links in following content
                next_elem = heading.find_next()

                for _ in range(20):  # Check next 20 elements
                    if not next_elem:
                        break

                    # Stop at next heading
                    if next_elem.name in ["h1", "h2", "h3", "h4"]:
                        break

                    # Look for links
                    if next_elem.name == "a":
                        href = next_elem.get("href", "")
                        company_name = next_elem.get_text(strip=True)

                        if self._is_company_website(href) and len(company_name) > 2:
                            opportunity = OpportunityData(
                                source="artemis_update",
                                source_email=self.extract_email_address(
                                    email_message.get("From", "")
                                ),
                                type="funding_lead",
                                company=company_name,
                                title=None,
                                link=href,
                                description="Featured in Artemis growth update",
                                funding_stage="Growth",
                                needs_research=True,
                            )
                            opportunities.append(opportunity)

                    next_elem = next_elem.find_next()

        return opportunities


def main():
    """CLI entry point for testing"""
    import argparse
    import email

    parser = argparse.ArgumentParser(description="Test Artemis parser with email file")
    parser.add_argument("email_file", help="Path to .eml file")

    args = parser.parse_args()

    # Load email
    with open(args.email_file) as f:
        msg = email.message_from_file(f)

    # Parse
    artemis_parser = ArtemisParser()

    if not artemis_parser.can_handle(msg):
        print("❌ This doesn't look like an Artemis email")
        return

    print("✓ Identified as Artemis update")
    print("\nParsing company growth announcements...")

    result = artemis_parser.parse(msg)

    if result.success:
        print(f"\n✓ Found {len(result.opportunities)} growing companies:\n")
        for opp in result.opportunities:
            print(f"→ {opp.company}")
            print(f"  Description: {opp.description}")
            print(f"  Website: {opp.link or 'Not found'}")
            print(f"  Needs Research: {opp.needs_research}\n")
    else:
        print(f"\n❌ Parsing failed: {result.error}")


if __name__ == "__main__":
    main()
