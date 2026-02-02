"""
Database migration: Add multi-person scoring support
Creates job_scores table for per-person job scores

Migration #001 - Multi-Person Scoring
"""

import sqlite3
from pathlib import Path


def migrate(db_path: str = "data/jobs.db") -> bool:
    """
    Add job_scores table for multi-person scoring

    The existing jobs table keeps the job data (title, company, link, etc.)
    The new job_scores table stores per-person scores with profile_id

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
        # Create job_scores table for per-person scoring
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                fit_score INTEGER,
                fit_grade TEXT,
                score_breakdown TEXT,
                digest_sent_at TEXT,
                notified_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                UNIQUE(job_id, profile_id)
            )
        """)

        # Create indexes for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_scores_job_id
            ON job_scores(job_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_scores_profile_id
            ON job_scores(profile_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_scores_fit_score
            ON job_scores(fit_score)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_scores_digest_sent
            ON job_scores(digest_sent_at)
        """)

        # Migrate existing scores from jobs table to job_scores
        # Default to 'wes' profile for existing scores (legacy behavior)
        cursor.execute("""
            INSERT OR IGNORE INTO job_scores (
                job_id, profile_id, fit_score, fit_grade, score_breakdown,
                digest_sent_at, notified_at, created_at, updated_at
            )
            SELECT
                id, 'wes', fit_score, fit_grade, score_breakdown,
                digest_sent_at, notified_at,
                COALESCE(created_at, datetime('now')),
                COALESCE(updated_at, datetime('now'))
            FROM jobs
            WHERE fit_score IS NOT NULL
        """)

        migrated_count = cursor.rowcount

        conn.commit()
        print("Migration successful: job_scores table created")
        print(f"Migrated {migrated_count} existing scores to 'wes' profile")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(db_path: str = "data/jobs.db") -> bool:
    """
    Rollback migration - drop job_scores table

    WARNING: This will delete all per-person scoring data!
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS job_scores")
        conn.commit()
        print("Rollback successful: job_scores table dropped")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    import os
    import sys

    # Safety check: prevent running migrations on test databases
    db_path = os.getenv("DATABASE_PATH", "data/jobs.db")
    if "test" in db_path.lower() or "tmp" in db_path.lower():
        print(f"⚠️  WARNING: Detected test database path: {db_path}")
        print("Migrations should only run on production database.")
        print("Unset DATABASE_PATH or use production path.")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
    else:
        migrate()
