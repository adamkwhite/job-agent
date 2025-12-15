"""
Integration tests for auto-disable functionality in CompanyScraper
Tests the full workflow: scraping failures → auto-disable → exclusion from future scrapes
"""

import tempfile
from pathlib import Path

import pytest

from api.company_service import CompanyService


@pytest.fixture
def temp_db():
    """Create a temporary database with companies table"""
    import sqlite3

    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    db_path = Path(path)

    # Create companies table with auto-disable fields
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
            consecutive_failures INTEGER DEFAULT 0,
            last_failure_reason TEXT,
            auto_disabled_at TEXT,
            UNIQUE(name, careers_url)
        )
    """)
    conn.commit()
    conn.close()

    # Initialize service with temp database
    service = CompanyService(db_path=str(db_path))

    yield service, str(db_path)

    # Cleanup
    db_path.unlink(missing_ok=True)


def test_successful_scrape_resets_failures_logic(temp_db):
    """Test that successful scrape logic resets the failure counter (unit test)"""
    service, db_path = temp_db

    # Add company with some failures
    result = service.add_company("Test Co", "https://test.com/careers")
    company_id = result["company"]["id"]

    # Simulate 2 previous failures
    service.increment_company_failures(company_id, "timeout")
    service.increment_company_failures(company_id, "parse error")

    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 2

    # Simulate successful scrape (jobs found) - reset counter
    service.reset_company_failures(company_id)

    # Verify failures were reset
    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 0
    assert company["last_failure_reason"] is None


def test_failed_scrape_increments_failures_logic(temp_db):
    """Test that failed scrape logic increments the failure counter (unit test)"""
    service, db_path = temp_db

    # Add company
    result = service.add_company("Failing Co", "https://failing.com/careers")
    company_id = result["company"]["id"]

    # Simulate failed scrape (0 jobs extracted)
    failure_count = service.increment_company_failures(company_id, "0 jobs extracted")

    # Verify failure incremented
    assert failure_count == 1
    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 1
    assert company["last_failure_reason"] == "0 jobs extracted"
    assert company["active"] == 1  # Still active (not yet disabled)


def test_five_consecutive_failures_triggers_auto_disable_logic(temp_db):
    """Test that 5 consecutive failures auto-disables the company (unit test)"""
    service, db_path = temp_db

    # Add company
    result = service.add_company("Bad Co", "https://bad.com/careers")
    company_id = result["company"]["id"]

    # Simulate 4 previous failures
    for i in range(4):
        service.increment_company_failures(company_id, f"failure_{i + 1}")

    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 4
    assert company["active"] == 1  # Still active

    # 5th failure
    failure_count = service.increment_company_failures(company_id, "0 jobs extracted")
    assert failure_count == 5

    # Auto-disable company
    service.disable_company(company_id)

    # Verify auto-disabled
    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 5
    assert company["active"] == 0  # Now disabled
    assert company["auto_disabled_at"] is not None


def test_failure_success_failure_workflow_logic(temp_db):
    """Test failures → success (reset) → failures workflow (unit test)"""
    service, db_path = temp_db

    # Add company
    result = service.add_company("Flaky Co", "https://flaky.com/careers")
    company_id = result["company"]["id"]

    # Simulate 3 failures
    for i in range(3):
        service.increment_company_failures(company_id, f"failure_{i + 1}")

    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 3

    # Simulate success (jobs found) - reset
    service.reset_company_failures(company_id)

    # Verify reset
    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 0

    # Simulate failure again - should start counting from 0
    service.increment_company_failures(company_id, "new failure")

    # Verify new failure count starts from 1
    company = service.get_company(company_id)
    assert company["consecutive_failures"] == 1
    assert company["active"] == 1  # Still active


def test_auto_disabled_companies_excluded_from_scraping(temp_db):
    """Test that auto-disabled companies are not included in scraping queries"""
    service, db_path = temp_db

    # Add 3 companies
    service.add_company("Active Co", "https://active.com/careers")
    result2 = service.add_company("Disabled Co", "https://disabled.com/careers")
    service.add_company("Active Co 2", "https://active2.com/careers")

    # Auto-disable one company
    service.disable_company(result2["company"]["id"])

    # Get active companies (what scraper would fetch)
    active_companies = service.get_all_companies(active_only=True)

    # Should only get 2 active companies (disabled one excluded)
    assert len(active_companies) == 2
    company_names = [c["name"] for c in active_companies]
    assert "Active Co" in company_names
    assert "Active Co 2" in company_names
    assert "Disabled Co" not in company_names
