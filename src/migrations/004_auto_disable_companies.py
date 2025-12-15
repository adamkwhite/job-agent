"""
Database migration: Add auto-disable tracking for companies
Adds columns to track consecutive scraping failures and auto-disable companies after 5+ failures

Migration #004 - Auto-Disable Failed Companies
"""

import sqlite3
from pathlib import Path


def migrate(db_path: str = "data/jobs.db") -> bool:
    """
    Add auto-disable tracking fields to companies table

    Creates:
    1. consecutive_failures (INTEGER) - Count of consecutive failed scrapes
    2. last_failure_reason (TEXT) - Reason for most recent failure
    3. auto_disabled_at (TEXT) - Timestamp when company was auto-disabled

    Also creates performance index on (consecutive_failures, active) for efficient queries

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
        cursor.execute("PRAGMA table_info(companies)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add consecutive_failures column
        if "consecutive_failures" not in columns:
            cursor.execute("""
                ALTER TABLE companies
                ADD COLUMN consecutive_failures INTEGER DEFAULT 0
            """)
            print("Added consecutive_failures column to companies table")
        else:
            print("consecutive_failures column already exists in companies table")

        # Add last_failure_reason column
        if "last_failure_reason" not in columns:
            cursor.execute("""
                ALTER TABLE companies
                ADD COLUMN last_failure_reason TEXT
            """)
            print("Added last_failure_reason column to companies table")
        else:
            print("last_failure_reason column already exists in companies table")

        # Add auto_disabled_at column
        if "auto_disabled_at" not in columns:
            cursor.execute("""
                ALTER TABLE companies
                ADD COLUMN auto_disabled_at TEXT
            """)
            print("Added auto_disabled_at column to companies table")
        else:
            print("auto_disabled_at column already exists in companies table")

        # Create composite index on consecutive_failures and active for query performance
        # This optimizes queries like: SELECT * FROM companies WHERE active = 1 AND consecutive_failures < 5
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_failures_active
            ON companies(consecutive_failures, active)
        """)
        print("Created index on (consecutive_failures, active) for query optimization")

        # Create index on auto_disabled_at for review queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_auto_disabled_at
            ON companies(auto_disabled_at)
        """)
        print("Created index on auto_disabled_at for review interface")

        conn.commit()
        print("Migration successful: auto-disable tracking fields added")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        return False

    finally:
        conn.close()


def rollback(_db_path: str = "data/jobs.db") -> bool:
    """
    Rollback migration - remove auto-disable tracking fields

    WARNING: This will delete all failure tracking data!
    Note: SQLite does not support DROP COLUMN, so columns will remain but be unused
    """
    print("Note: SQLite does not support DROP COLUMN")
    print("To rollback, you would need to recreate the companies table without these columns")
    print("Auto-disable tracking columns will remain but can be ignored")
    print("\nTo fully rollback:")
    print("1. Export company data: SELECT id, name, careers_url, active, notes FROM companies;")
    print("2. Drop and recreate companies table without new columns")
    print("3. Re-import company data")
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
            print("Usage: python 004_auto_disable_companies.py [--rollback|--test-idempotency]")
    else:
        migrate()
