"""
Simple API tests without mocking - just test a few key endpoints
"""

import pytest

from api.app import app


@pytest.fixture
def client():
    """Create Flask test client"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
