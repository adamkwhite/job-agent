#!/usr/bin/env python3
"""
Re-score all existing jobs with the new ProfileScorer system.
This ensures consistency after migrating from old JobScorer to new multi-profile system.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import JobDatabase
from utils.multi_scorer import get_multi_scorer


def main():
    """Re-score all jobs in database with new ProfileScorer"""
    db = JobDatabase()
    scorer = get_multi_scorer()

    # Get all jobs
    print("Fetching all jobs from database...")
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, company, location, description
        FROM jobs
        ORDER BY id
    """)

    jobs = cursor.fetchall()
    conn.close()

    print(f"Found {len(jobs)} jobs to re-score\n")
    print("=" * 80)

    rescored_count = 0
    error_count = 0

    for job_id, title, company, location, description in jobs:
        try:
            # Create job dict
            job_dict = {
                "title": title or "",
                "company": company or "",
                "location": location or "",
                "description": description or "",
            }

            # Score for all profiles
            score_results = scorer.score_new_job(job_dict, job_id)

            # Get max score across profiles
            max_score = max(score for score, grade in score_results.values())

            rescored_count += 1

            # Show high-scoring jobs
            if max_score >= 80:
                profile_scores = ", ".join(
                    f"{pid}:{score}" for pid, (score, _) in score_results.items()
                )
                print(f"⭐ [{job_id}] {title[:60]} - {profile_scores}")
            elif rescored_count % 50 == 0:
                print(f"   Processed {rescored_count}/{len(jobs)} jobs...")

        except Exception as e:
            error_count += 1
            print(f"❌ Error scoring job {job_id}: {e}")

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Total jobs: {len(jobs)}")
    print(f"  Successfully re-scored: {rescored_count}")
    print(f"  Errors: {error_count}")
    print("=" * 80)


if __name__ == "__main__":
    main()
