"""
Database migration: Add filter tracking fields
Adds columns to track filtering decisions, stale job validation, and manual review flags

Migration #003 - Filter Tracking & Stale Job Detection
"""

import sqlite3
from pathlib import Path


def migrate(db_path: str = "data/jobs.db") -> bool:
    """
    Add filter tracking fields to jobs table

    Creates:
    1. filter_reason (TEXT) - Which filter blocked the job
    2. filtered_at (TEXT) - When job was filtered
    3. manual_review_flag (INTEGER) - Flag for edge cases needing review
    4. stale_check_result (TEXT) - Result of stale job validation

    Returns:
        True if migration successful, False otherwise
    """
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check which columns already exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add filter_reason column
        if "filter_reason" not in columns:
            cursor.execute("""
                ALTER TABLE jobs
                ADD COLUMN filter_reason TEXT
            """)
            print("Added filter_reason column to jobs table")
        else:
            print("filter_reason column already exists in jobs table")

        # Add filtered_at column
        if "filtered_at" not in columns:
            cursor.execute("""
                ALTER TABLE jobs
                ADD COLUMN filtered_at TEXT
            """)
            print("Added filtered_at column to jobs table")
        else:
            print("filtered_at column already exists in jobs table")

        # Add manual_review_flag column
        if "manual_review_flag" not in columns:
            cursor.execute("""
                ALTER TABLE jobs
                ADD COLUMN manual_review_flag INTEGER DEFAULT 0
            """)
            print("Added manual_review_flag column to jobs table")
        else:
            print("manual_review_flag column already exists in jobs table")

        # Add stale_check_result column
        if "stale_check_result" not in columns:
            cursor.execute("""
                ALTER TABLE jobs
                ADD COLUMN stale_check_result TEXT DEFAULT 'not_checked'
            """)
            print("Added stale_check_result column to jobs table")
        else:
            print("stale_check_result column already exists in jobs table")

        # Create index on filter_reason for query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_filter_reason
            ON jobs(filter_reason)
        """)

        # Create index on stale_check_result for digest filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_stale_check_result
            ON jobs(stale_check_result)
        """)

        # Create index on manual_review_flag for review interface
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_manual_review_flag
            ON jobs(manual_review_flag)
        """)

        conn.commit()
        print("Migration successful: filter tracking fields added")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(_db_path: str = "data/jobs.db") -> bool:
    """
    Rollback migration - remove filter tracking fields

    WARNING: This will delete all filter tracking data!
    Note: SQLite does not support DROP COLUMN, so columns will remain but be unused
    """
    print("Note: SQLite does not support DROP COLUMN")
    print("To rollback, you would need to recreate the jobs table without these columns")
    print("Filter tracking columns will remain but can be ignored")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
    else:
        migrate()
