"""
Company monitoring service - handles database operations for companies
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.company_matcher import CompanyMatcher


class CompanyService:
    """Manages company monitoring database operations"""

    def __init__(self, db_path: str | None = None):
        # Respect DATABASE_PATH environment variable for test isolation
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "data/jobs.db")

        # CRITICAL: Prevent production database usage during tests
        import sys

        if "pytest" in sys.modules and "data/jobs.db" in db_path:
            raise RuntimeError(
                "❌ BLOCKED: Attempted to use production database (data/jobs.db) during tests!\n"
                "DATABASE_PATH environment variable must be set to a test path.\n"
                "This is a safety check to prevent test data pollution."
            )

        # Convert to absolute path relative to project root
        if not Path(db_path).is_absolute():
            # Assume project root is 2 levels up from this file
            project_root = Path(__file__).parent.parent.parent
            self.db_path = project_root / db_path
        else:
            self.db_path = Path(db_path)

    def add_company(self, name: str, careers_url: str, notes: str = "") -> dict:
        """
        Add a new company to monitor

        Args:
            name: Company name
            careers_url: URL to careers page
            notes: Optional notes about the company

        Returns:
            Dictionary with success status and company data or error message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        try:
            cursor.execute(
                """
                INSERT INTO companies (
                    name, careers_url, scraper_type, active, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (name, careers_url, "generic", 1, notes, now, now),
            )

            company_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "company": {
                    "id": company_id,
                    "name": name,
                    "careers_url": careers_url,
                    "active": True,
                    "created_at": now,
                },
            }

        except sqlite3.IntegrityError:
            # Duplicate company (UNIQUE constraint violation)
            return {
                "success": False,
                "error": f"Company '{name}' with URL '{careers_url}' already exists",
            }

        finally:
            conn.close()

    def add_companies_batch(
        self, companies: list[dict], similarity_threshold: float = 90.0
    ) -> dict:
        """
        Add multiple companies in batch, with fuzzy matching to prevent duplicates

        Args:
            companies: List of dicts with 'name', 'careers_url', 'notes' (optional), 'source' (optional)
            similarity_threshold: Fuzzy matching threshold (0-100, default 90)

        Returns:
            Dict with stats: {added: int, skipped_duplicates: int, errors: int, details: list}
        """
        # Get existing companies for fuzzy matching
        existing_companies = self.get_all_companies(active_only=False)

        # Initialize matcher
        matcher = CompanyMatcher(similarity_threshold=similarity_threshold)

        stats: dict[str, Any] = {
            "added": 0,
            "skipped_duplicates": 0,
            "errors": 0,
            "details": [],
        }

        print(f"\n[CompanyService] Batch import of {len(companies)} companies...")
        print(f"  Matching against {len(existing_companies)} existing companies")
        print(f"  Fuzzy matching threshold: {similarity_threshold}%\n")

        for company in companies:
            name = company.get("name", "").strip()
            careers_url = company.get("careers_url", "").strip()
            notes = company.get("notes", "")

            if not name or not careers_url:
                stats["errors"] += 1
                stats["details"].append(
                    {
                        "company": name or "(no name)",
                        "status": "error",
                        "reason": "Missing name or URL",
                    }
                )
                continue

            # Check for fuzzy match with existing companies
            match = matcher.find_match(company, existing_companies)

            if match:
                stats["skipped_duplicates"] += 1
                stats["details"].append(
                    {
                        "company": name,
                        "status": "skipped",
                        "reason": f"Matches existing: {match['name']}",
                    }
                )
                print(f"  ⊘ SKIP: {name} (matches {match['name']})")
                continue

            # Add company
            result = self.add_company(name=name, careers_url=careers_url, notes=notes)

            if result["success"]:
                stats["added"] += 1
                stats["details"].append({"company": name, "status": "added", "url": careers_url})
                print(f"  ✓ ADDED: {name}")

                # Add to existing companies list for future fuzzy matching within this batch
                existing_companies.append(
                    {
                        "name": name,
                        "careers_url": careers_url,
                        "notes": notes,
                    }
                )
            else:
                # Already exists (exact match from database UNIQUE constraint)
                stats["skipped_duplicates"] += 1
                stats["details"].append(
                    {"company": name, "status": "skipped", "reason": "Already exists (exact match)"}
                )
                print(f"  ⊘ SKIP: {name} (exact match in DB)")

        print("\n[CompanyService] Batch import complete:")
        print(f"  ✓ Added: {stats['added']}")
        print(f"  ⊘ Skipped (duplicates): {stats['skipped_duplicates']}")
        print(f"  ✗ Errors: {stats['errors']}")

        return stats

    def get_all_companies(self, active_only: bool = True) -> list[dict]:
        """
        Get all monitored companies

        Args:
            active_only: If True, only return active companies

        Returns:
            List of company dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if active_only:
            cursor.execute(
                """
                SELECT * FROM companies
                WHERE active = 1
                ORDER BY name
            """
            )
        else:
            cursor.execute("""
                SELECT * FROM companies
                ORDER BY name
            """)

        companies = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return companies

    def get_company(self, company_id: int) -> dict | None:
        """Get a single company by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()

        conn.close()

        return dict(row) if row else None

    def update_last_checked(self, company_id: int):
        """Update the last_checked timestamp for a company"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE companies
            SET last_checked = ?, updated_at = ?
            WHERE id = ?
        """,
            (now, now, company_id),
        )

        conn.commit()
        conn.close()

    def toggle_active(self, company_id: int) -> bool:
        """
        Toggle company active status

        Returns:
            New active status (True/False)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current status
        cursor.execute("SELECT active FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False

        new_status = 0 if row[0] == 1 else 1
        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE companies
            SET active = ?, updated_at = ?
            WHERE id = ?
        """,
            (new_status, now, company_id),
        )

        conn.commit()
        conn.close()

        return bool(new_status)

    def increment_company_failures(self, company_id: int, failure_reason: str) -> int:
        """
        Increment consecutive_failures counter and store failure reason

        Args:
            company_id: Company ID to update
            failure_reason: Description of why scraping failed (e.g., "0 jobs found", "timeout", "404")

        Returns:
            New consecutive_failures count after increment
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE companies
            SET consecutive_failures = consecutive_failures + 1,
                last_failure_reason = ?,
                updated_at = ?
            WHERE id = ?
        """,
            (failure_reason, now, company_id),
        )

        # Get the new count
        cursor.execute("SELECT consecutive_failures FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        new_count = row[0] if row else 0

        conn.commit()
        conn.close()

        return new_count

    def reset_company_failures(self, company_id: int) -> None:
        """
        Reset consecutive_failures counter to 0 after successful scrape

        Args:
            company_id: Company ID to reset
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE companies
            SET consecutive_failures = 0,
                last_failure_reason = NULL,
                updated_at = ?
            WHERE id = ?
        """,
            (now, company_id),
        )

        conn.commit()
        conn.close()

    def disable_company(self, company_id: int, reason: str = "auto_disabled_5_failures") -> None:
        """
        Disable a company (set active = 0) and record auto-disable timestamp

        Args:
            company_id: Company ID to disable
            reason: Reason for disabling (default: auto-disabled after 5 failures)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE companies
            SET active = 0,
                auto_disabled_at = ?,
                last_failure_reason = ?,
                updated_at = ?
            WHERE id = ?
        """,
            (now, reason, now, company_id),
        )

        conn.commit()
        conn.close()

    def get_auto_disabled_companies(self) -> list[dict]:
        """
        Get all companies that were auto-disabled (have auto_disabled_at timestamp)

        Returns:
            List of company dictionaries with auto-disable details
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM companies
            WHERE auto_disabled_at IS NOT NULL
            ORDER BY auto_disabled_at DESC
        """
        )

        companies = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return companies


if __name__ == "__main__":
    # Test the service
    service = CompanyService()

    # Add a test company
    result = service.add_company(
        name="Boston Dynamics",
        careers_url="https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
        notes="Robotics company - high priority",
    )

    print("Add company result:", result)

    # Get all companies
    companies = service.get_all_companies()
    print(f"\nTotal companies: {len(companies)}")
    for company in companies:
        print(f"  - {company['name']}: {company['careers_url']}")
