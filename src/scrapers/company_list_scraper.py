"""
Generic company list scraper for curated lists, event pages, and rankings
Extracts company data from various HTML formats using AI-powered extraction
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from models import OpportunityData  # noqa: E402 (requires sys.path insert above)


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
        logger.info("Fetching %s", url)
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
        logger.info("Extracting company data with AI...")

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
                logger.error("Unknown provider: %s", self.provider)
                return []

            # Extract JSON from response
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON array found in AI response")
                return []

            companies_data = json.loads(json_match.group(0))
            logger.info("AI extracted %d companies", len(companies_data))

            return self._convert_to_opportunities(companies_data, source_url)

        except Exception as e:
            logger.exception("AI extraction failed: %s", e)
            return []

    def _extract_with_patterns(self, soup: BeautifulSoup, source_url: str) -> list[OpportunityData]:
        """Fallback: Extract using HTML patterns (less accurate)"""
        logger.info("Extracting company data with pattern matching...")

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

        logger.info("Pattern matching found %d companies", len(companies))
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


def _load_urls(args: argparse.Namespace) -> list[str]:
    """
    Load URLs from CLI arguments and/or input file.

    Args:
        args: Parsed argparse namespace with 'url' and 'input_file' attributes

    Returns:
        List of URLs to process

    Raises:
        SystemExit: If no URLs provided via either argument
    """
    urls: list[str] = []

    if args.url:
        urls.append(args.url)

    if args.input_file:
        with open(args.input_file) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    urls.append(stripped)

    if not urls:
        logger.error("No URLs provided. Use a positional URL argument or --input-file")
        sys.exit(1)

    return urls


def _print_opportunities(opportunities: list) -> None:
    """Log extracted company details."""
    for opp in opportunities:
        parts = [f"Company: {opp.company}"]
        if opp.company_location:
            parts.append(f"Location: {opp.company_location}")
        if opp.company_website:
            parts.append(f"Website: {opp.company_website}")
        if opp.funding_stage:
            parts.append(f"Stage: {opp.funding_stage}")
        logger.info(" | ".join(parts))


def _store_to_db(all_opportunities: list) -> dict:
    """
    Store extracted companies in the database via CompanyService.

    Args:
        all_opportunities: List of OpportunityData objects to store

    Returns:
        Stats dict from CompanyService.add_companies_batch()
    """
    from api.company_service import CompanyService

    service = CompanyService()
    companies_for_db = []
    for opp in all_opportunities:
        careers_url = opp.company_website or opp.link or ""
        notes = f"Source: {opp.source}."
        if opp.description:
            notes += f" {opp.description[:200]}"
        companies_for_db.append(
            {
                "name": opp.company,
                "careers_url": careers_url,
                "notes": notes,
            }
        )

    if not companies_for_db:
        logger.info("No companies to store in database.")
        return {"added": 0, "skipped_duplicates": 0, "errors": 0, "details": []}

    return service.add_companies_batch(companies_for_db)


def _print_summary(urls: list[str], all_opportunities: list, db_stats: dict | None) -> None:
    """Log final summary of batch processing results."""
    summary = f"Summary: {len(urls)} URLs processed, {len(all_opportunities)} companies found"
    if db_stats is not None:
        summary += (
            f", {db_stats.get('added', 0)} stored"
            f", {db_stats.get('skipped_duplicates', 0)} duplicates"
            f", {db_stats.get('errors', 0)} errors"
        )
    logger.info(summary)


def _setup_logging() -> None:
    """Configure dual logging: console (INFO) + file (DEBUG with timestamps)."""
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "company_list_scraper.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ],
    )
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    """CLI entry point"""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    _setup_logging()

    parser = argparse.ArgumentParser(description="Scrape companies from curated lists")
    parser.add_argument("url", nargs="?", default=None, help="URL to scrape")
    parser.add_argument(
        "--input-file",
        help="Text file with URLs (one per line, # comments and blank lines skipped)",
    )
    parser.add_argument("--store-db", action="store_true", help="Store extracted companies in DB")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI extraction")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openrouter"],
        default="anthropic",
        help="AI provider (anthropic or openrouter, default: anthropic)",
    )

    args = parser.parse_args()

    urls = _load_urls(args)

    # Get API key from environment based on provider
    if args.provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
    else:  # openrouter
        api_key = os.getenv("OPENROUTER_API_KEY")

    use_ai = not args.no_ai and api_key is not None

    if args.no_ai:
        logger.info("AI extraction disabled, using pattern matching")
    elif not api_key:
        logger.warning(
            "%s_API_KEY not found, falling back to pattern matching", args.provider.upper()
        )
        use_ai = False

    scraper = CompanyListScraper(api_key=api_key, provider=args.provider)

    all_opportunities: list[OpportunityData] = []

    # Use tqdm progress bar for batch processing (multiple URLs)
    if len(urls) > 1:
        try:
            from tqdm import tqdm

            url_iter = tqdm(urls, desc="Scraping URLs")
        except ImportError:
            url_iter = urls
    else:
        url_iter = urls

    start_time = time.time()

    for url in url_iter:
        try:
            url_start = time.time()
            opportunities = scraper.scrape_url(url, use_ai=use_ai)
            all_opportunities.extend(opportunities)
            logger.info(
                "Scraped %d companies from %s in %.1fs",
                len(opportunities),
                url,
                time.time() - url_start,
            )
        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)
            continue

    elapsed = time.time() - start_time
    logger.info(
        "Extracted %d companies from %d URL(s) in %.1fs",
        len(all_opportunities),
        len(urls),
        elapsed,
    )

    _print_opportunities(all_opportunities)

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
            for opp in all_opportunities
        ]

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info("Saved to %s", args.output)

    # Store in DB if requested
    db_stats = None
    if args.store_db:
        db_stats = _store_to_db(all_opportunities)

    _print_summary(urls, all_opportunities, db_stats)


if __name__ == "__main__":
    main()
