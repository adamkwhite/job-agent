"""
Unit tests for CompanyService (database operations)
"""

import tempfile
from pathlib import Path

import pytest

from api.company_service import CompanyService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    import sqlite3

    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    db_path = Path(path)

    # Create companies table
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
            UNIQUE(name, careers_url)
        )
    """)
    conn.commit()
    conn.close()

    # Initialize service with temp database
    service = CompanyService(db_path=str(db_path))

    yield service

    # Cleanup
    db_path.unlink(missing_ok=True)


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
