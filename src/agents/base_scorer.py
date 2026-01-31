"""
Base Job Scorer
Abstract base class for job scoring with shared logic

This class provides common scoring methods used by both:
- JobScorer (hardcoded Wesley profile)
- ProfileScorer (dynamic profiles)

Shared Methods:
- _score_seniority() - Score based on seniority level (0-30)
- _score_domain() - Score based on domain keywords (0-25)
- _score_location() - Score based on location preferences (0-15)
- _score_technical_keywords() - Score based on technical keywords (0-10)
- score_job() - Main orchestration method

Abstract Methods:
- _score_role_type() - Must be implemented by subclasses (0-20 points)
  - JobScorer: Uses detailed matchers for Wes's role categories
  - ProfileScorer: Uses simple keyword matching for generic profiles
"""

import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.company_classifier import CompanyClassifier, classify_and_score_company
from utils.scoring_utils import calculate_grade

logger = logging.getLogger(__name__)


def load_role_category_keywords() -> dict:
    """Load role category keywords from config file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "filter-keywords.json"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("role_category_keywords", {})


class BaseScorer:
    """
    Abstract base class for job scoring

    Provides shared scoring logic for seniority, domain, location, and technical keywords.
    Subclasses must implement _score_role_type() for their specific role matching logic.

    Attributes:
        profile: Profile configuration dict with scoring criteria
        db: Job database connection
        role_category_keywords: Role category keywords from config
        company_classifier: Company classifier for software/hardware detection
    """

    def __init__(self, profile: dict):
        """
        Initialize base scorer with profile configuration

        Args:
            profile: Profile dict with keys:
                - target_seniority: list[str] - Seniority keywords (e.g., ["vp", "director"])
                - domain_keywords: list[str] - Domain keywords (e.g., ["robotics", "automation"])
                - role_types: dict - Role type categories
                - location_preferences: dict - Location settings
                - filtering: dict - Filtering configuration
                - (optional) technical_keywords: list[str] - Additional technical keywords
        """
        self.profile = profile
        self.db = JobDatabase()
        self.role_category_keywords = load_role_category_keywords()
        self.company_classifier = CompanyClassifier()

    def score_job(self, job: dict) -> tuple[int, str, dict, dict]:
        """
        Score a job from 0-115 with grade and breakdown

        Scoring categories:
        - Role Type: 0-20 points (subclass-specific implementation)
        - Seniority: 0-30 points
        - Domain: 0-25 points
        - Location: 0-15 points
        - Technical Keywords: 0-10 points
        - Company Classification: ±20 points (software penalty or hardware boost)

        Args:
            job: Job dict with keys: title, company, location

        Returns:
            Tuple of (score, grade, breakdown_dict, classification_metadata)
            - score: Total score (0-115)
            - grade: Letter grade (A, B, C, D, F)
            - breakdown_dict: Score breakdown by category
            - classification_metadata: Company classification details
        """
        title = job["title"].lower()
        company = job["company"].lower()
        company_display = job["company"]  # Keep original case for classification
        location = (job.get("location") or "").lower()

        breakdown = {}

        # 1. Role Type Match (0-20 points) - MUST MATCH FIRST
        # Check role type before seniority to prevent "Marketing Director" from scoring
        role_score = self._score_role_type(title)
        breakdown["role_type"] = role_score

        # 2. Seniority Match (0-30 points)
        # Score seniority independently to allow filtering by seniority alone
        seniority_score = self._score_seniority(title)
        breakdown["seniority"] = seniority_score

        # 3. Domain Match (0-25 points)
        domain_score = self._score_domain(title, company)
        breakdown["domain"] = domain_score

        # 4. Location Match (0-15 points)
        location_score = self._score_location(location)
        breakdown["location"] = location_score

        # 5. Technical Keywords (0-10 points)
        tech_score = self._score_technical_keywords(title, company)
        breakdown["technical"] = tech_score

        # 6. Company Classification Adjustment (filtering penalties/boosts)
        company_adjustment, classification_metadata = classify_and_score_company(
            company_classifier=self.company_classifier,
            company_name=company_display,
            job_title=job["title"],
            domain_keywords=self._get_domain_keywords(),
            role_types=self._get_role_types(),
            filtering_config=self._get_filtering_config(),
        )

        breakdown["company_classification"] = company_adjustment

        # Total score (max 100 + adjustments)
        total_score = sum(breakdown.values())

        # Grade (using shared utility)
        grade = calculate_grade(total_score)

        return total_score, grade, breakdown, classification_metadata

    def _score_role_type(self, title: str) -> int:
        """
        Score based on role type (0-20 points)

        ABSTRACT METHOD - Must be implemented by subclasses

        Args:
            title: Job title (lowercase)

        Returns:
            Score 0-20 based on role type match

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement _score_role_type()")

    def _score_seniority(self, title: str) -> int:
        """
        Score based on seniority level (0-30 points)

        Seniority tiers:
        - VP/C-level: 30 points
        - Director/Executive: 25 points
        - Senior Manager/Principal: 15 points
        - Manager/Lead: 10 points
        - IC roles: 0 points

        Uses word boundary matching to avoid false positives
        (e.g., "vp" won't match "supervisor").

        NOTE: This method scores based on title keywords alone, NOT target_seniority.
        The target_seniority profile field is used by other methods (filtering, etc.)

        Args:
            title: Job title (lowercase)

        Returns:
            Score 0-30 based on seniority level
        """
        # VP/C-level keywords (30 points)
        if self._has_any_keyword(title, ["vp", "vice president", "chief", "cto", "cpo", "head of"]):
            return 30

        # Director/Executive (25 points)
        if self._has_any_keyword(title, ["director", "executive director"]):
            return 25

        # Senior Manager/Principal (15 points)
        if self._has_any_keyword(title, ["senior manager", "principal", "staff", "senior"]):
            return 15

        # Manager/Lead (10 points)
        if self._has_any_keyword(title, ["manager", "lead", "leadership"]):
            return 10

        # IC roles (0 points)
        return 0

    def _score_domain(self, title: str, company: str) -> int:
        """
        Score based on domain keyword matches (0-25 points)

        Scoring:
        - 3+ keyword matches: 25 points
        - 2 keyword matches: 20 points
        - 1 keyword match: 15 points
        - Engineering/product generic: 10 points
        - Default: 5 points

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)

        Returns:
            Score 0-25 based on domain match
        """
        text = f"{title} {company}"
        domain_keywords = self._get_domain_keywords()

        # Count domain keyword matches
        matches = sum(1 for kw in domain_keywords if kw in text)

        # More matches = higher score
        if matches >= 3:
            return 25
        elif matches >= 2:
            return 20
        elif matches >= 1:
            return 15
        elif "engineering" in text or "product" in text:
            return 10
        return 5

    def _score_location(self, location: str) -> int:
        """
        Score based on location preferences (0-15 points)

        Scoring:
        - Remote: 15 points
        - Hybrid + preferred city/region: 15 points
        - Preferred city: 12 points
        - Preferred region: 8 points
        - Other: 0 points

        Args:
            location: Location string (any case)

        Returns:
            Score 0-15 based on location match
        """
        if not location:
            return 0

        location_lower = location.lower()
        prefs = self._get_location_preferences()

        remote_keywords = prefs.get("remote_keywords", ["remote", "wfh", "anywhere"])
        hybrid_keywords = prefs.get("hybrid_keywords", ["hybrid"])
        preferred_cities = prefs.get("preferred_cities", [])
        preferred_regions = prefs.get("preferred_regions", [])

        # Check for remote (15 points)
        if any(kw in location_lower for kw in remote_keywords):
            return 15

        # Check for hybrid
        is_hybrid = any(kw in location_lower for kw in hybrid_keywords)

        # Check for preferred cities
        in_preferred_city = any(city in location_lower for city in preferred_cities)

        # Check for preferred regions
        in_preferred_region = any(region in location_lower for region in preferred_regions)

        # Scoring logic
        if is_hybrid and (in_preferred_city or in_preferred_region):
            return 15
        elif in_preferred_city:
            return 12
        elif in_preferred_region:
            return 8
        return 0

    def _score_technical_keywords(self, title: str, company: str) -> int:
        """
        Score based on technical keyword matches (0-10 points)

        Gives +2 points per matching technical keyword (max 10).

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)

        Returns:
            Score 0-10 based on technical keyword matches
        """
        text = f"{title} {company}".lower()
        domain_keywords = self._get_domain_keywords()

        score = 0
        for keyword in domain_keywords:
            if keyword in text:
                score += 2
                if score >= 10:
                    break

        return min(score, 10)

    # ========== Utility Methods ==========

    def _has_keyword(self, text: str, keyword: str) -> bool:
        """
        Check if keyword exists in text at word boundaries

        Handles special cases like "VP," "VP-" "VP " etc.
        Uses regex word boundaries to prevent false matches:
        - "vp" won't match "supervisor"
        - "chief" won't match "mischief"

        Args:
            text: Text to search in (lowercase)
            keyword: Keyword to search for (lowercase)

        Returns:
            True if keyword found at word boundary
        """
        # Use word boundary regex: \b ensures we match whole words
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text))

    def _has_any_keyword(self, text: str, keywords: list[str]) -> bool:
        """
        Check if any keyword from list exists in text at word boundaries

        Args:
            text: Text to search in (lowercase)
            keywords: List of keywords to search for (lowercase)

        Returns:
            True if any keyword found
        """
        return any(self._has_keyword(text, keyword) for keyword in keywords)

    def _count_keyword_matches(self, text: str, keywords: list[str]) -> int:
        """
        Count how many keywords from list appear in text

        Args:
            text: Text to search in
            keywords: List of keywords to count

        Returns:
            Number of matching keywords
        """
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw.lower() in text_lower)

    def _is_leadership_title(self, title_lower: str) -> bool:
        """
        Check if title indicates leadership position

        Args:
            title_lower: Job title in lowercase

        Returns:
            True if title contains leadership keywords
        """
        leadership_keywords = ["vp", "director", "head", "chief", "executive"]
        return any(self._has_keyword(title_lower, kw) for kw in leadership_keywords)

    # ========== Profile Accessors ==========
    # These helper methods allow both dict-based and Profile object-based access

    def _get_target_seniority(self) -> list[str]:
        """Get target seniority keywords from profile"""
        if hasattr(self.profile, "get_target_seniority"):
            # Profile object (ProfileScorer)
            return self.profile.get_target_seniority()
        # Dict-based (JobScorer)
        return self.profile.get("target_seniority", [])

    def _get_domain_keywords(self) -> list[str]:
        """Get domain keywords from profile"""
        if hasattr(self.profile, "get_domain_keywords"):
            # Profile object (ProfileScorer)
            return self.profile.get_domain_keywords()
        # Dict-based (JobScorer)
        return self.profile.get("domain_keywords", [])

    def _get_location_preferences(self) -> dict:
        """Get location preferences from profile"""
        if hasattr(self.profile, "get_location_preferences"):
            # Profile object (ProfileScorer)
            return self.profile.get_location_preferences()
        # Dict-based (JobScorer)
        return self.profile.get("location_preferences", {})

    def _get_role_types(self) -> dict:
        """Get role types from profile"""
        if hasattr(self.profile, "scoring"):
            # Profile object (ProfileScorer)
            return self.profile.scoring.get("role_types", {})
        # Dict-based (JobScorer)
        return self.profile.get("role_types", {})

    def _get_filtering_config(self) -> dict:
        """Get filtering configuration from profile"""
        if hasattr(self.profile, "scoring"):
            # Profile object (ProfileScorer)
            return self.profile.scoring.get("filtering", {})
        # Dict-based (JobScorer)
        return self.profile.get("filtering", {})
