"""
View jobs stored in the database
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import JobDatabase


def view_database(profile_id: str = "wes"):
    """Display jobs scored for a specific profile

    Args:
        profile_id: Profile ID for scoring (default: "wes")
    """
    db = JobDatabase()

    # Get stats
    stats = db.get_stats()

    print("=" * 70)
    print(f"DATABASE CONTENTS - Profile: {profile_id}")
    print("=" * 70)
    print(f"\nTotal jobs: {stats['total_jobs']}")
    print(f"Notified: {stats['notified_jobs']}")
    print(f"Unnotified: {stats['unnotified_jobs']}")
    print("\nJobs by source:")
    for source, count in stats.get("jobs_by_source", {}).items():
        print(f"  {source}: {count}")

    # Get profile-specific jobs
    jobs = db.get_jobs_for_profile_digest(
        profile_id=profile_id,
        min_grade="F",  # Include all grades
        min_location_score=0,  # No location filtering
        limit=100,
        max_age_days=30,
    )

    if not jobs:
        print("\nNo jobs in database")
        return

    print(f"\n{'=' * 70}")
    print(f"JOBS FOR PROFILE: {profile_id} ({len(jobs)})")
    print(f"{'=' * 70}\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location'] or 'Not specified'}")
        print(f"   Score: {job.get('fit_score', 'N/A')} ({job.get('fit_grade', 'N/A')})")

        # Parse keywords
        try:
            keywords = json.loads(job["keywords_matched"])
            if keywords:
                print(f"   Keywords: {', '.join(keywords)}")
        except (json.JSONDecodeError, TypeError):
            pass

        print(f"   Link: {job['link']}")
        print(
            f"   Source: {job['source']} | Received: {job['received_at'][:10]} | Notified: {'Yes' if job['notified_at'] else 'No'}"
        )
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View jobs in database for a profile")
    parser.add_argument(
        "--profile",
        type=str,
        default="wes",
        help="Profile ID for scoring (default: wes)",
    )
    args = parser.parse_args()

    view_database(profile_id=args.profile)
