"""
Profile-Based Job Scorer
Evaluates job opportunities against any user profile

This is the multi-person version of JobScorer that uses Profile objects
instead of hardcoded Wesley preferences.
"""

import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import JobDatabase
from utils.company_classifier import CompanyClassifier
from utils.profile_manager import Profile, get_profile_manager
from utils.scoring_utils import calculate_grade, classify_and_score_company

logger = logging.getLogger(__name__)


def load_role_category_keywords() -> dict:
    """Load role category keywords from config file"""
    config_path = Path(__file__).parent.parent.parent / "config" / "filter-keywords.json"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("role_category_keywords", {})


class ProfileScorer:
    """Score jobs against a specific user profile"""

    def __init__(self, profile: Profile):
        self.profile = profile
        self.db = JobDatabase()
        self.role_category_keywords = load_role_category_keywords()
        self.company_classifier = CompanyClassifier()  # Multi-signal company classification

    def score_job(self, job: dict) -> tuple[int, str, dict, dict]:
        """
        Score a job from 0-115 with grade and breakdown

        Includes company classification and software role filtering logic.
        Filtered software engineering roles receive penalty from profile config.
        Hardware company engineering roles receive boost from profile config.

        Returns:
            (score, grade, breakdown_dict, classification_metadata)
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

        # 2. Seniority Match (0-30 points) - ONLY if role type matches
        # This prevents "Director of Marketing" from scoring 30 points
        # while "Director of Engineering" gets full points
        seniority_score = self._score_seniority(title) if role_score > 0 else 0
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
            domain_keywords=self.profile.get_domain_keywords(),
            role_types=self.profile.scoring.get("role_types", {}),
            filtering_config=self.profile.scoring.get("filtering", {}),
        )

        breakdown["company_classification"] = company_adjustment

        # Total score (max 100 + adjustments)
        total_score = sum(breakdown.values())

        # Grade (using shared utility)
        grade = calculate_grade(total_score)

        return total_score, grade, breakdown, classification_metadata

    def _score_seniority(self, title: str) -> int:
        """Score based on seniority level (0-30)"""
        target_seniority = self.profile.get_target_seniority()

        # VP/C-level keywords
        vp_keywords = ["vp ", "vice president", "chief", "cto", "cpo", "head of"]
        director_keywords = ["director", "executive director"]
        senior_keywords = ["senior manager", "principal", "staff", "senior"]
        mid_keywords = ["manager", "lead", "leadership"]

        # Check for VP/C-level matches (30 points)
        if any(kw in title for kw in vp_keywords) and any(
            kw in target_seniority for kw in ["vp", "chief", "head of", "executive"]
        ):
            return 30

        # Director (25 points)
        if any(kw in title for kw in director_keywords) and "director" in target_seniority:
            return 25

        # Senior Manager/Principal (15 points)
        if any(kw in title for kw in senior_keywords) and any(
            kw in target_seniority for kw in ["senior", "principal", "staff"]
        ):
            return 15

        # Manager/Lead (10 points)
        if any(kw in title for kw in mid_keywords) and any(
            kw in target_seniority for kw in ["manager", "lead", "senior"]
        ):
            return 10

        return 0

    def _score_domain(self, title: str, company: str) -> int:
        """Score based on domain match (0-25)"""
        text = f"{title} {company}"
        domain_keywords = self.profile.get_domain_keywords()

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

    def _count_keyword_matches(self, text: str, keywords: list[str]) -> int:
        """Count how many keywords from list appear in text"""
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw.lower() in text_lower)

    def _score_role_type(self, title: str) -> int:
        """Score based on role type (0-20)

        Uses word boundary matching to prevent false positives like:
        - "cto" matching "director"
        - "product" matching "production"
        """
        title_lower = title.lower()
        scoring = self.profile.scoring
        role_types = scoring.get("role_types", {})

        is_leadership = any(
            kw in title_lower for kw in ["vp", "director", "head", "chief", "executive"]
        )

        # Check each role type category with word boundary matching
        for _role_type, keywords in role_types.items():
            # Use word boundaries to prevent substring false positives
            # e.g., "cto" should not match "director"
            for kw in keywords:
                # Create regex pattern with word boundaries
                # \b matches word boundary (start/end of word)
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, title_lower):
                    if is_leadership:
                        return 20
                    return 15

        # No fallback points - only award points for explicit role type matches
        # This prevents "Performance Marketing Director" from scoring 10 points
        return 0

    def _score_location(self, location: str) -> int:
        """Score based on location match (0-15 points)"""
        if not location:
            return 0

        location_lower = location.lower()
        prefs = self.profile.get_location_preferences()

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
        """Score based on technical keyword matches (0-10)"""
        text = f"{title} {company}".lower()
        domain_keywords = self.profile.get_domain_keywords()

        score = 0
        for keyword in domain_keywords:
            if keyword in text:
                score += 2
                if score >= 10:
                    break

        return min(score, 10)


def score_job_for_profile(job: dict, profile_id: str) -> tuple[int, str, dict, dict] | None:
    """
    Convenience function to score a job for a specific profile

    Args:
        job: Job dictionary with title, company, location
        profile_id: Profile ID (e.g., 'wes', 'adam')

    Returns:
        (score, grade, breakdown, classification_metadata) or None if profile not found
    """
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        return None

    scorer = ProfileScorer(profile)
    return scorer.score_job(job)


def score_job_for_all_profiles(job: dict) -> dict[str, tuple[int, str, dict, dict]]:
    """
    Score a job for all enabled profiles

    Args:
        job: Job dictionary with title, company, location

    Returns:
        Dictionary mapping profile_id to (score, grade, breakdown, classification_metadata)
    """
    manager = get_profile_manager()
    results: dict[str, tuple[int, str, dict, dict]] = {}

    for profile in manager.get_enabled_profiles():
        scorer = ProfileScorer(profile)
        results[profile.id] = scorer.score_job(job)

    return results


if __name__ == "__main__":
    # Test scoring the same job for different profiles
    test_job = {
        "title": "VP of Engineering",
        "company": "Robotics Startup Inc",
        "location": "Remote, USA",
    }

    print(f"Test Job: {test_job['title']} at {test_job['company']}")
    print(f"Location: {test_job['location']}")
    print("=" * 60)

    results = score_job_for_all_profiles(test_job)

    for profile_id, (score, grade, breakdown, classification_metadata) in results.items():
        print(f"\n{profile_id.upper()} Profile:")
        print(f"  Score: {score}/115 (Grade {grade})")
        print(f"  Breakdown: {breakdown}")
        filtered = " [FILTERED]" if classification_metadata.get("filtered") else ""
        print(f"  Company: {classification_metadata.get('company_type')}{filtered}")
