"""
Job Scoring Agent
Evaluates job opportunities against candidate profile

⚠️ IMPORTANT: When updating scoring criteria in this file:
1. Update the email template in src/send_profile_digest.py (scoring explanation in email footer)
2. Update profile JSON files (profiles/wes.json, profiles/adam.json) if scoring weights change
3. Update CLAUDE.md documentation if categories/ranges change
4. Consider running src/rescore_all_jobs.py to re-evaluate historical data

NOTE: This is the legacy scorer with Wesley's hardcoded profile.
For multi-profile support, use ProfileScorer instead.

Extends BaseScorer with Wesley-specific role matching and country restriction logic.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_scorer import BaseScorer
from database import JobDatabase

logger = logging.getLogger(__name__)


def load_location_settings() -> dict:
    """Load location restriction patterns from config file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "location-settings.json"
    with open(config_path) as f:
        return json.load(f)


# Wesley's hardcoded profile configuration
WES_PROFILE = {
    "target_seniority": ["vp", "director", "head of", "executive", "chief", "cto", "cpo"],
    "domain_keywords": [
        "robotics",
        "automation",
        "iot",
        "hardware",
        "medtech",
        "medical device",
        "mechatronics",
        "embedded",
        "firmware",
        "mechanical",
        "physical product",
        "manufacturing",
        "supply chain",
        "dfm",
        "dfa",
        "industrial",
    ],
    "role_types": {
        "engineering_leadership": ["engineering", "r&d", "technical", "hardware"],
        "product_leadership": ["product", "cpo", "chief product"],
        "dual_role": ["product engineering", "technical product", "hardware product"],
    },
    "company_stage": ["series a", "series b", "series c", "growth", "scale-up", "funded"],
    "avoid_keywords": ["junior", "associate", "intern", "coordinator"],
    "location_preferences": {
        "remote_keywords": ["remote", "work from home", "wfh", "anywhere", "distributed"],
        "hybrid_keywords": ["hybrid"],
        "preferred_cities": [
            "toronto",
            "waterloo",
            "burlington",
            "oakville",
            "hamilton",
            "mississauga",
            "kitchener",
            "guelph",
        ],
        "preferred_regions": ["ontario", "canada", "greater toronto area", "gta"],
    },
    "filtering": {
        "aggression_level": "moderate",
        "software_engineering_avoid": [
            "software engineer",
            "software engineering",
            "vp of software",
            "director of software",
            "frontend",
            "backend",
            "full stack",
            "web developer",
            "mobile app",
            "devops",
            "cloud engineer",
            "saas",
            "fintech software",
        ],
        "hardware_company_boost": 10,
        "software_company_penalty": -20,
    },
}


class JobScorer(BaseScorer):
    """
    Score jobs against Wesley van Ooyen's profile

    Legacy scorer with hardcoded Wes profile and custom role matchers.
    Extends BaseScorer with Wesley-specific:
    - 8 detailed role category matchers
    - Country restriction logic for remote jobs
    - Keyword bonus calculations
    """

    def __init__(self):
        """Initialize with Wesley's hardcoded profile"""
        super().__init__(WES_PROFILE)
        self.db = JobDatabase()  # Keep for backward compatibility
        self.location_settings = load_location_settings()  # For country restriction logic

    def score_job(self, job: dict) -> tuple[int, str, dict, dict]:
        """
        Score a job from 0-110 (100 base + adjustments) with grade and breakdown

        Overrides BaseScorer.score_job() to handle job description for country restrictions.

        Args:
            job: Job dict with title, company, location, description (optional)

        Returns:
            (score, grade, breakdown_dict, classification_metadata)
        """
        title = job["title"].lower()
        company = job["company"].lower()
        company_display = job["company"]  # Keep original case
        location = (job.get("location") or "").lower()
        description = job.get("description", "")  # For country restriction check

        breakdown = {}

        # Use shared BaseScorer methods for most scoring
        breakdown["seniority"] = self._score_seniority(title)
        breakdown["domain"] = self._score_domain(title, company)
        breakdown["role_type"] = self._score_role_type(title)  # Wes-specific implementation below
        breakdown["location"] = self._score_location(location, description)  # Wes-specific override
        breakdown["technical"] = self._score_technical_keywords(title, company)

        # Company classification (from BaseScorer via classify_and_score_company)
        from utils.company_classifier import classify_and_score_company

        company_adjustment, classification_metadata = classify_and_score_company(
            company_classifier=self.company_classifier,
            company_name=company_display,
            job_title=job["title"],
            domain_keywords=self._get_domain_keywords(),
            role_types=self._get_role_types(),
            filtering_config=self._get_filtering_config(),
        )

        breakdown["company_classification"] = company_adjustment

        # Total score
        total_score = sum(breakdown.values())

        # Grade
        from utils.scoring_utils import calculate_grade

        grade = calculate_grade(total_score)

        return total_score, grade, breakdown, classification_metadata

    def _score_domain(self, title: str, company: str) -> int:
        """
        Score based on domain match (0-25 points)

        Wesley-specific override with tiered keyword lists.

        Scoring:
        - Hardware/Robotics/Automation: 25 points
        - MedTech: 20 points
        - Physical product: 15 points
        - Generic engineering: 10 points
        - Default: 5 points

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)

        Returns:
            Score 0-25 based on domain match
        """
        text = f"{title} {company}"

        # Hardware/Robotics/Automation: 25 points
        hardware_keywords = [
            "robotics",
            "automation",
            "hardware",
            "iot",
            "mechatronics",
            "embedded",
        ]
        if any(kw in text for kw in hardware_keywords):
            return 25

        # MedTech: 20 points
        medtech_keywords = ["medtech", "medical device", "healthcare", "pharma"]
        if any(kw in text for kw in medtech_keywords):
            return 20

        # Physical product: 15 points
        physical_keywords = ["manufacturing", "supply chain", "industrial", "mechanical"]
        if any(kw in text for kw in physical_keywords):
            return 15

        # Generic engineering: 10 points
        if "engineering" in text:
            return 10

        return 5  # Default for product roles

    def _score_technical_keywords(self, title: str, company: str) -> int:
        """
        Score based on technical keyword matches (0-10 points)

        Wesley-specific override with hardcoded tech keywords and word boundary matching.

        Args:
            title: Job title (lowercase)
            company: Company name (lowercase)

        Returns:
            Score 0-10 based on technical keyword matches
        """
        text = f"{title} {company}"
        score = 0

        # Strong technical matches (2 points each, max 10)
        tech_keywords = [
            "robotics",
            "automation",
            "iot",
            "hardware",
            "embedded",
            "firmware",
            "mechanical",
            "mechatronics",
            "manufacturing",
            "supply chain",
            "dfm",
            "industrial",
            "ml",
            "ai",
        ]

        for keyword in tech_keywords:
            if self._has_keyword(text, keyword):
                score += 2
                if score >= 10:
                    break

        return min(score, 10)

    def _score_location(self, location: str, description: str = "") -> int:
        """
        Score based on location match (0-15 points)

        Wesley-specific override with country restriction logic.

        Scoring:
        - Remote (unrestricted or Canada-friendly): 15 points
        - Remote (US-only or country-restricted): 0 points
        - Hybrid + Ontario: 15 points
        - Preferred Ontario cities: 12 points
        - Broader Canada: 8 points
        - US/Other: 0 points

        Args:
            location: Location string
            description: Job description (for country restriction check)

        Returns:
            Score 0-15
        """
        if not location:
            return 0

        location_lower = location.lower()
        prefs = self.profile["location_preferences"]

        # Check for remote (15 points - but verify no country restrictions)
        if any(kw in location_lower for kw in prefs["remote_keywords"]):
            # Check if remote job is restricted to non-Canadian countries
            if self._is_country_restricted(location, description):
                return 0  # US-only or country-restricted remote job
            return 15  # Unrestricted or Canada-friendly remote job

        # Check for hybrid
        is_hybrid = any(kw in location_lower for kw in prefs["hybrid_keywords"])

        # Check for preferred cities
        in_preferred_city = any(city in location_lower for city in prefs["preferred_cities"])

        # Check for preferred regions
        in_preferred_region = any(region in location_lower for region in prefs["preferred_regions"])

        # Scoring logic
        if is_hybrid and (in_preferred_city or in_preferred_region):
            return 15
        elif in_preferred_city:
            return 12
        elif in_preferred_region:
            return 8
        return 0

    def _is_country_restricted(self, location: str, description: str = "") -> bool:
        """
        Check if remote job is restricted to specific countries (excluding Canada)

        Args:
            location: Location string
            description: Job description text

        Returns:
            True if job is US-only or otherwise country-restricted
        """
        if not location:
            return False

        location_lower = location.lower()
        description_lower = description.lower() if description else ""
        patterns = self.location_settings.get("country_restriction_patterns", {})

        # Check for Canada-friendly patterns first (these override restrictions)
        canada_friendly = patterns.get("canada_friendly", [])
        for pattern in canada_friendly:
            if pattern in location_lower or pattern in description_lower:
                return False  # Explicitly welcomes Canadian candidates

        # Check for US-only patterns in location
        us_only_patterns = patterns.get("us_only", [])
        for pattern in us_only_patterns:
            if pattern in location_lower or pattern in description_lower:
                return True  # Restricted to US

        # Check for US states/cities in location (indicates US-specific remote)
        # Only flag if it's a remote job with a specific US location
        if any(kw in location_lower for kw in ["remote", "work from home", "wfh"]):
            us_states = patterns.get("us_states", [])
            for state in us_states:
                # Match full word boundaries to avoid false positives (e.g., "OR" in "Director")
                if f" {state} " in f" {location_lower} " or location_lower.endswith(f" {state}"):
                    return True  # Remote job in specific US location

        return False  # No country restrictions detected

    def _score_role_type(self, title: str) -> int:
        """
        Score based on role type using Wesley-specific matchers (0-20 points)

        Uses 8 detailed role category matchers for fine-grained categorization.
        Includes keyword bonus calculations (+2 per additional role keyword).
        Penalty: -5 for pure software engineering leadership.

        Args:
            title: Job title (lowercase)

        Returns:
            Score -5 to 22 (-5 penalty, or 20 base + up to 2 bonus)
        """
        is_leadership = self._is_leadership_title(title)

        # Check for software development penalty first
        penalty = self._calculate_software_penalty(title, is_leadership)
        if penalty < 0:
            return penalty

        # Try each category matcher in priority order
        # Product Leadership (highest priority)
        score, category = self._match_product_leadership(title, is_leadership)
        if score > 0:
            bonus = self._calculate_keyword_bonus(title, category)
            return min(score + bonus, 22)  # Cap at 22

        # Engineering Leadership
        score, category = self._match_engineering_leadership(title, is_leadership)
        if score > 0:
            bonus = self._calculate_keyword_bonus(title, category)
            return min(score + bonus, 22)

        # R&D Leadership
        score, category = self._match_rd_leadership(title, is_leadership)
        if score > 0:
            return score  # R&D doesn't get bonus

        # Technical Program Management
        score, category = self._match_technical_program_mgmt(title, is_leadership)
        if score > 0:
            return score

        # Manufacturing/Operations
        score, category = self._match_manufacturing_ops(title, is_leadership)
        if score > 0:
            return score

        # Product Development
        score, category = self._match_product_development(title, is_leadership)
        if score > 0:
            return score

        # Platform/Integrations
        score, category = self._match_platform_integrations(title, is_leadership)
        if score > 0:
            return score

        # Robotics/Automation
        score, category = self._match_robotics_automation(title, is_leadership)
        if score > 0:
            return score

        return 0  # No match

    def _calculate_software_penalty(self, title_lower: str, is_leadership: bool) -> int:
        """
        Return -5 if software development role, else 0.

        Consolidates duplicate penalty logic for pure software engineering roles.

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            -5 if software development role detected, 0 otherwise
        """
        if not is_leadership:
            return 0

        # Check for "software" + "development" combination first
        # (e.g., "Director of Software Development")
        if "software" in title_lower and "development" in title_lower:
            return -5

        # Check for software engineering penalties (only for engineering roles)
        if "engineering" in title_lower:
            software_indicators = ["software", "backend", "frontend", "web", "mobile"]
            for indicator in software_indicators:
                if indicator in title_lower:
                    return -5

        return 0

    def _calculate_keyword_bonus(self, title: str, category: str | None) -> int:
        """
        Calculate bonus points from keyword matches in config (max +2)

        Wesley-specific bonus calculation for roles with multiple matching keywords.

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

    # ========== Wesley-Specific Role Matchers ==========

    def _match_product_leadership(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Product Leadership roles (CPO, VP/Director of Product)"""
        product_keywords = ["product", "cpo", "chief product"]

        if any(self._has_keyword(title_lower, kw) for kw in product_keywords):
            if is_leadership:
                # Exclude pure product marketing unless it's dual role
                if "marketing" in title_lower and "engineering" not in title_lower:
                    return 0, None
                return 20, "product_leadership"
            return 15, "product_leadership"
        return 0, None

    def _match_engineering_leadership(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Engineering Leadership roles (VP/Director of Engineering)"""
        eng_keywords = ["engineering", "r&d", "technical", "hardware"]

        if any(self._has_keyword(title_lower, kw) for kw in eng_keywords):
            if is_leadership:
                return 20, "engineering_leadership"
            return 15, "engineering_leadership"
        return 0, None

    def _match_rd_leadership(self, title_lower: str, is_leadership: bool) -> tuple[int, str | None]:
        """Match R&D specific roles"""
        if self._has_keyword(title_lower, "r&d"):
            if is_leadership:
                return 20, None
            return 15, None
        return 0, None

    def _match_technical_program_mgmt(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Technical Program Management roles"""
        if not is_leadership:
            return 0, None

        program_keywords = ["program", "pmo", "delivery"]
        if any(self._has_keyword(title_lower, kw) for kw in program_keywords):
            return 15, "technical_program_management"

        return 0, None

    def _match_manufacturing_ops(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Manufacturing/NPI/Operations roles"""
        manufacturing_keywords = ["manufacturing", "npi", "operations", "production"]
        if not any(self._has_keyword(title_lower, kw) for kw in manufacturing_keywords):
            return 0, None

        base_score = 18 if is_leadership else 12
        return base_score, "manufacturing_npi_operations"

    def _match_product_development(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Product Development/R&D roles"""
        if "development" not in title_lower and "r&d" not in title_lower:
            return 0, None

        base_score = 15 if is_leadership else 10
        return base_score, "product_development_rnd"

    def _match_platform_integrations(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Platform/Integrations/Systems roles"""
        platform_keywords = ["platform", "integration", "systems"]
        if not any(self._has_keyword(title_lower, kw) for kw in platform_keywords):
            return 0, None

        base_score = 18 if is_leadership else 15
        return base_score, "platform_integrations_systems"

    def _match_robotics_automation(
        self, title_lower: str, _is_leadership: bool
    ) -> tuple[int, str | None]:
        """Match Robotics/Automation Engineering roles"""
        robotics_keywords = ["robotics", "automation", "mechatronics"]
        if not any(self._has_keyword(title_lower, kw) for kw in robotics_keywords):
            return 0, None

        # Senior+ or leadership gets higher score
        is_senior = any(
            kw in title_lower
            for kw in ["senior", "lead", "principal", "staff", "vp", "director", "head", "chief"]
        )

        if is_senior:
            return 15, "robotics_automation_engineering"
        return 10, "robotics_automation_engineering"

    def _calculate_grade(self, score: int) -> str:
        """
        Convert score to letter grade (out of 100 maximum)

        DEPRECATED: Use utils.scoring_utils.calculate_grade() directly instead.
        This method is kept for backwards compatibility with existing tests.

        Thresholds (100-point system):
        - A: 85+ (85%)
        - B: 70+ (70%)
        - C: 55+ (55%)
        - D: 40+ (40%)
        - F: <40 (<40%)
        """
        from utils.scoring_utils import calculate_grade

        return calculate_grade(score)


if __name__ == "__main__":
    # Test the scorer
    test_jobs = [
        {
            "title": "VP of Product Engineering",
            "company": "Robotics Startup",
            "location": "Remote",
            "description": "",
        },
        {
            "title": "Director of Hardware Engineering",
            "company": "Medical Device Company",
            "location": "Toronto, Canada",
            "description": "",
        },
        {
            "title": "Senior Software Engineer",
            "company": "Tech Startup",
            "location": "Remote - US Only",
            "description": "Must be located in the United States",
        },
    ]

    scorer = JobScorer()

    for job in test_jobs:
        score, grade, breakdown, metadata = scorer.score_job(job)
        print(f"\n{job['title']} at {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Score: {score}/110 (Grade {grade})")
        print(f"Breakdown: {breakdown}")
        print(
            f"Classification: {metadata.get('company_type')} (filtered: {metadata.get('filtered')})"
        )
