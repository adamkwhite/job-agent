"""
Company Matcher - Fuzzy matching to prevent duplicate companies

Uses fuzzy string matching to determine if a discovered company
already exists in the database with a similar name or URL.
"""

import re
from urllib.parse import urlparse

from rapidfuzz import fuzz


class CompanyMatcher:
    """Fuzzy matching for company names and URLs"""

    def __init__(self, similarity_threshold: float = 90.0):
        """
        Initialize company matcher

        Args:
            similarity_threshold: Minimum similarity score (0-100) to consider a match.
                                 Default is 90 (very strict)
        """
        self.similarity_threshold = similarity_threshold

    def find_match(self, candidate_company: dict, existing_companies: list[dict]) -> dict | None:
        """
        Find if candidate company matches any existing company

        Args:
            candidate_company: Dict with 'name' and 'careers_url'
            existing_companies: List of dicts with 'name' and 'careers_url'

        Returns:
            Matching company dict if found, None otherwise
        """
        candidate_name = candidate_company.get("name", "")
        candidate_url = candidate_company.get("careers_url", "")

        if not candidate_name or not candidate_url:
            return None

        # Normalize candidate
        norm_candidate_name = self._normalize_company_name(candidate_name)
        norm_candidate_url = self._normalize_url(candidate_url)

        # Check each existing company
        for existing in existing_companies:
            existing_name = existing.get("name", "")
            existing_url = existing.get("careers_url", "")

            if not existing_name or not existing_url:
                continue

            # Normalize existing
            norm_existing_name = self._normalize_company_name(existing_name)
            norm_existing_url = self._normalize_url(existing_url)

            # Check URL match first (more reliable)
            url_similarity = fuzz.ratio(norm_candidate_url, norm_existing_url)
            if url_similarity >= self.similarity_threshold:
                print(
                    f"  [MATCH] URL similarity: {url_similarity:.1f}% - {candidate_url} ≈ {existing_url}"
                )
                return existing

            # Check name match
            name_similarity = fuzz.ratio(norm_candidate_name, norm_existing_name)
            if name_similarity >= self.similarity_threshold:
                print(
                    f"  [MATCH] Name similarity: {name_similarity:.1f}% - {candidate_name} ≈ {existing_name}"
                )
                return existing

        return None

    def deduplicate_companies(self, companies: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Remove duplicate companies from a list

        Args:
            companies: List of company dicts

        Returns:
            Tuple of (unique_companies, duplicates_found)
        """
        unique: list[dict] = []
        duplicates: list[dict] = []

        for company in companies:
            # Check if this company matches any in the unique list
            match = self.find_match(company, unique)

            if match:
                duplicates.append(company)
            else:
                unique.append(company)

        if duplicates:
            print(
                f"\n[CompanyMatcher] Found {len(duplicates)} duplicates within discovered companies"
            )

        return unique, duplicates

    def _normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for comparison

        Handles:
        - Lowercasing
        - Removing punctuation
        - Removing common suffixes (Inc, LLC, Ltd, Corp, Co, etc.)
        - Removing extra whitespace

        Examples:
            "Boston Dynamics Inc." -> "boston dynamics"
            "Agility Robotics, LLC" -> "agility robotics"
        """
        if not name:
            return ""

        # Lowercase
        normalized = name.lower()

        # Remove common company suffixes
        suffixes = [
            r"\binc\.?",
            r"\bllc\.?",
            r"\bltd\.?",
            r"\bcorp\.?",
            r"\bcorporation",
            r"\bco\.?",
            r"\bcompany",
            r"\blimited",
            r"\bincorporated",
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)

        # Remove punctuation except spaces
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def _normalize_url(self, url: str) -> str:
        """
                Normalize URL for comparison

                Handles:
                - Lowercasing
                - Removing protocol (http vs https)
                - Removing trailing slashes
                - Removing www. prefix
                - Removing query parameters and fragments

                Examples:
                    "https://www.bostondy

        namics.com/careers/" -> "bostondynamics.com/careers"
                    "http://careers.agility.io?utm=source" -> "careers.agility.io"
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)

            # Extract domain and path
            domain = parsed.netloc.lower()
            path = parsed.path.rstrip("/")

            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            # Combine domain and path
            normalized = f"{domain}{path}"

            return normalized

        except Exception:
            # Fallback: just lowercase and strip
            return url.lower().strip().rstrip("/")
