"""
View jobs stored in the database
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import JobDatabase


def view_database():
    """Display all jobs in the database"""
    db = JobDatabase()

    # Get stats
    stats = db.get_stats()

    print("=" * 70)
    print("DATABASE CONTENTS")
    print("=" * 70)
    print(f"\nTotal jobs: {stats['total_jobs']}")
    print(f"Notified: {stats['notified_jobs']}")
    print(f"Unnotified: {stats['unnotified_jobs']}")
    print("\nJobs by source:")
    for source, count in stats.get("jobs_by_source", {}).items():
        print(f"  {source}: {count}")

    # Get all jobs
    jobs = db.get_recent_jobs(limit=100)

    if not jobs:
        print("\nNo jobs in database")
        return

    print(f"\n{'=' * 70}")
    print(f"ALL JOBS ({len(jobs)})")
    print(f"{'=' * 70}\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location'] or 'Not specified'}")

        # Parse keywords
        try:
            keywords = json.loads(job["keywords_matched"])
            if keywords:
                print(f"   Keywords: {', '.join(keywords)}")
        except:
            pass

        print(f"   Link: {job['link']}")
        print(
            f"   Source: {job['source']} | Received: {job['received_at'][:10]} | Notified: {'Yes' if job['notified_at'] else 'No'}"
        )
        print()


if __name__ == "__main__":
    view_database()
