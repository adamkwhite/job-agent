"""
Multi-Person Job Scorer
Scores jobs for all enabled profiles simultaneously

Use this after adding new jobs to ensure they're scored for all users.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.profile_scorer import ProfileScorer
from database import JobDatabase
from utils.profile_manager import get_profile_manager


class MultiPersonScorer:
    """Score jobs for all enabled profiles"""

    def __init__(self):
        self.db = JobDatabase()
        self.manager = get_profile_manager()

        # Create scorers for each profile
        self.scorers = {}
        for profile in self.manager.get_enabled_profiles():
            self.scorers[profile.id] = ProfileScorer(profile)

    def score_job_for_all(self, job: dict, job_id: int) -> dict[str, tuple[int, str]]:
        """
        Score a job for all enabled profiles and save to database

        Args:
            job: Job dictionary with title, company, location
            job_id: Database ID of the job

        Returns:
            Dictionary mapping profile_id to (score, grade)
        """
        results = {}

        for profile_id, scorer in self.scorers.items():
            score, grade, breakdown, classification_metadata = scorer.score_job(job)

            # Save to job_scores table
            self.db.upsert_job_score(
                job_id=job_id,
                profile_id=profile_id,
                score=score,
                grade=grade,
                breakdown=json.dumps(breakdown),
                classification_metadata=json.dumps(classification_metadata),
            )

            results[profile_id] = (score, grade)

        return results

    def score_new_job(self, job_data: dict, job_id: int) -> dict:
        """
        Score a newly added job for all profiles

        This is the main entry point for scoring new jobs.

        Args:
            job_data: Job dictionary (from parsing/scraping)
            job_id: Database ID of the job

        Returns:
            Scoring results for all profiles
        """
        return self.score_job_for_all(job_data, job_id)

    def get_best_match_profile(self, job_id: int) -> tuple[str, int, str] | None:
        """
        Find which profile has the best match for a job

        Args:
            job_id: Database ID of the job

        Returns:
            (profile_id, score, grade) or None if no scores
        """
        best = None

        for profile_id in self.scorers:
            score_data = self.db.get_job_score(job_id, profile_id)
            if score_data:
                score = score_data.get("fit_score", 0)
                grade = score_data.get("fit_grade", "F")
                if best is None or score > best[1]:
                    best = (profile_id, score, grade)

        return best


# Singleton instance
_multi_scorer: MultiPersonScorer | None = None


def get_multi_scorer() -> MultiPersonScorer:
    """Get or create MultiPersonScorer singleton"""
    global _multi_scorer
    if _multi_scorer is None:
        _multi_scorer = MultiPersonScorer()
    return _multi_scorer


def score_job_all_profiles(job: dict, job_id: int) -> dict[str, tuple[int, str]]:
    """
    Convenience function to score a job for all profiles

    Args:
        job: Job dictionary with title, company, location
        job_id: Database ID of the job

    Returns:
        Dictionary mapping profile_id to (score, grade)
    """
    scorer = get_multi_scorer()
    return scorer.score_new_job(job, job_id)


if __name__ == "__main__":
    # Test scoring
    scorer = MultiPersonScorer()

    test_job = {
        "title": "Senior Software Engineer",
        "company": "Tech Startup",
        "location": "Toronto, Canada",
    }

    print("Test job:", test_job)
    print("\nScoring for all profiles (not saving to DB):")

    for profile_id, profile_scorer in scorer.scorers.items():
        score, grade, breakdown, classification_metadata = profile_scorer.score_job(test_job)
        filtered_status = " [FILTERED]" if classification_metadata.get("filtered") else ""
        print(f"  {profile_id}: {score}/115 (Grade {grade}){filtered_status}")
