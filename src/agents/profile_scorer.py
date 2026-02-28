"""
Profile-Based Job Scorer
Evaluates job opportunities against any user profile

Uses Profile objects for configurable scoring criteria.
Extends BaseScorer with role type matching, software penalty, and keyword bonus.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_scorer import BaseScorer
from utils.profile_manager import Profile, get_profile_manager


class ProfileScorer(BaseScorer):
    """Score jobs against a specific user profile"""

    def __init__(self, profile: Profile) -> None:
        """
        Initialize scorer with a Profile object

        Args:
            profile: Profile object with scoring criteria
        """
        super().__init__(profile)
        # Keep Profile object for convenience
        self.profile = profile

    def _score_role_type(self, title: str) -> int:
        """
        Score based on role type (-5 to 22 points)

        Uses word boundary matching to prevent false positives.
        Applies configurable software penalty and keyword bonus.

        Args:
            title: Job title (lowercase)

        Returns:
            Score -5 to 22 based on role type match
        """
        title_lower = title.lower()
        scoring = self.profile.scoring
        role_types = scoring.get("role_types", {})

        is_leadership = self._is_leadership_title(title_lower)

        # Check for software development penalty (configurable, default 0)
        penalty = self._get_role_software_penalty()
        if penalty < 0 and is_leadership and self._is_software_title(title_lower):
            return penalty

        # Check each role type category with word boundary matching
        for role_category, keywords in role_types.items():
            for kw in keywords:
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, title_lower):
                    score = 20 if is_leadership else 15
                    bonus = self._calculate_keyword_bonus(title, role_category)
                    return min(score + bonus, 22)

        return 0

    def _is_software_title(self, title_lower: str) -> bool:
        """Check if title indicates a software development role"""
        software_indicators = ["software", "backend", "frontend", "web", "mobile"]
        is_software_dev = "software" in title_lower and "development" in title_lower
        is_software_eng = "engineering" in title_lower and any(
            ind in title_lower for ind in software_indicators
        )
        return is_software_dev or is_software_eng

    def _get_role_software_penalty(self) -> int:
        """Get the software role penalty from filtering config (default 0)"""
        filtering = self.profile.scoring.get("filtering", {})
        return filtering.get("role_software_penalty", 0)


def score_job_for_profile(
    job: dict[str, str], profile_id: str
) -> tuple[int, str, dict[str, int], dict[str, object]] | None:
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


def score_job_for_all_profiles(
    job: dict[str, str],
) -> dict[str, tuple[int, str, dict[str, int], dict[str, object]]]:
    """
    Score a job for all enabled profiles

    Args:
        job: Job dictionary with title, company, location

    Returns:
        Dictionary mapping profile_id to (score, grade, breakdown, classification_metadata)
    """
    manager = get_profile_manager()
    results: dict[str, tuple[int, str, dict[str, int], dict[str, object]]] = {}

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
