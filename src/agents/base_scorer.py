"""
Base Job Scorer
Abstract base class for job scoring with shared logic

ProfileScorer extends this class with role-type matching.
All scoring features are profile-configurable via optional fields.

Shared Methods:
- _score_seniority() - Score based on seniority level (0-30)
- _score_domain() - Score based on domain keywords (0-25)
- _score_location() - Score based on location preferences (0-15)
- _score_technical_keywords() - Score based on technical keywords (0-10)
- score_job() - Main orchestration method

Abstract Methods:
- _score_role_type() - Must be implemented by subclasses (0-20 points)
"""

import copy
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.company_classifier import CompanyClassifier, classify_and_score_company
from utils.keyword_matcher import KeywordMatcher
from utils.scoring_utils import calculate_grade

logger = logging.getLogger(__name__)


# Seniority Hierarchy (Issue #244 - Relative Seniority Scoring)
# Maps career progression levels (0=Junior → 8=C-level)
SENIORITY_HIERARCHY: dict[int, list[str]] = {
    0: ["junior", "entry level", "entry-level", "associate", "intern", "co-op", "trainee"],
    1: ["mid-level", "engineer", "analyst", "specialist", "developer"],  # IC without "senior"
    2: ["senior", "staff", "principal", "sr"],
    3: ["lead", "team lead", "tech lead", "technical lead"],
    4: ["architect", "distinguished", "fellow"],
    5: ["manager", "engineering manager", "people manager"],
    6: ["director", "senior manager", "group manager"],
    7: ["vp", "vice president", "head of", "executive director"],
    8: ["chief", "cto", "cpo", "ceo", "cfo", "coo"],
}


def load_role_category_keywords() -> dict:
    """Load role category keywords from config file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "filter-keywords.json"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("role_category_keywords", {})


def load_location_settings() -> dict:
    """Load location restriction patterns from config file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "location-settings.json"
    with open(config_path) as f:
        return json.load(f)


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

    def __init__(self, profile):
        """
        Initialize base scorer with profile configuration

        Args:
            profile: Profile object with scoring criteria
        """
        # Deep copy profile to prevent test mutation bugs
        # Tests that modify scorer.profile["filtering"]["aggression_level"]
        # would otherwise mutate the shared module-level WES_PROFILE dict
        self.profile = copy.deepcopy(profile)
        self.db = JobDatabase()
        self.role_category_keywords = load_role_category_keywords()
        self.company_classifier = CompanyClassifier()
        self.location_settings = load_location_settings()

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
        description = job.get("description", "")

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
        domain_score = self._score_domain(title, company, description)
        breakdown["domain"] = domain_score

        # 4. Location Match (0-15 points)
        location_score = self._score_location(location, description)
        breakdown["location"] = location_score

        # 5. Technical Keywords (0-10 points)
        tech_score = self._score_technical_keywords(title, company, description)
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
        Score based on seniority match to target (0-30 points) - RELATIVE SCORING

        This method uses **relative scoring** based on the candidate's target_seniority
        preferences. Jobs matching the candidate's target level receive maximum points.

        Scoring Logic:
        - Perfect match to target level: 30 points
        - One level away (above or below): 25 points
        - Two levels away: 15 points
        - Three levels away: 10 points
        - Four+ levels away: 5 points

        Fallback: If target_seniority is empty, uses absolute scoring (old behavior).

        Args:
            title: Job title (any case)

        Returns:
            Score 0-30 based on seniority match to target

        Examples:
            Mario (targets "senior, staff, lead"):
                "Senior QA Engineer" → 30pts (perfect match to level 2)
                "Lead QA Engineer" → 30pts (perfect match to level 3)
                "QA Manager" → 25pts (one level up: 5 vs 3)
                "Director of QA" → 15pts (three levels up: 6 vs 3)

            Wes (targets "director, vp, head of"):
                "Director of Engineering" → 30pts (perfect match to level 6)
                "VP Engineering" → 30pts (perfect match to level 7)
                "Senior Manager" → 25pts (one level down: 6 vs 6)
        """
        target_seniority = self._get_target_seniority()

        # Fallback to absolute scoring if no target specified
        if not target_seniority:
            return self._score_seniority_absolute(title)

        # Detect job seniority level
        job_level = self._detect_seniority_level(title)
        if job_level == -1:
            return 0  # No seniority keywords found

        # Detect all target levels
        target_levels = self._detect_all_target_levels(target_seniority)
        if not target_levels:
            # Target seniority specified but doesn't map to hierarchy
            return self._score_seniority_absolute(title)

        # Check if job level matches ANY target level (perfect match)
        if job_level in target_levels:
            return 30

        # Calculate minimum distance to nearest target level
        min_distance = min(abs(job_level - target_level) for target_level in target_levels)

        # Score based on distance
        if min_distance == 1:
            return 25  # One level away (stretch or slightly junior)
        if min_distance == 2:
            return 15  # Two levels away
        if min_distance == 3:
            return 10  # Three levels away
        return 5  # Four+ levels away (major mismatch)

    def _score_seniority_absolute(self, title: str) -> int:
        """
        LEGACY: Score based on absolute seniority level (0-30 points)

        This is the old absolute scoring logic used as a fallback when
        target_seniority is not specified in the profile.

        Seniority tiers:
        - VP/C-level: 30 points
        - Director/Executive: 25 points
        - Senior Manager/Principal: 15 points
        - Manager/Lead: 10 points
        - IC roles: 0 points

        Args:
            title: Job title (any case)

        Returns:
            Score 0-30 based on absolute seniority level
        """
        title_lower = title.lower()

        # VP/C-level keywords (30 points)
        if self._has_any_keyword(
            title_lower, ["vp", "vice president", "chief", "cto", "cpo", "head of"]
        ):
            return 30

        # Director/Executive (25 points)
        if self._has_any_keyword(title_lower, ["director", "executive director"]):
            return 25

        # Senior Manager/Principal (15 points)
        if self._has_any_keyword(title_lower, ["senior manager", "principal", "staff", "senior"]):
            return 15

        # Manager/Lead (10 points)
        if self._has_any_keyword(title_lower, ["manager", "lead", "leadership"]):
            return 10

        # IC roles (0 points)
        return 0

    def _score_domain(self, title: str, company: str, description: str = "") -> int:
        """
        Score based on domain keyword matches (0-25 points)

        If domain_tiers is configured, uses tiered matching (tier1=25, tier2=20, tier3=15).
        Otherwise, uses count-based matching (3+=25, 2=20, 1=15).

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)
            description: Job description text (optional, for enriched jobs)

        Returns:
            Score 0-25 based on domain match
        """
        text = f"{title} {company}"
        if description:
            text = f"{text} {description.lower()}"
        domain_tiers = self._get_domain_tiers()

        if domain_tiers:
            return self._score_domain_tiered(text, domain_tiers)

        domain_keywords = self._get_domain_keywords()
        matches = sum(1 for kw in domain_keywords if kw in text)

        if matches >= 3:
            return 25
        elif matches >= 2:
            return 20
        elif matches >= 1:
            return 15
        elif "engineering" in text or "product" in text:
            return 10
        return 5

    def _score_domain_tiered(self, text: str, tiers: dict[str, list[str]]) -> int:
        """
        Score domain using tiered keyword lists

        Checks highest-value tier first and returns on first match.

        Args:
            text: Combined title + company text
            tiers: Dict with tier1/tier2/tier3 keyword lists

        Returns:
            Score 5-25 based on tier match
        """
        tier_scores = [
            (tiers.get("tier1", []), 25),
            (tiers.get("tier2", []), 20),
            (tiers.get("tier3", []), 15),
        ]
        for keywords, score in tier_scores:
            if any(kw in text for kw in keywords):
                return score

        return 10 if "engineering" in text else 5

    def _score_location(self, location: str, description: str = "") -> int:
        """
        Score based on location preferences (0-15 points)

        Scoring:
        - Remote (unrestricted): 15 points
        - Remote (country-restricted, if enabled): 0 points
        - Hybrid + preferred city/region: 15 points
        - Preferred city: 12 points
        - Preferred region: 8 points
        - Other: 0 points

        Args:
            location: Location string (any case)
            description: Job description for country restriction check

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

        # Check for remote (15 points - but verify no country restrictions if enabled)
        if any(kw in location_lower for kw in remote_keywords):
            if (
                self._is_country_restriction_enabled()
                and self._get_candidate_country()
                and self._is_country_restricted(location, description)
            ):
                return 0
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

    def _score_technical_keywords(self, title: str, company: str, description: str = "") -> int:
        """
        Score based on technical keyword matches (0-10 points)

        Gives +2 points per matching technical keyword (max 10).
        Uses dedicated technical_keywords if configured, else falls back to domain_keywords.
        When technical_keywords is explicitly set, uses word boundary matching.

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)
            description: Job description text (optional, for enriched jobs)

        Returns:
            Score 0-10 based on technical keyword matches
        """
        text = f"{title} {company}".lower()
        if description:
            text = f"{text} {description.lower()}"
        tech_keywords = self._get_technical_keywords()
        use_word_boundary = self._has_explicit_technical_keywords()

        score = 0
        for keyword in tech_keywords:
            matched = self._has_keyword(text, keyword) if use_word_boundary else keyword in text
            if matched:
                score += 2
                if score >= 10:
                    break

        return min(score, 10)

    # ========== Utility Methods ==========

    def _has_keyword(self, text: str, keyword: str) -> bool:
        """
        Check if keyword exists in text at word boundaries

        Uses KeywordMatcher with word boundary mode to prevent false matches:
        - "vp" won't match "supervisor"
        - "chief" won't match "mischief"

        Args:
            text: Text to search in (lowercase)
            keyword: Keyword to search for (lowercase)

        Returns:
            True if keyword found at word boundary
        """
        matcher = KeywordMatcher([keyword])
        return matcher.has_any(text, mode="word_boundary")

    def _has_any_keyword(self, text: str, keywords: list[str]) -> bool:
        """
        Check if any keyword from list exists in text at word boundaries

        Uses KeywordMatcher with word boundary mode.

        Args:
            text: Text to search in (lowercase)
            keywords: List of keywords to search for (lowercase)

        Returns:
            True if any keyword found
        """
        matcher = KeywordMatcher(keywords)
        return matcher.has_any(text, mode="word_boundary")

    def _count_keyword_matches(self, text: str, keywords: list[str]) -> int:
        """
        Count how many keywords from list appear in text

        Uses KeywordMatcher with substring mode for flexible matching.

        Args:
            text: Text to search in
            keywords: List of keywords to count

        Returns:
            Number of matching keywords
        """
        matcher = KeywordMatcher(keywords)
        return matcher.count_matches(text, mode="substring")

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

    # ========== Country Restriction Methods ==========

    def _is_country_restricted(self, location: str, description: str = "") -> bool:
        """
        Check if remote job is restricted to specific countries (excluding candidate's)

        Args:
            location: Location string
            description: Job description text

        Returns:
            True if job is country-restricted (e.g., US-only for Canadian candidates)
        """
        if not location:
            return False

        location_lower = location.lower()
        description_lower = description.lower() if description else ""
        patterns = self.location_settings.get("country_restriction_patterns", {})

        if self._is_canada_friendly(location_lower, description_lower, patterns):
            return False
        return self._is_us_only(
            location_lower, description_lower, patterns
        ) or self._has_us_state_in_remote(location_lower, patterns)

    def _is_canada_friendly(
        self, location_lower: str, description_lower: str, patterns: dict
    ) -> bool:
        """Check if job explicitly welcomes Canadian candidates."""
        canada_friendly = patterns.get("canada_friendly", [])
        return any(p in location_lower or p in description_lower for p in canada_friendly)

    def _is_us_only(self, location_lower: str, description_lower: str, patterns: dict) -> bool:
        """Check if job is restricted to US-only."""
        us_only_patterns = patterns.get("us_only", [])
        return any(p in location_lower or p in description_lower for p in us_only_patterns)

    def _has_us_state_in_remote(self, location_lower: str, patterns: dict) -> bool:
        """Check if remote job mentions a specific US state/city."""
        if not any(kw in location_lower for kw in ["remote", "work from home", "wfh"]):
            return False
        us_states = patterns.get("us_states", [])
        return any(
            f" {state} " in f" {location_lower} " or location_lower.endswith(f" {state}")
            for state in us_states
        )

    # ========== Keyword Bonus ==========

    def _calculate_keyword_bonus(self, title: str, category: str | None) -> int:
        """
        Calculate bonus points from keyword matches in config (max +2)

        Args:
            title: Job title (original case)
            category: Role category (engineering_leadership, product_leadership, etc.)

        Returns:
            Bonus points 0-2
        """
        if not category:
            return 0

        if category not in self.role_category_keywords:
            logger.warning(
                f"Role category '{category}' not found in config/filter-keywords.json. "
                f"Job '{title}' will not receive keyword-based bonus points. "
                f"Please add '{category}' to 'role_category_keywords' section in config."
            )
            return 0

        category_keywords = self.role_category_keywords[category]
        must_kw = category_keywords.get("must_keywords", [])
        nice_kw = category_keywords.get("nice_keywords", [])

        must_matches = self._count_keyword_matches(title, must_kw)
        nice_matches = self._count_keyword_matches(title, nice_kw)

        return (must_matches + nice_matches) * 2

    # ========== Profile Accessors ==========

    def _get_target_seniority(self) -> list[str]:
        """Get target seniority keywords from profile"""
        return self.profile.get_target_seniority()

    def _get_domain_keywords(self) -> list[str]:
        """Get domain keywords from profile"""
        return self.profile.get_domain_keywords()

    def _get_location_preferences(self) -> dict:
        """Get location preferences from profile"""
        return self.profile.get_location_preferences()

    def _get_candidate_country(self) -> str | None:
        """Get candidate's country from profile"""
        return self.profile.scoring.get("candidate_country")

    def _is_country_restriction_enabled(self) -> bool:
        """Check if country restriction filtering is enabled"""
        prefs = self._get_location_preferences()
        return prefs.get("country_restriction_enabled", False)

    def _get_domain_tiers(self) -> dict | None:
        """Get tiered domain keywords if configured"""
        return self.profile.scoring.get("domain_tiers")

    def _get_technical_keywords(self) -> list[str]:
        """Get technical keywords (falls back to domain_keywords)"""
        explicit = self.profile.scoring.get("technical_keywords")
        return explicit if explicit else self._get_domain_keywords()

    def _has_explicit_technical_keywords(self) -> bool:
        """Check if profile has explicit technical_keywords configured"""
        return self.profile.scoring.get("technical_keywords") is not None

    # ========== Seniority Detection Helpers (Issue #244) ==========

    def _detect_seniority_level(self, title: str) -> int:
        """
        Detect seniority level from job title using hierarchy mapping

        Uses word boundary matching to avoid false positives.
        For titles with multiple seniority keywords, returns the highest level.

        Args:
            title: Job title (any case)

        Returns:
            Seniority level 0-8, or -1 if no seniority keywords found

        Examples:
            "Senior Software Engineer" → 2 (senior)
            "Director of Engineering" → 6 (director)
            "VP of Product" → 7 (vp)
            "Senior Manager" → 6 (manager wins over senior due to higher level)
        """
        title_lower = title.lower()
        highest_level = -1

        for level, keywords in SENIORITY_HIERARCHY.items():
            for keyword in keywords:
                # Word boundary matching to avoid false positives
                pattern = r"\b" + re.escape(keyword) + r"\b"
                if re.search(pattern, title_lower):
                    highest_level = max(highest_level, level)

        return highest_level

    def _detect_all_target_levels(self, target_seniority: list[str]) -> list[int]:
        """
        Detect all seniority levels from target_seniority list

        Args:
            target_seniority: List of target seniority keywords

        Returns:
            List of seniority levels (0-8) found in target keywords

        Examples:
            ["senior", "staff"] → [2] (both map to level 2)
            ["senior", "lead", "director"] → [2, 3, 6]
            [] → []
        """
        if not target_seniority:
            return []

        levels = set()
        for target_kw in target_seniority:
            target_lower = target_kw.lower().strip()
            for level, keywords in SENIORITY_HIERARCHY.items():
                if target_lower in keywords:
                    levels.add(level)

        return sorted(levels)

    def _get_role_types(self) -> dict:
        """Get role types from profile"""
        return self.profile.scoring.get("role_types", {})

    def _get_filtering_config(self) -> dict:
        """Get filtering configuration from profile"""
        return self.profile.scoring.get("filtering", {})
