#!/usr/bin/env python3
"""
Cleanup Test/Placeholder Companies

Deactivates placeholder companies that were used for testing but are now
causing DNS failures and wasting API credits.

Identifies test companies by patterns:
- Domain matches: test.com, a.com, b.com, active.com, inactive.com
- Name patterns: "Test Company", "Company A", "Company B", etc.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"

# Patterns to identify test/placeholder companies
TEST_DOMAINS = [
    "test.com",
    "a.com",
    "b.com",
    "active.com",
    "inactive.com",
]

TEST_NAME_PATTERNS = [
    "Test Company",
    "Company A",
    "Company B",
    "Active Company",
    "Inactive Company",
]


def find_test_companies(conn: sqlite3.Connection) -> list[tuple]:
    """Find companies matching test patterns"""
    cursor = conn.cursor()

    # Build query to find test companies - use precise domain matching
    domain_conditions = " OR ".join(
        [
            f"careers_url LIKE '%://{domain}/%' OR careers_url LIKE '%://{domain}'"
            for domain in TEST_DOMAINS
        ]
    )
    name_conditions = " OR ".join([f"name = '{name}'" for name in TEST_NAME_PATTERNS])

    query = f"""
    SELECT id, name, careers_url, active, notes
    FROM companies
    WHERE ({domain_conditions}) OR ({name_conditions})
    ORDER BY id
    """

    cursor.execute(query)
    return cursor.fetchall()


def deactivate_companies(conn: sqlite3.Connection, company_ids: list[int]) -> None:
    """Deactivate companies by ID"""
    cursor = conn.cursor()

    for company_id in company_ids:
        cursor.execute("UPDATE companies SET active = 0 WHERE id = ?", (company_id,))

    conn.commit()


def main():
    """Main entry point"""
    print("=" * 80)
    print("CLEANUP TEST/PLACEHOLDER COMPANIES")
    print("=" * 80)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Find test companies
    test_companies = find_test_companies(conn)

    if not test_companies:
        print("\n✓ No test companies found!")
        conn.close()
        return

    print(f"\nFound {len(test_companies)} test/placeholder companies:\n")

    # Display found companies
    for company in test_companies:
        company_id, name, url, active, notes = company
        status = "ACTIVE" if active else "INACTIVE"
        print(f"  ID {company_id}: {name}")
        print(f"    URL: {url}")
        print(f"    Status: {status}")
        print(f"    Notes: {notes or 'None'}")
        print()

    # Confirm deactivation
    response = input("Deactivate these companies? (yes/no): ").strip().lower()

    if response == "yes":
        active_ids = [c[0] for c in test_companies if c[3] == 1]

        if active_ids:
            deactivate_companies(conn, active_ids)
            print(f"\n✓ Deactivated {len(active_ids)} companies")
        else:
            print("\n✓ All test companies already inactive")
    else:
        print("\n✗ Cancelled - no changes made")

    conn.close()

    print("\n" + "=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
