#!/usr/bin/env python3
"""View LLM extraction failures from database"""

import sqlite3
from datetime import datetime

db_path = "data/jobs.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all failures, most recent first
cursor.execute(
    """
    SELECT id, company_name, failure_reason, error_details, occurred_at, review_action
    FROM llm_extraction_failures
    ORDER BY occurred_at DESC
    """
)

failures = cursor.fetchall()

print(f"\n{'=' * 80}")
print(f"LLM EXTRACTION FAILURES - Total: {len(failures)}")
print(f"{'=' * 80}\n")

for failure in failures:
    id_, company, reason, error, occurred, status = failure

    # Parse timestamp
    try:
        dt = datetime.fromisoformat(occurred)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        time_str = occurred

    # Truncate long error messages
    error_display = error[:200] + "..." if error and len(error) > 200 else error

    print(f"[{id_}] {company} - {time_str}")
    print(f"    Reason: {reason}")
    print(f"    Status: {status or 'pending'}")
    if error_display:
        print(f"    Error: {error_display}")
    print()

conn.close()

# Also show summary by error type
print(f"\n{'=' * 80}")
print("SUMMARY BY ERROR TYPE")
print(f"{'=' * 80}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute(
    """
    SELECT failure_reason, COUNT(*) as count
    FROM llm_extraction_failures
    GROUP BY failure_reason
    ORDER BY count DESC
    """
)

for reason, count in cursor.fetchall():
    print(f"  {reason}: {count}")

conn.close()
