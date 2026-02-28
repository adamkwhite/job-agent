#!/usr/bin/env python3
"""
Re-score all jobs in database with updated scoring criteria

This script re-evaluates all historical jobs using the current scoring logic,
allowing us to identify jobs that may now meet our criteria with the new
7-category role scoring system.

Usage:
    python src/rescore_all_jobs.py [--min-score 50] [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.profile_scorer import ProfileScorer
from database import JobDatabase
from utils.profile_manager import get_profile_manager


def rescore_all_jobs(
    min_score: int = 50, dry_run: bool = False
) -> tuple[dict[str, int | dict[str, int]], list[dict]]:
    """
    Re-score all jobs in the database with current scoring criteria

    Args:
        min_score: Minimum score threshold to highlight (default: 50 for D+ grade)
        dry_run: If True, don't update database, just report

    Returns:
        Tuple of (stats dict, newly_qualifying_jobs list)
    """
    db = JobDatabase()
    wes_profile = get_profile_manager().get_profile("wes")
    scorer = ProfileScorer(wes_profile)

    print("=" * 80)
    print("RE-SCORING ALL JOBS WITH UPDATED CRITERIA")
    print("=" * 80)
    print(f"Minimum score threshold: {min_score}")
    print(f"Mode: {'DRY RUN (no database updates)' if dry_run else 'LIVE (will update scores)'}")
    print()

    # Get all jobs from database
    jobs = db.get_all_jobs()
    print(f"Found {len(jobs)} total jobs in database\n")

    stats: dict[str, int | dict[str, int]] = {
        "total_jobs": len(jobs),
        "rescored": 0,
        "score_increased": 0,
        "score_decreased": 0,
        "score_unchanged": 0,
        "newly_qualifying": 0,  # Jobs that now meet min_score threshold
        "no_longer_qualifying": 0,  # Jobs that no longer meet min_score threshold
        "grade_changes": {},  # Track grade transitions
    }

    newly_qualifying_jobs = []
    significant_increases = []  # Jobs with +20 point increase

    for job in jobs:
        old_score = job.get("fit_score") or 0  # Handle None values
        old_grade = job.get("fit_grade") or "F"

        # Re-score the job
        new_score, new_grade, breakdown, _classification_metadata = scorer.score_job(job)

        assert isinstance(stats["rescored"], int)
        stats["rescored"] += 1

        # Track score changes
        score_diff = new_score - old_score

        if score_diff > 0:
            assert isinstance(stats["score_increased"], int)
            stats["score_increased"] += 1
        elif score_diff < 0:
            assert isinstance(stats["score_decreased"], int)
            stats["score_decreased"] += 1
        else:
            assert isinstance(stats["score_unchanged"], int)
            stats["score_unchanged"] += 1

        # Track grade transitions
        if old_grade != new_grade:
            transition = f"{old_grade}→{new_grade}"
            grade_changes = stats["grade_changes"]
            assert isinstance(grade_changes, dict)
            grade_changes[transition] = grade_changes.get(transition, 0) + 1

        # Track jobs that now meet threshold
        if old_score < min_score <= new_score:
            assert isinstance(stats["newly_qualifying"], int)
            stats["newly_qualifying"] += 1
            newly_qualifying_jobs.append(
                {
                    "id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "location": job.get("location", ""),
                    "link": job["link"],
                    "old_score": old_score,
                    "new_score": new_score,
                    "old_grade": old_grade,
                    "new_grade": new_grade,
                    "score_diff": score_diff,
                    "breakdown": breakdown,
                }
            )

        # Track jobs that no longer meet threshold
        if old_score >= min_score > new_score:
            assert isinstance(stats["no_longer_qualifying"], int)
            stats["no_longer_qualifying"] += 1

        # Track significant increases (+20 points or more)
        if score_diff >= 20:
            significant_increases.append(
                {
                    "title": job["title"],
                    "company": job["company"],
                    "old_score": old_score,
                    "new_score": new_score,
                    "score_diff": score_diff,
                    "old_grade": old_grade,
                    "new_grade": new_grade,
                }
            )

        # Update database (unless dry run)
        if not dry_run:
            db.update_job_score(job["id"], new_score, new_grade, json.dumps(breakdown))

    # Print summary
    print("\n" + "=" * 80)
    print("RE-SCORING SUMMARY")
    print("=" * 80)
    print(f"Total jobs processed: {stats['total_jobs']}")
    print(f"Jobs rescored: {stats['rescored']}")
    print()
    print("Score changes:")
    print(f"  Increased: {stats['score_increased']}")
    print(f"  Decreased: {stats['score_decreased']}")
    print(f"  Unchanged: {stats['score_unchanged']}")
    print()
    print(f"Threshold changes (min_score={min_score}):")
    print(f"  Newly qualifying: {stats['newly_qualifying']} ⬆️")
    print(f"  No longer qualifying: {stats['no_longer_qualifying']} ⬇️")
    print()

    grade_changes = stats["grade_changes"]
    if grade_changes and isinstance(grade_changes, dict):
        print("Grade transitions:")
        for transition, count in sorted(grade_changes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {transition}: {count} jobs")
        print()

    # Show newly qualifying jobs
    if newly_qualifying_jobs:
        print("\n" + "=" * 80)
        print(f"NEWLY QUALIFYING JOBS (now ≥ {min_score} points)")
        print("=" * 80)

        # Sort by new score (highest first)
        newly_qualifying_jobs.sort(key=lambda x: x["new_score"], reverse=True)

        for i, job in enumerate(newly_qualifying_jobs[:20], 1):  # Show top 20
            print(f"\n{i}. {job['title']} at {job['company']}")
            print(f"   Location: {job['location']}")
            print(
                f"   Score: {job['old_score']}/115 ({job['old_grade']}) → {job['new_score']}/115 ({job['new_grade']}) [+{job['score_diff']}]"
            )
            print(f"   Breakdown: {job['breakdown']}")
            print(f"   Link: {job['link']}")

        if len(newly_qualifying_jobs) > 20:
            print(f"\n... and {len(newly_qualifying_jobs) - 20} more")

    # Show significant increases
    if significant_increases:
        print("\n" + "=" * 80)
        print("SIGNIFICANT SCORE INCREASES (+20 points or more)")
        print("=" * 80)

        significant_increases.sort(key=lambda x: x["score_diff"], reverse=True)

        for i, job in enumerate(significant_increases[:10], 1):
            print(f"\n{i}. {job['title']} at {job['company']}")
            print(
                f"   {job['old_score']}/115 ({job['old_grade']}) → {job['new_score']}/115 ({job['new_grade']}) [+{job['score_diff']}]"
            )

    print("\n" + "=" * 80)

    if dry_run:
        print("DRY RUN COMPLETE - No changes made to database")
    else:
        print("RE-SCORING COMPLETE - Database updated")

    print("=" * 80)

    return stats, newly_qualifying_jobs


def main():
    parser = argparse.ArgumentParser(description="Re-score all jobs with updated scoring criteria")
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Minimum score threshold to highlight (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't update database, just report what would change",
    )

    args = parser.parse_args()

    rescore_all_jobs(
        min_score=args.min_score,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
