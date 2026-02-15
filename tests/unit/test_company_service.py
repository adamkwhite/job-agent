"""
Unit tests for CompanyService (database operations)
"""

import pytest

from api.company_service import CompanyService


@pytest.fixture
def temp_db(test_db_path):
    """Create a temporary database for testing using centralized test_db_path"""
    import sqlite3

    # Create companies table using centralized test database path
    conn = sqlite3.connect(test_db_path)
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

    # Initialize service with test database
    service = CompanyService(db_path=str(test_db_path))

    return service


def test_add_company_success(temp_db):
    """Test successfully adding a new company"""
    result = temp_db.add_company(
        name="Test Company", careers_url="https://example.com/careers", notes="Test notes"
    )

    assert result["success"] is True
    assert result["company"]["name"] == "Test Company"
    assert result["company"]["careers_url"] == "https://example.com/careers"
    assert result["company"]["id"] == 1


def test_add_duplicate_company(temp_db):
    """Test that duplicate companies are rejected"""
    # Add first company
    temp_db.add_company(name="Test Company", careers_url="https://example.com/careers")

    # Try to add same company again
    result = temp_db.add_company(name="Test Company", careers_url="https://example.com/careers")

    assert result["success"] is False
    assert "already exists" in result["error"]


def test_get_all_companies(temp_db):
    """Test retrieving all companies"""
    # Add multiple companies
    temp_db.add_company("Company A", "https://a.com/careers")
    temp_db.add_company("Company B", "https://b.com/careers")
    temp_db.add_company("Company C", "https://c.com/careers")

    companies = temp_db.get_all_companies()

    assert len(companies) == 3
    assert companies[0]["name"] == "Company A"


def test_get_active_companies_only(temp_db):
    """Test filtering for active companies"""
    # Add companies
    temp_db.add_company("Active Co", "https://active.com/careers")
    result = temp_db.add_company("Inactive Co", "https://inactive.com/careers")

    # Toggle one to inactive
    temp_db.toggle_active(result["company"]["id"])

    # Get active only
    companies = temp_db.get_all_companies(active_only=True)

    assert len(companies) == 1
    assert companies[0]["name"] == "Active Co"


def test_get_company_by_id(temp_db):
    """Test retrieving a specific company by ID"""
    result = temp_db.add_company("Test Co", "https://test.com/careers")
    company_id = result["company"]["id"]

    company = temp_db.get_company(company_id)

    assert company is not None
    assert company["name"] == "Test Co"
    assert company["id"] == company_id


def test_get_nonexistent_company(temp_db):
    """Test that getting non-existent company returns None"""
    company = temp_db.get_company(999)

    assert company is None


def test_toggle_active_status(temp_db):
    """Test toggling company active status"""
    result = temp_db.add_company("Test Co", "https://test.com/careers")
    company_id = result["company"]["id"]

    # Should start active (1)
    company = temp_db.get_company(company_id)
    assert company["active"] == 1

    # Toggle to inactive
    new_status = temp_db.toggle_active(company_id)
    assert new_status is False

    # Toggle back to active
    new_status = temp_db.toggle_active(company_id)
    assert new_status is True


def test_add_companies_batch_success(temp_db):
    """Test batch adding multiple companies"""
    companies = [
        {
            "name": "Boston Dynamics",
            "careers_url": "https://bostondynamics.com/careers",
            "notes": "Test note A",
        },
        {
            "name": "Agility Robotics",
            "careers_url": "https://agilityrobotics.com/careers",
            "notes": "Test note B",
        },
        {
            "name": "Skydio Corporation",
            "careers_url": "https://skydio.com/careers",
            "notes": "Test note C",
        },
    ]

    result = temp_db.add_companies_batch(companies, similarity_threshold=90.0)

    assert result["added"] == 3
    assert result["skipped_duplicates"] == 0
    assert result["errors"] == 0
    assert len(result["details"]) == 3


def test_add_companies_batch_with_duplicates(temp_db):
    """Test batch import skips fuzzy duplicates"""
    # Add one company first
    temp_db.add_company("Boston Dynamics", "https://bostondynamics.com/careers")

    companies = [
        {
            "name": "Boston Dynamics Inc",  # Fuzzy match
            "careers_url": "https://bostondynamics.com/careers",
            "notes": "Duplicate",
        },
        {
            "name": "Agility Robotics",
            "careers_url": "https://agility.io/careers",
            "notes": "New company",
        },
    ]

    result = temp_db.add_companies_batch(companies, similarity_threshold=90.0)

    assert result["added"] == 1  # Only Agility
    assert result["skipped_duplicates"] == 1  # Boston Dynamics duplicate


def test_add_companies_batch_missing_fields(temp_db):
    """Test batch import handles missing required fields"""
    companies = [
        {
            "name": "",  # Missing name
            "careers_url": "https://a.com/careers",
        },
        {
            "name": "Valid Company",
            "careers_url": "",  # Missing URL
        },
        {
            "name": "Good Company",
            "careers_url": "https://good.com/careers",
        },
    ]

    result = temp_db.add_companies_batch(companies, similarity_threshold=90.0)

    assert result["added"] == 1  # Only Good Company
    assert result["errors"] == 2  # Two invalid entries


def test_add_companies_batch_empty_list(temp_db):
    """Test batch import with empty list"""
    result = temp_db.add_companies_batch([], similarity_threshold=90.0)

    assert result["added"] == 0
    assert result["skipped_duplicates"] == 0
    assert result["errors"] == 0


def test_add_companies_batch_exact_duplicate_from_db(temp_db):
    """Test batch import detects exact duplicates from database UNIQUE constraint"""
    # Add company first
    temp_db.add_company("Test Company", "https://test.com/careers")

    # Try to add exact same company
    companies = [
        {
            "name": "Test Company",  # Exact match
            "careers_url": "https://test.com/careers",  # Exact match
        }
    ]

    result = temp_db.add_companies_batch(companies, similarity_threshold=90.0)

    assert result["added"] == 0
    assert result["skipped_duplicates"] == 1


def test_add_companies_batch_within_batch_deduplication(temp_db):
    """Test batch import deduplicates within the batch itself"""
    companies = [
        {
            "name": "Figure AI",
            "careers_url": "https://figure.ai/careers",
        },
        {
            "name": "Figure AI Inc",  # Similar to first
            "careers_url": "https://figure.ai/careers",
        },
        {
            "name": "Bright Machines",
            "careers_url": "https://brightmachines.com/careers",
        },
    ]

    result = temp_db.add_companies_batch(companies, similarity_threshold=90.0)

    # First Figure AI added, second skipped, Bright Machines added
    assert result["added"] == 2
    assert result["skipped_duplicates"] == 1


# ===== Auto-Disable Failure Tracking Tests =====


def test_increment_company_failures_first_failure(temp_db):
    """Test incrementing failures from 0 to 1"""
    result = temp_db.add_company("Test Co", "https://test.com/careers")
    company_id = result["company"]["id"]

    # Increment failures
    new_count = temp_db.increment_company_failures(company_id, "0 jobs found")

    assert new_count == 1

    # Verify in database
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 1
    assert company["last_failure_reason"] == "0 jobs found"


def test_increment_company_failures_multiple_times(temp_db):
    """Test incrementing failures multiple times (simulating 5 consecutive failures)"""
    result = temp_db.add_company("Failing Co", "https://failing.com/careers")
    company_id = result["company"]["id"]

    # Simulate 5 consecutive failures
    count1 = temp_db.increment_company_failures(company_id, "timeout")
    assert count1 == 1

    count2 = temp_db.increment_company_failures(company_id, "404 not found")
    assert count2 == 2

    count3 = temp_db.increment_company_failures(company_id, "0 jobs found")
    assert count3 == 3

    count4 = temp_db.increment_company_failures(company_id, "parse error")
    assert count4 == 4

    count5 = temp_db.increment_company_failures(company_id, "0 jobs found")
    assert count5 == 5

    # Verify final state
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 5
    assert company["last_failure_reason"] == "0 jobs found"  # Most recent reason


def test_reset_company_failures_after_success(temp_db):
    """Test resetting failure counter after successful scrape"""
    result = temp_db.add_company("Recovery Co", "https://recovery.com/careers")
    company_id = result["company"]["id"]

    # Increment to 3 failures
    temp_db.increment_company_failures(company_id, "timeout")
    temp_db.increment_company_failures(company_id, "0 jobs")
    temp_db.increment_company_failures(company_id, "parse error")

    # Verify failures incremented
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 3
    assert company["last_failure_reason"] is not None

    # Reset after successful scrape
    temp_db.reset_company_failures(company_id)

    # Verify reset
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 0
    assert company["last_failure_reason"] is None


def test_reset_company_failures_zero_to_zero(temp_db):
    """Test resetting failures when already at 0 (edge case)"""
    result = temp_db.add_company("Never Failed Co", "https://neverfailed.com/careers")
    company_id = result["company"]["id"]

    # Reset when already at 0
    temp_db.reset_company_failures(company_id)

    # Should still be 0
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 0
    assert company["last_failure_reason"] is None


def test_disable_company_sets_inactive_and_timestamp(temp_db):
    """Test that disable_company sets active=0 and records auto_disabled_at"""
    result = temp_db.add_company("Disabled Co", "https://disabled.com/careers")
    company_id = result["company"]["id"]

    # Verify starts active
    company = temp_db.get_company(company_id)
    assert company["active"] == 1
    assert company["auto_disabled_at"] is None

    # Disable company
    temp_db.disable_company(company_id)

    # Verify disabled
    company = temp_db.get_company(company_id)
    assert company["active"] == 0
    assert company["auto_disabled_at"] is not None
    assert company["last_failure_reason"] == "auto_disabled_5_failures"


def test_disable_company_custom_reason(temp_db):
    """Test disabling company with custom reason"""
    result = temp_db.add_company("Manual Disabled Co", "https://manual.com/careers")
    company_id = result["company"]["id"]

    # Disable with custom reason
    temp_db.disable_company(company_id, reason="manually_disabled_by_admin")

    # Verify custom reason stored
    company = temp_db.get_company(company_id)
    assert company["active"] == 0
    assert company["last_failure_reason"] == "manually_disabled_by_admin"


def test_get_auto_disabled_companies_empty(temp_db):
    """Test get_auto_disabled_companies returns empty list when none disabled"""
    # Add active companies
    temp_db.add_company("Active 1", "https://active1.com/careers")
    temp_db.add_company("Active 2", "https://active2.com/careers")

    disabled = temp_db.get_auto_disabled_companies()

    assert len(disabled) == 0


def test_get_auto_disabled_companies_returns_disabled(temp_db):
    """Test get_auto_disabled_companies returns only auto-disabled companies"""
    # Add companies
    result1 = temp_db.add_company("Disabled 1", "https://disabled1.com/careers")
    temp_db.add_company("Active", "https://active.com/careers")
    result3 = temp_db.add_company("Disabled 2", "https://disabled2.com/careers")

    # Disable 2 companies
    temp_db.disable_company(result1["company"]["id"])
    temp_db.disable_company(result3["company"]["id"])

    # Get auto-disabled list
    disabled = temp_db.get_auto_disabled_companies()

    assert len(disabled) == 2
    assert disabled[0]["name"] in ["Disabled 1", "Disabled 2"]
    assert disabled[1]["name"] in ["Disabled 1", "Disabled 2"]
    assert all(company["auto_disabled_at"] is not None for company in disabled)


def test_get_auto_disabled_companies_ordered_by_date(temp_db):
    """Test that auto-disabled companies are ordered by auto_disabled_at DESC"""
    import time

    # Add and disable multiple companies with delay
    result1 = temp_db.add_company("First Disabled", "https://first.com/careers")
    temp_db.disable_company(result1["company"]["id"])

    time.sleep(0.1)  # Small delay to ensure different timestamps

    result2 = temp_db.add_company("Second Disabled", "https://second.com/careers")
    temp_db.disable_company(result2["company"]["id"])

    # Get auto-disabled list (should be ordered newest first)
    disabled = temp_db.get_auto_disabled_companies()

    assert len(disabled) == 2
    # Most recently disabled should be first
    assert disabled[0]["name"] == "Second Disabled"
    assert disabled[1]["name"] == "First Disabled"


def test_full_failure_to_disable_workflow(temp_db):
    """Integration test: Full workflow from 0 failures → 5 failures → auto-disable"""
    result = temp_db.add_company("Workflow Co", "https://workflow.com/careers")
    company_id = result["company"]["id"]

    # Verify starts at 0 failures, active
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 0
    assert company["active"] == 1
    assert company["auto_disabled_at"] is None

    # Simulate 4 failures (not yet disabled)
    for i in range(4):
        count = temp_db.increment_company_failures(company_id, f"failure_{i + 1}")
        assert count == i + 1

    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 4
    assert company["active"] == 1  # Still active

    # 5th failure triggers auto-disable
    count = temp_db.increment_company_failures(company_id, "failure_5")
    assert count == 5

    # Manually disable (simulating scraper auto-disable logic)
    temp_db.disable_company(company_id)

    # Verify final state
    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 5
    assert company["active"] == 0  # Now disabled
    assert company["auto_disabled_at"] is not None

    # Verify appears in auto-disabled list
    disabled = temp_db.get_auto_disabled_companies()
    assert len(disabled) == 1
    assert disabled[0]["name"] == "Workflow Co"


def test_failure_then_success_then_failure_workflow(temp_db):
    """Integration test: Failures → Success (reset) → Failures again"""
    result = temp_db.add_company("Flaky Co", "https://flaky.com/careers")
    company_id = result["company"]["id"]

    # 2 failures
    temp_db.increment_company_failures(company_id, "timeout")
    temp_db.increment_company_failures(company_id, "parse error")

    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 2

    # Success - reset counter
    temp_db.reset_company_failures(company_id)

    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 0
    assert company["last_failure_reason"] is None

    # New failures start from 0 again
    temp_db.increment_company_failures(company_id, "new failure")

    company = temp_db.get_company(company_id)
    assert company["consecutive_failures"] == 1
    assert company["last_failure_reason"] == "new failure"


# ===== Auto-Discovery Tests =====


def test_company_exists_case_insensitive(temp_db):
    """Test company_exists is case-insensitive"""
    temp_db.add_company("Boston Dynamics", "https://bostondynamics.com/careers")

    # Exact match
    assert temp_db.company_exists("Boston Dynamics") is True

    # Different case
    assert temp_db.company_exists("boston dynamics") is True
    assert temp_db.company_exists("BOSTON DYNAMICS") is True
    assert temp_db.company_exists("BoStOn DyNaMiCs") is True

    # Non-existent
    assert temp_db.company_exists("Agility Robotics") is False


def test_company_exists_empty_string(temp_db):
    """Test company_exists returns False for empty string"""
    assert temp_db.company_exists("") is False


def test_company_exists_nonexistent(temp_db):
    """Test company_exists returns False for non-existent company"""
    temp_db.add_company("Existing Co", "https://existing.com/careers")

    assert temp_db.company_exists("Nonexistent Co") is False


def test_add_discovered_company_success(temp_db):
    """Test successfully adding a discovered company"""
    result = temp_db.add_discovered_company(
        name="Auto Discovered Co", source="email_auto_discovery"
    )

    assert result["success"] is True
    assert result["company"]["name"] == "Auto Discovered Co"
    assert result["company"]["active"] is False  # Inactive by default
    assert "placeholder" in result["company"]["careers_url"].lower()
    assert "email_auto_discovery" in result["company"]["notes"]
    assert "manual review" in result["company"]["notes"].lower()


def test_add_discovered_company_custom_url(temp_db):
    """Test adding discovered company with custom career page URL"""
    result = temp_db.add_discovered_company(
        name="Custom URL Co",
        source="company_monitoring",
        careers_url="https://custom.com/careers",
    )

    assert result["success"] is True
    assert result["company"]["careers_url"] == "https://custom.com/careers"


def test_add_discovered_company_duplicate_name(temp_db):
    """Test adding discovered company with duplicate name (different URL)"""
    # Add first company
    temp_db.add_company("Duplicate Test", "https://first.com/careers")

    # Try to add discovered company with same name but different URL
    result = temp_db.add_discovered_company(name="Duplicate Test", source="email_auto_discovery")

    # Should succeed because URL is different (UNIQUE constraint is on name+URL combo)
    assert result["success"] is True
    assert result["company"]["name"] == "Duplicate Test"
    assert "placeholder" in result["company"]["careers_url"].lower()


def test_add_discovered_company_exact_duplicate(temp_db):
    """Test adding discovered company that exactly matches existing"""
    # Add discovered company first
    temp_db.add_discovered_company(name="Exact Dup", source="email")

    # Try to add same company again
    result = temp_db.add_discovered_company(name="Exact Dup", source="email")

    assert result["success"] is False
    assert "already exists" in result["error"]


def test_add_discovered_company_inactive_by_default(temp_db):
    """Test that discovered companies are added as inactive"""
    result = temp_db.add_discovered_company(name="Needs Review Co", source="linkedin")

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert company["active"] == 0  # Inactive
    assert company["auto_disabled_at"] is None  # Not auto-disabled, just inactive


def test_add_discovered_company_source_in_notes(temp_db):
    """Test that source is recorded in notes"""
    result = temp_db.add_discovered_company(name="Source Test Co", source="builtin_auto_discovery")

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "builtin_auto_discovery" in company["notes"]
    assert "manual review" in company["notes"].lower()


# ===== Enhanced Notes Tests (Career URL Extraction) =====


def test_add_discovered_company_notes_placeholder_url(temp_db):
    """Test notes indicate placeholder URL needs manual review"""
    result = temp_db.add_discovered_company(
        name="Placeholder Co",
        source="email_auto_discovery",
        careers_url="https://placeholder.com/careers",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "Needs manual review and careers URL" in company["notes"]
    assert "placeholder" in company["careers_url"]


def test_add_discovered_company_notes_generic_fallback(temp_db):
    """Test notes indicate generic fallback URL needs verification"""
    # Generic fallback pattern: https://domain.com/jobs (3 slashes, ends with /jobs)
    result = temp_db.add_discovered_company(
        name="Generic Fallback Co",
        source="email_auto_discovery",
        careers_url="https://example-company.com/jobs",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "generic fallback - verify before activating" in company["notes"]
    assert company["careers_url"] == "https://example-company.com/jobs"


def test_add_discovered_company_notes_extracted_workday_url(temp_db):
    """Test notes indicate auto-extracted URL from Workday"""
    result = temp_db.add_discovered_company(
        name="Workday Co",
        source="email_auto_discovery",
        careers_url="https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "auto-extracted from job posting" in company["notes"]
    assert "verify before activating" in company["notes"]
    assert "myworkdayjobs.com" in company["careers_url"]


def test_add_discovered_company_notes_extracted_greenhouse_url(temp_db):
    """Test notes indicate auto-extracted URL from Greenhouse"""
    result = temp_db.add_discovered_company(
        name="Greenhouse Co",
        source="email_auto_discovery",
        careers_url="https://job-boards.greenhouse.io/figureai",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "auto-extracted from job posting" in company["notes"]
    assert "verify before activating" in company["notes"]
    assert "greenhouse.io" in company["careers_url"]


def test_add_discovered_company_notes_extracted_lever_url(temp_db):
    """Test notes indicate auto-extracted URL from Lever"""
    result = temp_db.add_discovered_company(
        name="Lever Co",
        source="email_auto_discovery",
        careers_url="https://jobs.lever.co/kuka",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    assert "auto-extracted from job posting" in company["notes"]
    assert "verify before activating" in company["notes"]
    assert "lever.co" in company["careers_url"]


def test_add_discovered_company_notes_generic_fallback_not_three_slashes(temp_db):
    """Test that deep URL paths don't trigger generic fallback warning"""
    # URL with more than 3 slashes should get "auto-extracted" notes, not "generic fallback"
    result = temp_db.add_discovered_company(
        name="Deep Path Co",
        source="email_auto_discovery",
        careers_url="https://example.com/company/deep/path/jobs",
    )

    company_id = result["company"]["id"]
    company = temp_db.get_company(company_id)

    # Should NOT be treated as generic fallback (too many slashes)
    assert "auto-extracted from job posting" in company["notes"]
    assert "generic fallback" not in company["notes"]
