"""
Career page URL discovery system
Tries multiple strategies: pattern matching → Google search → manual input
"""

import re
from urllib.parse import urljoin, urlparse

import requests

from models import OpportunityData


class CareerPageFinder:
    """Find career page URLs for companies"""

    def __init__(self):
        self.common_patterns = [
            "/careers",
            "/jobs",
            "/job",
            "/career",
            "/work-with-us",
            "/join-us",
            "/join",
            "/opportunities",
            "/hiring",
            "/team",
            "/about/careers",
            "/company/careers",
        ]

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def find_career_page(self, opportunity: OpportunityData) -> str | None:
        """
        Find career page URL for a company

        Strategy:
        1. Try pattern matching (fast)
        2. Try Google search (if available)
        3. Return None for manual entry

        Returns:
            Career page URL or None
        """
        company = opportunity.company

        # Step 1: Try pattern matching
        print(f"\nFinding career page for: {company}")
        print("  Strategy 1: Pattern matching...")

        base_url = self._guess_company_website(company)
        if base_url:
            career_url = self._try_patterns(base_url)
            if career_url:
                print(f"  ✓ Found via pattern: {career_url}")
                return career_url

        # Step 2: Try Google search (placeholder - would need API key)
        print("  Strategy 2: Google search...")
        google_result = self._google_search(company)
        if google_result:
            print(f"  ✓ Found via Google: {google_result}")
            return google_result

        # Step 3: Manual entry needed
        print("  ✗ Could not find career page automatically")
        print("  → Manual entry required")
        return None

    def _guess_company_website(self, company_name: str) -> str | None:
        """
        Guess company website from name using 4 strategies in priority order.

        Examples:
        - "Clio (clio.com)" -> "https://clio.com"
        - "World Labs (worldlabs.ai)" -> "https://worldlabs.ai"
        - "Provision.com" -> "https://provision.com"
        - "Adaptyx Biosciences" -> "https://adaptyx.com"
        - "Anterior (formerly Co:Helm)" -> "https://anterior.com"
        - "Taalas Inc" -> "https://taalas.com"
        """
        name = company_name.strip()

        return (
            self._extract_parenthetical_domain(name)
            or self._extract_direct_domain(name)
            or self._build_from_clean_name(name)
        )

    @staticmethod
    def _extract_parenthetical_domain(name: str) -> str | None:
        """Strategy 1: Extract domain from parenthetical, e.g. 'Clio (clio.com)'."""
        paren_match = re.search(r"\(([a-z0-9][\w.-]*\.[a-z]{2,})\)", name, re.IGNORECASE)
        if paren_match:
            return f"https://{paren_match.group(1).lower()}"
        return None

    @staticmethod
    def _extract_direct_domain(name: str) -> str | None:
        """Strategy 2: Name IS a domain, e.g. 'Provision.com'."""
        if re.match(r"^[\w.-]+\.(com|io|ai|co|net|org|dev)$", name, re.IGNORECASE):
            return f"https://{name.lower()}"
        return None

    def _build_from_clean_name(self, name: str) -> str | None:
        """Strategy 3+4: Clean name + .com, with TLD probing fallback."""
        clean_name = self._clean_company_name(name)
        if not clean_name:
            return None

        url = f"https://{clean_name}.com"
        if self._validate_url(url):
            return url

        # Strategy 4: TLD probing if .com didn't validate
        return self._guess_with_tld_probing(clean_name) or url

    @staticmethod
    def _clean_company_name(name: str) -> str:
        """Clean company name for domain construction."""
        clean = name.lower()

        # Strip parenthetical content, e.g. "(formerly Co:Helm)"
        clean = re.sub(r"\s*\([^)]*\)", "", clean)

        # Strip "formerly ..." without parens
        clean = re.sub(r"\s+formerly\s+.*$", "", clean, flags=re.IGNORECASE)

        # Remove common suffixes
        clean = re.sub(
            r"\s+(inc|llc|ltd|limited|corp|corporation|gmbh|labs?)\.?$",
            "",
            clean,
            flags=re.IGNORECASE,
        )

        # Remove spaces and special characters
        clean = re.sub(r"[^a-z0-9]", "", clean)

        return clean

    def _validate_url(self, url: str) -> bool:
        """HEAD request with 5s timeout. Returns True if status < 400."""
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except Exception:
            return False

    def _guess_with_tld_probing(self, clean_name: str) -> str | None:
        """Try alternative TLDs (.io, .ai, .co) via HEAD validation."""
        for tld in (".io", ".ai", ".co"):
            url = f"https://{clean_name}{tld}"
            if self._validate_url(url):
                return url
        return None

    def _try_patterns(self, base_url: str) -> str | None:
        """Try common career page URL patterns"""
        for pattern in self.common_patterns:
            url = urljoin(base_url, pattern)

            try:
                response = self.session.get(url, timeout=5, allow_redirects=True)

                # Check if page looks like a careers page
                if response.status_code == 200 and self._is_careers_page(response.text):
                    return url

            except Exception:
                continue

        return None

    def _is_careers_page(self, html: str) -> bool:
        """Check if HTML looks like a careers page"""
        careers_keywords = [
            "career",
            "job",
            "hiring",
            "position",
            "opportunity",
            "openings",
            "join our team",
        ]

        html_lower = html.lower()

        # Check for careers keywords
        keyword_count = sum(1 for keyword in careers_keywords if keyword in html_lower)

        # Should have at least 3 keywords
        return keyword_count >= 3

    def _google_search(self, _company_name: str) -> str | None:
        """
        Search Google for company careers page

        NOTE: This is a placeholder. For production, you would:
        1. Use Google Custom Search API (requires API key)
        2. Use SerpAPI or similar service
        3. Use web scraping (unreliable, may get blocked)

        For now, returns None to trigger manual entry
        """
        # TODO: Implement Google search with API
        # Example query: f"{company_name} careers"

        return None

    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"


class ManualCareerPageCollector:
    """
    Collect career page URLs that couldn't be found automatically
    Stores them for manual review
    """

    def __init__(self, output_path: str = "data/manual_career_pages.txt"):
        self.output_path = output_path

    def add_for_manual_review(self, opportunity: OpportunityData):
        """Add company to manual review list"""
        with open(self.output_path, "a") as f:
            f.write(f"\n{'=' * 70}\n")
            f.write(f"Company: {opportunity.company}\n")
            f.write(f"Location: {opportunity.company_location}\n")
            f.write(f"Funding: {opportunity.funding_stage} - {opportunity.funding_amount}\n")
            f.write(f"Industries: {', '.join(opportunity.industry_tags or [])}\n")
            f.write(f"Investors: {', '.join(opportunity.investors or [])}\n")
            f.write(f"\nGuessed website: {self._guess_website(opportunity.company)}\n")
            f.write("Career page URL (fill this in): ____________________________\n")

        print(f"  → Added to manual review: {self.output_path}")

    def _guess_website(self, company_name: str) -> str:
        """Provide a guess for the user to check"""
        finder = CareerPageFinder()
        return finder._guess_company_website(company_name) or "Unknown"

    def load_manual_entries(self) -> dict:
        """
        Load manually entered career page URLs

        Returns:
            Dictionary of {company_name: career_url}
        """
        # TODO: Implement parser for filled-in manual entries
        # For now, returns empty dict
        return {}
