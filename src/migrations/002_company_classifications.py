"""
Database migration: Add company classification system
Creates company_classifications table and adds classification_metadata to job_scores

Migration #002 - Company Classifications & Software Role Filtering
"""

import sqlite3
from pathlib import Path


def migrate(db_path: str = "data/jobs.db") -> bool:
    """
    Add company_classifications table and classification_metadata column

    Creates:
    1. company_classifications table - stores company type (software/hardware/both/unknown)
    2. classification_metadata column in job_scores - stores classification decisions per job

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
        # Create company_classifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                classification TEXT NOT NULL CHECK(classification IN ('software', 'hardware', 'both', 'unknown')),
                confidence_score REAL NOT NULL CHECK(confidence_score BETWEEN 0.0 AND 1.0),
                source TEXT NOT NULL CHECK(source IN ('auto', 'manual')),
                signals TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_company_classifications_name
            ON company_classifications(company_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_company_classifications_type
            ON company_classifications(classification)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_company_classifications_source
            ON company_classifications(source)
        """)

        # Add classification_metadata column to job_scores table
        # Check if column exists first
        cursor.execute("PRAGMA table_info(job_scores)")
        columns = [col[1] for col in cursor.fetchall()]

        if "classification_metadata" not in columns:
            cursor.execute("""
                ALTER TABLE job_scores
                ADD COLUMN classification_metadata TEXT
            """)
            print("Added classification_metadata column to job_scores table")
        else:
            print("classification_metadata column already exists in job_scores table")

        conn.commit()
        print("Migration successful: company_classifications table created")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(db_path: str = "data/jobs.db") -> bool:
    """
    Rollback migration - drop company_classifications table and classification_metadata column

    WARNING: This will delete all company classification data!
    Note: SQLite does not support DROP COLUMN, so classification_metadata will remain but be unused
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS company_classifications")
        conn.commit()
        print("Rollback successful: company_classifications table dropped")
        print(
            "Note: classification_metadata column cannot be dropped in SQLite (ALTER TABLE DROP COLUMN not supported)"
        )
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
