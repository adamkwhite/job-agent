#!/usr/bin/env python3
"""
Score all unscored jobs for all enabled profiles
Run this after fixing database schema issues
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3

from src.utils.multi_scorer import get_multi_scorer


def score_all_unscored_jobs():
    """Score all jobs that don't have scores for any profile"""

    multi_scorer = get_multi_scorer()

    # Get all jobs that need scoring
    conn = sqlite3.connect("data/jobs.db")
    cursor = conn.cursor()

    # Find jobs that have fewer than 4 profile scores (should have one per enabled profile)
    cursor.execute("""
        SELECT j.id, j.title, j.company, j.location, j.link, j.description,
               COUNT(js.id) as score_count
        FROM jobs j
        LEFT JOIN job_scores js ON j.id = js.job_id
        GROUP BY j.id
        HAVING score_count < 4
        ORDER BY j.received_at DESC
    """)

    jobs_to_score = cursor.fetchall()
    conn.close()

    print(f"Found {len(jobs_to_score)} jobs needing scoring")
    print("This may take a few minutes...\n")

    scored_count = 0
    error_count = 0

    for i, job_data in enumerate(jobs_to_score, 1):
        job_id, title, company, location, link, description, current_scores = job_data

        # Show progress every 50 jobs
        if i % 50 == 0:
            print(f"Progress: {i}/{len(jobs_to_score)} jobs processed...")

        # Create job dictionary
        job = {
            "title": title,
            "company": company,
            "location": location or "",
            "link": link,
            "description": description or "",
        }

        # Score for all profiles
        try:
            results = multi_scorer.score_job_for_all(job=job, job_id=job_id)

            if results:
                scored_count += 1
                # Show first 10 results as examples
                if i <= 10:
                    scores_str = ", ".join(
                        [f"{pid}:{grade}({score})" for pid, (score, grade) in results.items()]
                    )
                    print(f"  [{i}] {title[:50]:50s} → {scores_str}")
            else:
                error_count += 1
                if i <= 10:
                    print(f"  [{i}] {title[:50]:50s} → Failed to score")
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # Show first 5 errors
                print(f"  ✗ Error scoring {title}: {e}")

    print(f"\n{'=' * 60}")
    print("✅ Scoring complete!")
    print(f"   Jobs processed: {len(jobs_to_score)}")
    print(f"   Successfully scored: {scored_count}")
    print(f"   Errors: {error_count}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    score_all_unscored_jobs()
