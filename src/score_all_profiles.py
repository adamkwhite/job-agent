"""
Score All Jobs for All Profiles
Re-scores all jobs in the database against all enabled profiles

This creates per-person scores in the job_scores table.
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from agents.profile_scorer import ProfileScorer
from database import JobDatabase
from utils.profile_manager import get_profile_manager


def score_all_jobs_for_profile(profile_id: str, limit: int = 1000) -> dict[str, Any]:
    """
    Score all jobs for a specific profile

    Args:
        profile_id: Profile to score against
        limit: Max jobs to score

    Returns:
        Statistics about scoring results
    """
    manager = get_profile_manager()
    profile = manager.get_profile(profile_id)

    if not profile:
        print(f"Profile not found: {profile_id}")
        return {"error": f"Profile not found: {profile_id}"}

    db = JobDatabase()
    scorer = ProfileScorer(profile)

    # Get all jobs
    jobs = db.get_all_jobs()[:limit]

    by_grade: dict[str, int] = {}
    stats: dict[str, Any] = {"total": len(jobs), "by_grade": by_grade, "scored": 0}

    print(f"\nScoring {len(jobs)} jobs for profile: {profile_id} ({profile.name})")

    for i, job in enumerate(jobs):
        score, grade, breakdown, classification_metadata = scorer.score_job(job)

        # Save to job_scores table
        db.upsert_job_score(
            job_id=job["id"],
            profile_id=profile_id,
            score=score,
            grade=grade,
            breakdown=json.dumps(breakdown),
            classification_metadata=json.dumps(classification_metadata),
        )

        stats["scored"] += 1
        stats["by_grade"][grade] = stats["by_grade"].get(grade, 0) + 1

        # Progress indicator every 50 jobs
        if (i + 1) % 50 == 0:
            print(f"  Scored {i + 1}/{len(jobs)} jobs...")

    return stats


def score_all_profiles(limit: int = 1000) -> dict[str, dict[str, Any]]:
    """Score all jobs for all enabled profiles"""
    manager = get_profile_manager()

    results: dict[str, dict[str, Any]] = {}

    for profile in manager.get_enabled_profiles():
        print(f"\n{'=' * 60}")
        print(f"Profile: {profile.id} ({profile.name})")
        print(f"{'=' * 60}")

        stats = score_all_jobs_for_profile(profile.id, limit)
        results[profile.id] = stats

        print(f"\nResults for {profile.id}:")
        print(f"  Total scored: {stats.get('scored', 0)}")
        print(f"  Grade distribution: {stats.get('by_grade', {})}")

    return results


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Score jobs for all profiles")
    parser.add_argument(
        "--profile",
        type=str,
        help="Only score for this profile ID (default: all enabled profiles)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Max jobs to score (default: 1000)",
    )

    args = parser.parse_args()

    if args.profile:
        stats = score_all_jobs_for_profile(args.profile, args.limit)
        print(f"\nFinal stats: {stats}")
    else:
        results = score_all_profiles(args.limit)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        for profile_id, stats in results.items():
            print(f"\n{profile_id}:")
            print(f"  Scored: {stats.get('scored', 0)}")
            print(f"  Grades: {stats.get('by_grade', {})}")


if __name__ == "__main__":
    main()
