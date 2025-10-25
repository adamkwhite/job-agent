"""
Migration script to add companies table for career page monitoring
"""

import sqlite3
from pathlib import Path


def migrate_database(db_path: str = "data/jobs.db"):
    """Add companies table to existing database"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating database at {db_path}...")

    # Create companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            careers_url TEXT NOT NULL,
            scraper_type TEXT DEFAULT 'generic',
            active INTEGER DEFAULT 1,
            last_checked TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(name, careers_url)
        )
    """)

    # Create indexes for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_active ON companies(active)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_name ON companies(name)
    """)

    conn.commit()

    # Verify table was created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    if cursor.fetchone():
        print("✓ Companies table created successfully")

        # Show table schema
        cursor.execute("PRAGMA table_info(companies)")
        columns = cursor.fetchall()
        print("\nTable schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    else:
        print("✗ Failed to create companies table")

    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate_database()
