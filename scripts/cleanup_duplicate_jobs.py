#!/usr/bin/env python3
"""
Cleanup script to remove duplicate jobs from database

Identifies and removes duplicate jobs that differ only in LinkedIn tracking parameters.
Keeps the oldest instance of each duplicate (first received).
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def find_duplicates(db_path: str = "data/jobs.db"):
    """Find duplicate jobs (same title+company, different URLs)"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find all jobs grouped by title+company
    cursor.execute("""
        SELECT title, company, COUNT(*) as count
        FROM jobs
        GROUP BY title, company
        HAVING count > 1
        ORDER BY count DESC
    """)

    duplicates = []
    for row in cursor.fetchall():
        title, company, count = row["title"], row["company"], row["count"]

        # Get all instances of this job
        cursor.execute(
            """
            SELECT id, link, received_at, fit_score
            FROM jobs
            WHERE title = ? AND company = ?
            ORDER BY received_at ASC
        """,
            (title, company),
        )

        instances = [dict(row) for row in cursor.fetchall()]
        if len(instances) > 1:
            duplicates.append(
                {
                    "title": title,
                    "company": company,
                    "count": count,
                    "instances": instances,
                    "keep_id": instances[0]["id"],  # Keep oldest
                    "delete_ids": [inst["id"] for inst in instances[1:]],
                }
            )

    conn.close()
    return duplicates


def cleanup_duplicates(dry_run: bool = True):
    """Remove duplicate jobs, keeping the oldest instance"""
    duplicates = find_duplicates()

    if not duplicates:
        print("✓ No duplicates found!")
        return

    print(f"Found {len(duplicates)} sets of duplicate jobs:")
    print(f"Total duplicate records to remove: {sum(d['count'] - 1 for d in duplicates)}\n")

    for dup in duplicates:
        print(f"\n{dup['title']} @ {dup['company']}")
        print(f"  {dup['count']} instances found")
        print(f"  Keep ID {dup['keep_id']} (received {dup['instances'][0]['received_at']})")
        print(f"  Delete IDs: {', '.join(str(id) for id in dup['delete_ids'])}")

    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN - No changes made to database")
        print("Run with --execute flag to actually delete duplicates")
        return

    print("\n" + "=" * 80)
    print("Deleting duplicate records...")

    conn = sqlite3.connect("data/jobs.db")
    cursor = conn.cursor()

    total_deleted = 0
    for dup in duplicates:
        for delete_id in dup["delete_ids"]:
            cursor.execute("DELETE FROM jobs WHERE id = ?", (delete_id,))
            total_deleted += 1
            print(f"  ✓ Deleted job ID {delete_id}")

    conn.commit()
    conn.close()

    print(f"\n✓ Cleanup complete! Deleted {total_deleted} duplicate records")

    # Verify cleanup worked
    remaining_duplicates = find_duplicates()
    if remaining_duplicates:
        print(f"\n⚠️  Warning: {len(remaining_duplicates)} duplicate sets still exist")
    else:
        print("✓ Database is now clean - no duplicates remaining")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup duplicate jobs from database")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete duplicates (default is dry run)",
    )

    args = parser.parse_args()

    cleanup_duplicates(dry_run=not args.execute)
