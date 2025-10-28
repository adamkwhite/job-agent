"""
Generic company list scraper for curated lists, event pages, and rankings
Extracts company data from various HTML formats using AI-powered extraction
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from models import OpportunityData


class CompanyListScraper:
    """Generic scraper for company lists from various sources"""

    def __init__(
        self,
        api_key: str | None = None,
        provider: Literal["anthropic", "openrouter"] = "anthropic",
    ):
        """
        Initialize scraper with optional AI provider

        Args:
            api_key: API key for AI extraction
            provider: AI provider - "anthropic" or "openrouter"
        """
        self.api_key = api_key
        self.provider = provider
        self.client = None

        if api_key:
            if provider == "anthropic" and anthropic:
                self.client = anthropic.Anthropic(api_key=api_key)
            elif provider == "openrouter" and OpenAI:
                # OpenRouter uses OpenAI-compatible API
                self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    def scrape_url(self, url: str, use_ai: bool = True) -> list[OpportunityData]:
        """
        Scrape companies from a URL

        Args:
            url: URL to scrape
            use_ai: Use AI to extract structured data (default: True)

        Returns:
            List of OpportunityData objects with type="company_research"
        """
        print(f"Fetching {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        html_content = response.text
        soup = BeautifulSoup(html_content, "lxml")

        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract main content text
        main_text = soup.get_text(separator="\n", strip=True)

        if use_ai and self.api_key:
            return self._extract_with_ai(main_text, url)
        else:
            return self._extract_with_patterns(soup, url)

    def _extract_with_ai(self, text: str, source_url: str) -> list[OpportunityData]:
        """Use Claude to extract structured company data from text"""
        print("Extracting company data with AI...")

        # Truncate text if too long (keep first 50k chars)
        if len(text) > 50000:
            text = text[:50000] + "\n\n[Content truncated...]"

        prompt = f"""Extract all companies from this list. For each company, provide:
- company_name (required)
- website (if mentioned)
- location (city/country if mentioned)
- funding_stage (e.g., Seed, Series A, etc. if mentioned)
- description (brief 1-sentence description)

Return ONLY a valid JSON array of companies. Example format:
[
  {{
    "company_name": "Acme Corp",
    "website": "https://acme.com",
    "location": "Toronto, Canada",
    "funding_stage": "Series A",
    "description": "AI-powered robotics company"
  }}
]

Content to extract from:
{text}
"""

        try:
            if self.provider == "anthropic" and self.client:
                # Anthropic API
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = message.content[0].text

            elif self.provider == "openrouter" and self.client:
                # OpenRouter API (OpenAI-compatible)
                completion = self.client.chat.completions.create(
                    model="anthropic/claude-3.5-sonnet",  # OpenRouter model name
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = completion.choices[0].message.content

            else:
                print(f"Unknown provider: {self.provider}")
                return []

            # Extract JSON from response
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if not json_match:
                print("No JSON array found in AI response")
                return []

            companies_data = json.loads(json_match.group(0))
            print(f"AI extracted {len(companies_data)} companies")

            return self._convert_to_opportunities(companies_data, source_url)

        except Exception as e:
            print(f"AI extraction failed: {e}")
            return []

    def _extract_with_patterns(self, soup: BeautifulSoup, source_url: str) -> list[OpportunityData]:
        """Fallback: Extract using HTML patterns (less accurate)"""
        print("Extracting company data with pattern matching...")

        companies: list[dict] = []

        # Find all headings - try multiple levels
        all_headings = soup.find_all(["h2", "h3", "h4"])

        for heading in all_headings:
            heading_text = heading.get_text(strip=True)

            # Check if this is a numbered company heading (e.g., "1. Company Name")
            if not re.match(r"^[\d]+\.?\s+[A-Za-z]", heading_text):
                continue

            # Extract company name (remove number prefix)
            company_name = re.sub(r"^[\d]+\.?\s+", "", heading_text).strip()

            # Skip common non-company headings
            if company_name.lower() in [
                "conclusion",
                "introduction",
                "overview",
                "summary",
                "table of contents",
            ]:
                continue

            details: dict[str, str] = {"company_name": company_name}

            # Find following paragraphs for details
            current = heading.find_next_sibling()
            paragraph_count = 0

            while current and paragraph_count < 20:  # Look at next 20 siblings
                if current.name in ["h2", "h3", "h4"]:
                    # Stop at next heading
                    break

                if current.name == "p":
                    paragraph_count += 1
                    text = current.get_text(strip=True)

                    # Extract structured data with strong labels
                    for label, field in [("Location", "location"), ("Place", "location")]:
                        if f"{label}:" in text:
                            match = re.search(rf"{label}:\s*([^.\n]+)", text)
                            if match:
                                details[field] = match.group(1).strip()

                    for label, field in [("Stage", "funding_stage"), ("Phase", "funding_stage")]:
                        if f"{label}:" in text:
                            match = re.search(rf"{label}:\s*([^.\n]+)", text)
                            if match:
                                details[field] = match.group(1).strip()

                    # Look for website links (exclude social media)
                    if "website" not in details:
                        links = current.find_all("a", href=True)
                        for link in links:
                            href = link.get("href", "")

                            # Skip social media
                            if any(
                                x in href.lower()
                                for x in [
                                    "crunchbase",
                                    "linkedin",
                                    "twitter",
                                    "facebook",
                                    "instagram",
                                ]
                            ):
                                continue

                            # Clean up the URL
                            if href.startswith("http"):
                                details["website"] = href.split("?")[0]  # Remove query params
                            elif href.startswith("www."):
                                details["website"] = f"https://{href}"
                            break

                    # Capture description from long paragraphs
                    if (
                        "description" not in details
                        and 80 < len(text) < 800
                        and text.count(":") <= 1
                    ):
                        details["description"] = text

                current = current.find_next_sibling()

            # Only add if we found at least a company name
            if details.get("company_name"):
                companies.append(details)

        print(f"Pattern matching found {len(companies)} companies")
        return self._convert_to_opportunities(companies, source_url)

    def _convert_to_opportunities(
        self, companies_data: list[dict], source_url: str
    ) -> list[OpportunityData]:
        """Convert extracted company data to OpportunityData objects"""
        opportunities = []

        for company in companies_data:
            if not company.get("company_name"):
                continue

            opportunity = OpportunityData(
                type="funding_lead",  # Company research leads
                title="",  # No specific job title
                company=company["company_name"],
                location=company.get("location", ""),
                link=company.get("website", ""),
                description=company.get("description", ""),
                salary="",
                job_type="",
                posted_date="",
                source=f"company_list:{self._extract_domain(source_url)}",
                source_email="",
                received_at=datetime.now().isoformat(),
                keywords_matched=[],
                raw_content=json.dumps(company),
                # Funding information
                funding_stage=company.get("funding_stage", ""),
                company_website=company.get("website", ""),
                company_location=company.get("location", ""),
            )

            opportunities.append(opportunity)

        return opportunities

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL"""
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else "unknown"


def main():
    """CLI entry point"""
    import argparse
    import os

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="Scrape companies from curated lists")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI extraction")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter"],
        default="anthropic",
        help="AI provider (anthropic or openrouter, default: anthropic)",
    )

    args = parser.parse_args()

    # Get API key from environment based on provider
    if args.provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
    else:  # openrouter
        api_key = os.getenv("OPENROUTER_API_KEY")

    use_ai = not args.no_ai and api_key is not None

    if args.no_ai:
        print("AI extraction disabled, using pattern matching")
    elif not api_key:
        print(
            f"Warning: {args.provider.upper()}_API_KEY not found, falling back to pattern matching"
        )
        use_ai = False

    scraper = CompanyListScraper(api_key=api_key, provider=args.provider)

    try:
        opportunities = scraper.scrape_url(args.url, use_ai=use_ai)

        print(f"\n{'='*70}")
        print(f"Extracted {len(opportunities)} companies")
        print(f"{'='*70}\n")

        for opp in opportunities:
            print(f"Company: {opp.company}")
            if opp.company_location:
                print(f"  Location: {opp.company_location}")
            if opp.company_website:
                print(f"  Website: {opp.company_website}")
            if opp.funding_stage:
                print(f"  Stage: {opp.funding_stage}")
            if opp.description:
                print(f"  Description: {opp.description[:100]}...")
            print()

        # Save to JSON if requested
        if args.output:
            output_data = [
                {
                    "company": opp.company,
                    "website": opp.company_website,
                    "location": opp.company_location,
                    "funding_stage": opp.funding_stage,
                    "description": opp.description,
                    "source": opp.source,
                }
                for opp in opportunities
            ]

            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)

            print(f"Saved to {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
