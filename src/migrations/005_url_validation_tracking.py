"""
Database migration: Add URL validation tracking for jobs
Adds columns to track URL validation status and prevent broken links in digests

Migration #005 - URL Validation Tracking
"""

import sqlite3
from pathlib import Path


def _add_column_if_not_exists(
    cursor: sqlite3.Cursor, columns: list[str], column_name: str, column_type: str
) -> None:
    """
    Add a column to the jobs table if it doesn't exist

    Args:
        cursor: Database cursor
        columns: List of existing column names
        column_name: Name of column to add
        column_type: SQL type of column (e.g., 'BOOLEAN', 'TEXT')
    """
    if column_name not in columns:
        cursor.execute(f"""
            ALTER TABLE jobs
            ADD COLUMN {column_name} {column_type} DEFAULT NULL
        """)
        print(f"Added {column_name} column to jobs table")
    else:
        print(f"{column_name} column already exists in jobs table")


def migrate(db_path: str = "data/jobs.db") -> bool:
    """
    Add URL validation tracking fields to jobs table

    Creates:
    1. url_validated (BOOLEAN) - Whether URL has been validated
    2. url_validated_at (TEXT) - Timestamp of last validation
    3. url_validation_reason (TEXT) - Validation result reason (valid, not_found, timeout, etc.)

    Also creates index on url_validated for efficient filtering of invalid URLs

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

        # Add validation tracking columns
        _add_column_if_not_exists(cursor, columns, "url_validated", "BOOLEAN")
        _add_column_if_not_exists(cursor, columns, "url_validated_at", "TEXT")
        _add_column_if_not_exists(cursor, columns, "url_validation_reason", "TEXT")

        # Create index on url_validated for filtering invalid URLs
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_url_validated
            ON jobs(url_validated)
        """)
        print("Created index on url_validated for efficient filtering")

        conn.commit()
        print("Migration successful: URL validation tracking fields added")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(_db_path: str = "data/jobs.db") -> bool:
    """
    Rollback migration - remove URL validation tracking fields

    WARNING: This will delete all validation tracking data!
    Note: SQLite does not support DROP COLUMN, so columns will remain but be unused
    """
    print("Note: SQLite does not support DROP COLUMN")
    print("To rollback, you would need to recreate the jobs table without these columns")
    print("URL validation tracking columns will remain but can be ignored")
    print("\nTo fully rollback:")
    print("1. Export job data without new columns")
    print("2. Drop and recreate jobs table without validation columns")
    print("3. Re-import job data")
    return True


def test_idempotency(db_path: str = "data/jobs.db") -> bool:
    """
    Test that running migration multiple times is safe (idempotent)

    Returns:
        True if idempotency test passes
    """
    print("\n=== Testing Migration Idempotency ===")

    # Run migration first time
    print("\n1. Running migration (first time)...")
    result1 = migrate(db_path)
    if not result1:
        print("❌ First migration failed")
        return False

    # Run migration second time (should be idempotent)
    print("\n2. Running migration (second time - idempotency test)...")
    result2 = migrate(db_path)
    if not result2:
        print("❌ Second migration failed (not idempotent)")
        return False

    print("\n✅ Idempotency test passed - migration can be run multiple times safely")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--rollback":
            rollback()
        elif sys.argv[1] == "--test-idempotency":
            test_idempotency()
        else:
            print("Usage: python 005_url_validation_tracking.py [--rollback|--test-idempotency]")
    else:
        migrate()
