"""
Simple API tests without mocking - just test a few key endpoints
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

from api.app import app
from api.company_service import CompanyService


@pytest.fixture
def client():
    """Create Flask test client with temporary database"""
    # Create temp database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    temp_db = Path(db_path)

    # Create companies table
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        """
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
    """
    )
    conn.commit()
    conn.close()

    # Create new service with temp database
    test_service = CompanyService(db_path=str(temp_db))

    # Patch app's company_service with test service using sys.modules
    app_module = sys.modules["api.app"]
    original_service = app_module.company_service
    app_module.company_service = test_service

    # Configure app for testing
    app.config["TESTING"] = True

    # Yield test client
    with app.test_client() as client:
        yield client

    # Cleanup
    app_module.company_service = original_service
    temp_db.unlink(missing_ok=True)


def test_home_endpoint(client):
    """Test API health check endpoint"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "endpoints" in data
    assert "version" in data


def test_add_company_missing_name(client):
    """Test validation - missing name field"""
    response = client.post("/add-company", json={"careers_url": "https://test.com/careers"})

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_add_company_missing_url(client):
    """Test validation - missing URL field"""
    response = client.post("/add-company", json={"name": "Test Company"})

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False


def test_get_companies_endpoint_exists(client):
    """Test that /companies endpoint works"""
    response = client.get("/companies")

    assert response.status_code == 200
    data = response.get_json()
    assert "companies" in data
    assert "count" in data


def test_get_nonexistent_company(client):
    """Test getting a company that doesn't exist returns 404"""
    response = client.get("/company/99999")

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
