#!/usr/bin/env python3
"""
Re-score Ministry of Testing jobs after fixing company extraction bug

This script re-scores the 6 Ministry of Testing jobs to fix scores after
correcting the company name extraction logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from database import JobDatabase
from utils.multi_scorer import get_multi_scorer


def rescore_ministry_jobs():
    """Re-score all Ministry of Testing jobs"""
    db = JobDatabase()
    multi_scorer = get_multi_scorer()

    print("\n" + "=" * 80)
    print("RE-SCORING MINISTRY OF TESTING JOBS")
    print("=" * 80)

    # Get all Ministry of Testing jobs
    jobs = db.get_all_jobs()
    ministry_jobs = [j for j in jobs if j.get("source") == "ministry_of_testing"]

    print(f"Found {len(ministry_jobs)} Ministry of Testing jobs\n")

    for job in ministry_jobs:
        job_id = job["id"]
        title = job["title"]
        company = job["company"]
        location = job["location"]

        print(f"\n📋 Re-scoring Job {job_id}: {title}")
        print(f"   Company: {company}")
        print(f"   Location: {location}")

        # Re-score for all profiles
        try:
            profile_scores = multi_scorer.score_job_for_all(job, job_id)

            # Print scores for each profile
            for profile_id, (score, grade) in profile_scores.items():
                print(f"   {profile_id}: {score}/{grade}")

            # Highlight Mario's score
            if "mario" in profile_scores:
                mario_score, mario_grade = profile_scores["mario"]
                if mario_score >= 47:  # Mario's digest threshold
                    print(f"   🎯 QUALIFIES for Mario's digest (score: {mario_score})")

        except Exception as e:
            print(f"   ✗ Error re-scoring: {e}")

    print("\n" + "=" * 80)
    print("RE-SCORING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    rescore_ministry_jobs()
