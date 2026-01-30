"""
Profile-Based Job Scorer
Evaluates job opportunities against any user profile

This is the multi-person version of JobScorer that uses Profile objects
instead of hardcoded Wesley preferences.

Extends BaseScorer with generic role type matching.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_scorer import BaseScorer
from utils.profile_manager import Profile, get_profile_manager


class ProfileScorer(BaseScorer):
    """Score jobs against a specific user profile"""

    def __init__(self, profile: Profile):
        """
        Initialize scorer with a Profile object

        Args:
            profile: Profile object with scoring criteria
        """
        # Pass profile to BaseScorer (it handles both dict and Profile object)
        super().__init__(profile)
        self.profile = profile  # Keep Profile object for convenience

    def _score_role_type(self, title: str) -> int:
        """
        Score based on role type (0-20 points)

        Uses word boundary matching to prevent false positives like:
        - "cto" matching "director"
        - "product" matching "production"

        Generic implementation for multi-profile support.
        Uses simple keyword matching without complex matchers.

        Args:
            title: Job title (lowercase)

        Returns:
            Score 0-20 based on role type match
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
