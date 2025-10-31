"""
F6S funding news email parser
Extracts companies that raised funding for career page research
"""

import re
from email.message import Message

from bs4 import BeautifulSoup

from models import OpportunityData, ParserResult
from parsers.base_parser import BaseEmailParser


class F6SParser(BaseEmailParser):
    """Parse F6S funding news emails"""

    def __init__(self):
        super().__init__()
        self.from_emails = ["f6s.com", "noreply@f6s.com"]
        self.subject_keywords = ["f6s", "funding", "raised"]

        # Funding stage patterns
        self.stage_patterns = [
            "seed",
            "pre-seed",
            "series a",
            "series b",
            "series c",
            "series d",
            "private equity",
            "ipo",
        ]

    def can_handle(self, email_message: Message) -> bool:
        """Check if this is an F6S funding news email"""
        from_email = self.extract_email_address(email_message.get("From", "")).lower()
        subject = email_message.get("Subject", "").lower()

        # Check if from F6S
        is_from_f6s = any(domain in from_email for domain in self.from_emails)

        # Check if subject contains funding keywords
        is_funding_news = any(keyword in subject for keyword in self.subject_keywords)

        return is_from_f6s or is_funding_news

    def parse(self, email_message: Message) -> ParserResult:
        """Parse F6S email and extract funding opportunities"""
        try:
            from_email = self.extract_email_address(email_message.get("From", ""))
            html_body, text_body = self.extract_email_body(email_message)

            opportunities = []

            if html_body:
                opportunities = self._parse_html(html_body, from_email)
            elif text_body:
                opportunities = self._parse_text(text_body, from_email)

            return ParserResult(parser_name=self.name, success=True, opportunities=opportunities)

        except Exception as e:
            return ParserResult(
                parser_name=self.name, success=False, opportunities=[], error=str(e)
            )

    def _parse_html(self, html: str, from_email: str) -> list[OpportunityData]:
        """Parse HTML content for funding announcements"""
        # Try text parsing for now - F6S emails are often text-heavy
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text()
        return self._parse_text(text, from_email)

    def _parse_text(self, text: str, from_email: str) -> list[OpportunityData]:
        """Parse plain text content for funding announcements"""
        opportunities = []

        # Pattern to match funding announcements:
        # "$7m for Provision.com from Toronto, Canada (AI, Software) with funding from..."
        # "£500k for Patent Watch from London, UK (Health/Medical, Healthcare) with funding from..."
        # "$32m for Eden (edenmed.com) from Palo Alto, US (Diagnostics, Healthcare) with funding from..."

        # Updated pattern with non-greedy matching for company names (allows multi-word names)
        # and handles optional periods at the end
        pattern = r"([£$€][\d\.]+[kmb]?)\s+for\s+(.+?)\s+from\s+([^,]+),\s+([^\(]+)\s*\(([^\)]+)\)\s+with funding from\s+(.+?)[\.\n]"

        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            amount = match.group(1)
            company = match.group(2).strip()
            city = match.group(3).strip()
            country = match.group(4).strip()
            industries = match.group(5).strip()
            investors = match.group(6).strip()

            # Parse funding amount to USD
            amount_usd = self._parse_amount(amount)

            # Split industries
            industry_tags = [i.strip() for i in industries.split(",")]

            # Split investors
            investor_list = [i.strip() for i in re.split(r",\s*and\s+|\s+and\s+|,\s*", investors)]
            # Remove "X more" from investor list
            investor_list = [inv for inv in investor_list if not re.match(r"\d+\s+more", inv)]

            # Determine funding stage from context
            funding_stage = self._determine_stage(text, company)

            opportunity = OpportunityData(
                source="f6s",
                source_email=from_email,
                type="funding_lead",
                company=company,
                company_location=f"{city}, {country}",
                funding_stage=funding_stage,
                funding_amount=amount,
                funding_amount_usd=amount_usd,
                investors=investor_list,
                industry_tags=industry_tags,
                needs_research=True,  # Need to find career page
                raw_content=match.group(0),
            )

            opportunities.append(opportunity)

        return opportunities

    def _parse_amount(self, amount_str: str) -> float | None:
        """
        Convert funding amount string to USD float

        Examples:
        $7m -> 7000000
        £500k -> 650000 (approx)
        €10m -> 11000000 (approx)
        """
        # Remove currency symbol
        amount_str = amount_str.replace("$", "").replace("£", "").replace("€", "").strip()

        # Extract number and multiplier
        match = re.match(r"([\d\.]+)([kmb]?)", amount_str.lower())
        if not match:
            return None

        number = float(match.group(1))
        multiplier = match.group(2)

        # Apply multiplier
        if multiplier == "k":
            number *= 1000
        elif multiplier == "m":
            number *= 1000000
        elif multiplier == "b":
            number *= 1000000000

        # Simple currency conversion (rough estimates)
        currency = amount_str[0] if amount_str else "$"
        if currency == "£":
            number *= 1.3  # GBP to USD
        elif currency == "€":
            number *= 1.1  # EUR to USD

        return number

    def _determine_stage(self, text: str, company: str) -> str:
        """Determine funding stage from text context around company name"""
        # Find the section of text around this company
        company_idx = text.lower().find(company.lower())
        if company_idx == -1:
            return "Unknown"

        # Look at the 500 characters before the company mention
        context = text[max(0, company_idx - 500) : company_idx].lower()

        # Check for stage keywords
        for stage in self.stage_patterns:
            if stage in context:
                return stage.title()

        return "Unknown"

    def should_process_company(self, opportunity: OpportunityData, config: dict) -> bool:
        """
        Determine if company should be processed based on funding criteria

        Args:
            opportunity: The funding opportunity
            config: Configuration with filtering rules

        Returns:
            True if company meets criteria
        """
        # Check if filtering is enabled
        if not config.get("funding_filters", {}).get("enabled", False):
            return True

        min_amount = config.get("funding_filters", {}).get("min_amount_usd", 0)
        allowed_stages = config.get("funding_filters", {}).get("stages", [])

        # Check minimum amount
        if opportunity.funding_amount_usd and opportunity.funding_amount_usd < min_amount:
            return False

        # Check stage
        return not (
            allowed_stages
            and opportunity.funding_stage
            and opportunity.funding_stage.lower() not in [s.lower() for s in allowed_stages]
        )
