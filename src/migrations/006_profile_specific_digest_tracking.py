"""
Migration 006: Profile-Specific Digest Tracking

Migrates digest_sent from jobs table to job_scores table for multi-profile support.

Issue #262: After Issue #184, digest tracking is broken because digest_sent is in the
jobs table (shared across profiles) instead of job_scores table (profile-specific).

This migration:
1. Adds digest_sent and digest_sent_at columns to job_scores table
2. Migrates existing data (if job.digest_sent = 1, mark for ALL profiles)
3. Keeps old columns in jobs table temporarily for backwards compatibility

Run with:
    PYTHONPATH=$PWD job-agent-venv/bin/python src/migrations/006_profile_specific_digest_tracking.py
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def migrate(db_path: str = "data/jobs.db") -> None:
    """
    Migrate digest_sent tracking from jobs table to job_scores table

    Args:
        db_path: Path to SQLite database file
    """
    print("=" * 80)
    print("MIGRATION 006: Profile-Specific Digest Tracking")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Started: {datetime.now().isoformat()}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Check if columns already exist
        cursor.execute("PRAGMA table_info(job_scores)")
        columns = {row[1] for row in cursor.fetchall()}

        digest_sent_exists = "digest_sent" in columns
        digest_sent_at_exists = "digest_sent_at" in columns

        if digest_sent_exists and digest_sent_at_exists:
            print("⚠️  Migration already applied (both columns exist in job_scores)")
            print("Skipping migration.\n")
            return

        # Step 2: Add columns to job_scores table (if they don't exist)
        print("Step 1: Adding digest_sent columns to job_scores table...")

        if not digest_sent_exists:
            cursor.execute("""
                ALTER TABLE job_scores
                ADD COLUMN digest_sent BOOLEAN DEFAULT 0
            """)
            print("  ✓ Added digest_sent column")
        else:
            print("  ⊙ digest_sent column already exists, skipping")

        if not digest_sent_at_exists:
            cursor.execute("""
                ALTER TABLE job_scores
                ADD COLUMN digest_sent_at TEXT
            """)
            print("  ✓ Added digest_sent_at column")
        else:
            print("  ⊙ digest_sent_at column already exists, skipping")

        print()

        # Step 3: Migrate existing data
        print("Step 2: Migrating existing digest_sent data...")

        # Count jobs marked as sent
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE digest_sent = 1")
        jobs_marked_sent = cursor.fetchone()[0]

        if jobs_marked_sent > 0:
            # Migrate data: if job.digest_sent = 1, mark for ALL profiles
            cursor.execute("""
                UPDATE job_scores
                SET digest_sent = 1,
                    digest_sent_at = (
                        SELECT digest_sent_at
                        FROM jobs
                        WHERE jobs.id = job_scores.job_id
                    )
                WHERE job_id IN (
                    SELECT id FROM jobs WHERE digest_sent = 1
                )
            """)

            rows_updated = cursor.rowcount
            print(f"  ✓ Migrated {rows_updated} job_scores entries")
            print(f"    ({jobs_marked_sent} jobs marked as sent across all profiles)\n")
        else:
            print("  ⊙ No digest_sent data to migrate\n")

        # Step 4: Keep old columns for backwards compatibility (remove in future migration)
        print("Step 3: Backwards compatibility...")
        print("  ℹ️  Keeping digest_sent columns in jobs table for now")
        print("     (will be removed in future migration after verification)\n")

        # Commit changes
        conn.commit()

        print("=" * 80)
        print("✅ MIGRATION 006 COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Finished: {datetime.now().isoformat()}")
        print("\nNext steps:")
        print("  1. Test digest sending with multiple profiles")
        print("  2. Verify profile-specific tracking works correctly")
        print("  3. Remove old columns in future migration (007)\n")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ MIGRATION FAILED: {e}\n")
        raise

    finally:
        conn.close()


def rollback(db_path: str = "data/jobs.db") -> None:
    """
    Rollback migration by removing columns from job_scores table

    Args:
        db_path: Path to SQLite database file
    """
    print("=" * 80)
    print("ROLLBACK MIGRATION 006: Profile-Specific Digest Tracking")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Started: {datetime.now().isoformat()}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # SQLite doesn't support ALTER TABLE DROP COLUMN directly before version 3.35.0
        # So we need to recreate the table without the columns

        print("Step 1: Creating temporary job_scores table without digest columns...")

        # Get current schema
        cursor.execute("PRAGMA table_info(job_scores)")
        columns = [
            (row[1], row[2])
            for row in cursor.fetchall()
            if row[1] not in ("digest_sent", "digest_sent_at")
        ]

        # Create temp table
        column_defs = ", ".join(f"{name} {type_}" for name, type_ in columns)
        cursor.execute(f"""
            CREATE TABLE job_scores_temp (
                {column_defs}
            )
        """)
        print("  ✓ Created temporary table\n")

        print("Step 2: Copying data to temporary table...")
        column_names = ", ".join(name for name, _ in columns)
        cursor.execute(f"""
            INSERT INTO job_scores_temp ({column_names})
            SELECT {column_names} FROM job_scores
        """)
        print(f"  ✓ Copied {cursor.rowcount} rows\n")

        print("Step 3: Replacing original table...")
        cursor.execute("DROP TABLE job_scores")
        cursor.execute("ALTER TABLE job_scores_temp RENAME TO job_scores")
        print("  ✓ Replaced table\n")

        conn.commit()

        print("=" * 80)
        print("✅ ROLLBACK COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Finished: {datetime.now().isoformat()}\n")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ROLLBACK FAILED: {e}\n")
        raise

    finally:
        conn.close()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Migration 006: Profile-Specific Digest Tracking")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (remove columns)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/jobs.db",
        help="Path to database file (default: data/jobs.db)",
    )

    args = parser.parse_args()

    if args.rollback:
        rollback(args.db)
    else:
        migrate(args.db)


if __name__ == "__main__":
    main()
