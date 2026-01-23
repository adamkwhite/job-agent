"""
Job Scoring Agent
Evaluates job opportunities against candidate profile

⚠️ IMPORTANT: When updating scoring criteria in this file:
1. Update the email template in src/send_profile_digest.py (scoring explanation in email footer)
2. Update profile JSON files (profiles/wes.json, profiles/adam.json) if scoring weights change
3. Update CLAUDE.md documentation if categories/ranges change
4. Consider running src/rescore_all_jobs.py to re-evaluate historical data
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.company_classifier import CompanyClassifier
from utils.scoring_utils import calculate_grade, classify_and_score_company

logger = logging.getLogger(__name__)


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


class JobScorer:
    """Score jobs against Wesley van Ooyen's profile"""

    def __init__(self):
        self.db = JobDatabase()
        self.role_category_keywords = load_role_category_keywords()
        self.location_settings = load_location_settings()
        self.company_classifier = CompanyClassifier()

        # Wesley's profile criteria
        self.profile = {
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

    def score_job(self, job: dict) -> tuple[int, str, dict, dict]:
        """
        Score a job from 0-110 (100 base + adjustments) with grade and breakdown

        Includes company classification and software role filtering logic.
        Filtered software engineering roles receive -20 point penalty.
        Hardware company engineering roles receive +10 point boost.

        Returns:
            (score, grade, breakdown_dict, classification_metadata)
        """
        title = job["title"].lower()
        company = job["company"].lower()
        company_display = job["company"]  # Keep original case for display
        location = (job["location"] or "").lower()
        description = job.get(
            "description", ""
        )  # Get job description for country restriction check

        breakdown = {}
        classification_metadata = {}

        # 1. Seniority Match (0-30 points)
        seniority_score = self._score_seniority(title)
        breakdown["seniority"] = seniority_score

        # 2. Domain Match (0-25 points)
        domain_score = self._score_domain(title, company)
        breakdown["domain"] = domain_score

        # 3. Role Type Match (0-20 points)
        role_score = self._score_role_type(title)
        breakdown["role_type"] = role_score

        # 4. Location Match (0-15 points)
        location_score = self._score_location(location, description)
        breakdown["location"] = location_score

        # 5. Technical Keywords (0-10 points)
        tech_score = self._score_technical_keywords(title, company)
        breakdown["technical"] = tech_score

        # 6. Company Classification Adjustment (filtering penalties/boosts)
        company_adjustment, classification_metadata = classify_and_score_company(
            company_classifier=self.company_classifier,
            company_name=company_display,
            job_title=job["title"],
            domain_keywords=self.profile["domain_keywords"],
            role_types=self.profile["role_types"],
            filtering_config=self.profile.get("filtering", {}),
        )

        breakdown["company_classification"] = company_adjustment

        # Total score (max 100 + adjustments)
        total_score = sum(breakdown.values())

        # Grade (using shared 100-point grading system)
        grade = calculate_grade(total_score)

        return total_score, grade, breakdown, classification_metadata

    def _has_keyword(self, text: str, keyword: str) -> bool:
        """
        Check if keyword exists in text at word boundaries.
        Handles special cases like "VP," "VP-" "VP " etc.

        Args:
            text: Lowercase text to search in
            keyword: Lowercase keyword to search for

        Returns:
            True if keyword found at word boundary
        """
        import re

        # Use word boundary regex: \b ensures we match whole words
        # This prevents "vp" from matching "supervisor" and "chief" from matching "mischief"
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text))

    def _has_any_keyword(self, text: str, keywords: list[str]) -> bool:
        """Check if any keyword from list exists in text at word boundaries"""
        return any(self._has_keyword(text, keyword) for keyword in keywords)

    def _score_seniority(self, title: str) -> int:
        """Score based on seniority level (0-30)"""
        # VP/C-level: 30 points
        # Note: Using word boundaries to avoid false matches (e.g., "vp" in "supervisor")
        if self._has_any_keyword(title, ["vp", "vice president", "chief", "cto", "cpo", "head of"]):
            return 30

        # Director/Executive: 25 points
        if self._has_any_keyword(title, ["director", "executive director"]):
            return 25

        # Senior Manager/Principal: 15 points
        if self._has_any_keyword(title, ["senior manager", "principal", "staff"]):
            return 15

        # Manager/Lead: 10 points
        if self._has_any_keyword(title, ["manager", "lead", "leadership"]):
            return 10

        # IC roles: 0 points
        return 0

    def _score_domain(self, title: str, company: str) -> int:
        """Score based on domain match (0-25)"""
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

    def _count_keyword_matches(self, text: str, keywords: list[str]) -> int:
        """Count how many keywords from list appear in text (case-insensitive)"""
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw.lower() in text_lower)

    def _is_leadership_title(self, title_lower: str) -> bool:
        """
        Check if title indicates leadership position.

        Args:
            title_lower: Job title in lowercase

        Returns:
            True if title contains leadership keywords
        """
        leadership_keywords = ["vp", "director", "head", "chief", "executive"]
        return any(self._has_keyword(title_lower, kw) for kw in leadership_keywords)

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
        # Original logic from lines 356-360
        if "engineering" in title_lower:
            software_indicators = ["software", "backend", "frontend", "web", "mobile"]
            for indicator in software_indicators:
                if indicator in title_lower:
                    return -5

        return 0

    def _match_product_leadership(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Product Leadership roles (CPO, VP Product, etc.)

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        if "product" not in title_lower or not is_leadership:
            return (0, None)

        base_score = 15  # Default for product leadership

        # Hardware/technical boost (+5 points)
        hardware_keywords = ["hardware", "technical", "iot", "platform"]
        if any(self._has_keyword(title_lower, kw) for kw in hardware_keywords):
            base_score = 20
        # Product Engineering dual role
        elif "engineering" in title_lower:
            base_score = 18

        return (base_score, "product_leadership")

    def _match_engineering_leadership(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Engineering Leadership roles (CTO, VP Engineering, etc.)

        Note: Software penalty already checked in _calculate_software_penalty

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        if not is_leadership or "engineering" not in title_lower:
            return (0, None)

        # Hardware-focused engineering gets higher score
        hardware_keywords = ["hardware", "mechatronics", "systems"]
        if any(self._has_keyword(title_lower, kw) for kw in hardware_keywords):
            base_score = 20
        else:
            base_score = 15  # Generic engineering leadership

        return (base_score, "engineering_leadership")

    def _match_rd_leadership(self, title_lower: str, is_leadership: bool) -> tuple[int, str | None]:
        """
        Match R&D Leadership roles (VP of R&D, etc.)

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        if not is_leadership:
            return (0, None)

        if "r&d" in title_lower or "r & d" in title_lower:
            return (20, "engineering_leadership")

        return (0, None)

    def _match_technical_program_mgmt(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Technical Program Management roles

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        if not is_leadership:
            return (0, None)

        program_keywords = ["program", "pmo", "delivery"]
        if any(self._has_keyword(title_lower, kw) for kw in program_keywords):
            return (15, "technical_program_management")

        return (0, None)

    def _match_manufacturing_ops(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Manufacturing/NPI/Operations roles

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        manufacturing_keywords = ["manufacturing", "npi", "operations", "production"]
        if not any(self._has_keyword(title_lower, kw) for kw in manufacturing_keywords):
            return (0, None)

        base_score = 18 if is_leadership else 12
        return (base_score, "manufacturing_npi_operations")

    def _match_product_development(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Product Development/R&D roles

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        if "development" not in title_lower and "r&d" not in title_lower:
            return (0, None)

        base_score = 15 if is_leadership else 10
        return (base_score, "product_development_rnd")

    def _match_platform_integrations(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Platform/Integrations/Systems roles

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        platform_keywords = ["platform", "integration", "systems"]
        if not any(self._has_keyword(title_lower, kw) for kw in platform_keywords):
            return (0, None)

        base_score = 18 if is_leadership else 15
        return (base_score, "platform_integrations_systems")

    def _match_robotics_automation(
        self, title_lower: str, is_leadership: bool
    ) -> tuple[int, str | None]:
        """
        Match Robotics/Automation Engineering roles

        Args:
            title_lower: Job title in lowercase
            is_leadership: Whether title is a leadership position

        Returns:
            Tuple of (base_score, category_name) or (0, None) if no match
        """
        robotics_keywords = ["robotics", "automation", "mechatronics"]
        if not any(self._has_keyword(title_lower, kw) for kw in robotics_keywords):
            return (0, None)

        # Senior+ or leadership gets higher score
        is_senior = is_leadership or any(
            self._has_keyword(title_lower, kw) for kw in ["senior", "lead", "principal"]
        )
        base_score = 15 if is_senior else 10
        return (base_score, "robotics_automation_engineering")

    def _calculate_keyword_bonus(self, title: str, category: str | None) -> int:
        """
        Calculate bonus from keyword matches in config.

        Args:
            title: Job title (original case)
            category: Matched category name, or None

        Returns:
            Bonus points (+2 per matched keyword)
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

    def _score_role_type(self, title: str) -> int:
        """
        Score based on role type using 7-category system (0-20 base + bonuses)

        Categories (base scores):
        1. Product Leadership (15-20)
        2. Engineering Leadership (15-20)
        3. Technical Program Management (12-18)
        4. Manufacturing/NPI/Operations (12-18)
        5. Product Development/R&D (10-15)
        6. Platform/Integrations/Systems (15-18)
        7. Robotics/Automation Engineering (10-15)

        Bonus: +2 points per keyword match (must_keywords + nice_keywords)
        Penalty: -5 for pure software engineering leadership
        """
        title_lower = title.lower()
        is_leadership = self._is_leadership_title(title_lower)

        # Check for software development penalty first
        penalty = self._calculate_software_penalty(title_lower, is_leadership)
        if penalty < 0:
            return penalty

        # Try each category matcher in priority order
        matchers = [
            self._match_product_leadership,
            self._match_engineering_leadership,
            self._match_rd_leadership,
            self._match_technical_program_mgmt,
            self._match_manufacturing_ops,
            self._match_product_development,
            self._match_platform_integrations,
            self._match_robotics_automation,
        ]

        for matcher in matchers:
            base_score, category = matcher(title_lower, is_leadership)
            if category is not None:
                bonus_score = self._calculate_keyword_bonus(title, category)
                return base_score + bonus_score

        # Fallback for uncategorized titles
        base_score = 5 if "product" in title_lower or "program" in title_lower else 0
        return base_score

    def _is_country_restricted(self, location: str, description: str = "") -> bool:
        """
        Check if a remote job is restricted to a specific country (e.g., US-only)

        Args:
            location: Job location string (e.g., "Remote", "United States (Remote)")
            description: Job description text (may contain country requirements)

        Returns:
            True if job is restricted to non-Canadian countries, False otherwise
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

    def _score_location(self, location: str, description: str = "") -> int:
        """
        Score based on location match (0-15 points)

        Scoring:
        - Remote (unrestricted or Canada-friendly): 15 points (hard requirement met)
        - Remote (US-only or country-restricted): 0 points (not viable for Canadian candidates)
        - Hybrid + Ontario: 15 points (hard requirement met)
        - Preferred Ontario cities: 12 points (acceptable if hybrid)
        - Broader Canada: 8 points (possible)
        - US/Other: 0 points (not acceptable unless remote)
        """
        if not location:
            return 0

        location_lower = location.lower()
        prefs = self.profile["location_preferences"]

        # Check for remote (15 points - perfect match, but check for country restrictions)
        if any(kw in location_lower for kw in prefs["remote_keywords"]):
            # Check if remote job is restricted to non-Canadian countries
            if self._is_country_restricted(location, description):
                return 0  # US-only or country-restricted remote job
            return 15  # Unrestricted or Canada-friendly remote job

        # Check for hybrid (need to also check if in Ontario)
        is_hybrid = any(kw in location_lower for kw in prefs["hybrid_keywords"])

        # Check for preferred cities (Toronto, Waterloo, Burlington, etc.)
        in_preferred_city = any(city in location_lower for city in prefs["preferred_cities"])

        # Check for preferred regions (Ontario, Canada)
        in_preferred_region = any(region in location_lower for region in prefs["preferred_regions"])

        # Scoring logic
        if is_hybrid and (in_preferred_city or in_preferred_region):
            return 15  # Hybrid in Ontario - perfect
        elif in_preferred_city:
            return 12  # Preferred city (might be on-site, but acceptable location)
        elif in_preferred_region:
            return 8  # Broader Canada/Ontario
        else:
            return 0  # Not in preferred locations

    def _score_technical_keywords(self, title: str, company: str) -> int:
        """Score based on technical keyword matches (0-10)"""
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
        return calculate_grade(score)

    def score_all_jobs(self, limit: int = 100):
        """Score all recent jobs and update database"""
        jobs = self.db.get_recent_jobs(limit=limit)

        scored_jobs = []

        for job in jobs:
            score, grade, breakdown, classification_metadata = self.score_job(job)

            # Update job with score
            job_id = job["id"]
            self.db.update_job_score(job_id, score, grade, json.dumps(breakdown))

            scored_jobs.append(
                {
                    "id": job_id,
                    "title": job["title"],
                    "company": job["company"],
                    "score": score,
                    "grade": grade,
                    "breakdown": breakdown,
                }
            )

        # Sort by score
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)

        return scored_jobs


def main():
    """CLI entry point"""
    scorer = JobScorer()

    print("Scoring jobs against Wesley van Ooyen's profile...\n")

    scored_jobs = scorer.score_all_jobs()

    print(f"✓ Scored {len(scored_jobs)} jobs\n")
    print("=" * 80)
    print(f"{'GRADE':<8} {'SCORE':<8} {'TITLE':<40} {'COMPANY':<20}")
    print("=" * 80)

    for job in scored_jobs[:20]:  # Show top 20
        title = job["title"][:37] + "..." if len(job["title"]) > 40 else job["title"]
        company = job["company"][:17] + "..." if len(job["company"]) > 20 else job["company"]

        print(f"{job['grade']:<8} {job['score']:<8} {title:<40} {company:<20}")

    print("=" * 80)

    # Grade distribution
    grade_counts = {}
    for job in scored_jobs:
        grade = job["grade"]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    print("\nGrade Distribution:")
    for grade in ["A", "B", "C", "D", "F"]:
        count = grade_counts.get(grade, 0)
        print(f"  {grade}: {count} jobs")

    print("\nTop 5 matches:")
    for i, job in enumerate(scored_jobs[:5], 1):
        print(f"\n{i}. {job['title']} at {job['company']}")
        print(f"   Score: {job['score']}/100 (Grade {job['grade']})")
        print(f"   Breakdown: {job['breakdown']}")


if __name__ == "__main__":
    main()
