"""Unit tests for LLM failure update functionality (Issue #92)"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from database import JobDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Create database instance
    db = JobDatabase(db_path)

    # Create tables (if not created automatically)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure llm_extraction_failures table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_extraction_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            failure_reason TEXT NOT NULL,
            markdown_path TEXT,
            error_details TEXT,
            occurred_at TEXT DEFAULT CURRENT_TIMESTAMP,
            review_action TEXT DEFAULT 'pending',
            reviewed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield db

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_update_llm_failure_to_retry(temp_db):
    """Test updating LLM failure to 'retry' action"""
    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Test timeout",
        markdown_path="data/test.md",
        error_details="Test error",
    )

    # Update to retry
    success = temp_db.update_llm_failure(failure_id, "retry")
    assert success is True

    # Verify the update
    failures = temp_db.get_llm_failures(review_action="retry")
    assert len(failures) == 1
    assert failures[0]["id"] == failure_id
    assert failures[0]["review_action"] == "retry"
    assert failures[0]["reviewed_at"] is not None


def test_update_llm_failure_to_skip(temp_db):
    """Test updating LLM failure to 'skip' action"""
    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Test error",
        markdown_path="data/test.md",
        error_details="Test error",
    )

    # Update to skip
    success = temp_db.update_llm_failure(failure_id, "skip")
    assert success is True

    # Verify the update
    failures = temp_db.get_llm_failures(review_action="skip")
    assert len(failures) == 1
    assert failures[0]["id"] == failure_id
    assert failures[0]["review_action"] == "skip"
    assert failures[0]["reviewed_at"] is not None


def test_update_llm_failure_invalid_id(temp_db):
    """Test updating non-existent LLM failure returns False"""
    # Try to update a failure that doesn't exist
    success = temp_db.update_llm_failure(99999, "retry")
    assert success is False


def test_update_llm_failure_sets_reviewed_at(temp_db):
    """Test that update sets reviewed_at timestamp"""
    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Test error",
        markdown_path="data/test.md",
        error_details="Test error",
    )

    # Initially reviewed_at should be None
    failures = temp_db.get_llm_failures(review_action="pending")
    assert failures[0]["reviewed_at"] is None

    # Update the failure
    temp_db.update_llm_failure(failure_id, "retry")

    # Now reviewed_at should be set
    failures = temp_db.get_llm_failures(review_action="retry")
    assert failures[0]["reviewed_at"] is not None


def test_update_llm_failure_multiple_times(temp_db):
    """Test updating the same failure multiple times"""
    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Test error",
        markdown_path="data/test.md",
        error_details="Test error",
    )

    # Update to retry
    success = temp_db.update_llm_failure(failure_id, "retry")
    assert success is True

    # Update back to pending
    success = temp_db.update_llm_failure(failure_id, "pending")
    assert success is True

    # Verify final state
    failures = temp_db.get_llm_failures(review_action="pending")
    assert len(failures) == 1
    assert failures[0]["id"] == failure_id


def test_get_llm_failures_filters_correctly(temp_db):
    """Test that get_llm_failures filters by review_action"""
    # Create multiple failures
    id1 = temp_db.store_llm_failure("Company 1", "Error 1", "path1.md", "details1")
    id2 = temp_db.store_llm_failure("Company 2", "Error 2", "path2.md", "details2")
    id3 = temp_db.store_llm_failure("Company 3", "Error 3", "path3.md", "details3")

    # Update them to different states
    temp_db.update_llm_failure(id1, "retry")
    temp_db.update_llm_failure(id2, "skip")
    # id3 stays pending

    # Test filtering
    pending = temp_db.get_llm_failures(review_action="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == id3

    retry = temp_db.get_llm_failures(review_action="retry")
    assert len(retry) == 1
    assert retry[0]["id"] == id1

    skip = temp_db.get_llm_failures(review_action="skip")
    assert len(skip) == 1
    assert skip[0]["id"] == id2


def test_get_llm_failures_without_filter(temp_db):
    """Test that get_llm_failures without filter returns all"""
    # Create multiple failures
    id1 = temp_db.store_llm_failure("Company 1", "Error 1", "path1.md", "details1")
    temp_db.store_llm_failure("Company 2", "Error 2", "path2.md", "details2")

    # Update one
    temp_db.update_llm_failure(id1, "retry")

    # Get all failures (no filter)
    all_failures = temp_db.get_llm_failures()
    assert len(all_failures) == 2


def test_get_llm_failures_limit(temp_db):
    """Test that get_llm_failures respects limit parameter"""
    # Create 5 failures
    for i in range(5):
        temp_db.store_llm_failure(f"Company {i}", f"Error {i}", f"path{i}.md", f"details{i}")

    # Get with limit=3
    failures = temp_db.get_llm_failures(limit=3)
    assert len(failures) == 3


def test_update_llm_failure_preserves_other_fields(temp_db):
    """Test that update only changes review_action and reviewed_at"""
    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Original error",
        markdown_path="data/original.md",
        error_details="Original details",
    )

    # Get original values
    original = temp_db.get_llm_failures()[0]

    # Update the failure
    temp_db.update_llm_failure(failure_id, "retry")

    # Get updated values
    updated = temp_db.get_llm_failures(review_action="retry")[0]

    # Verify other fields are unchanged
    assert updated["company_name"] == original["company_name"]
    assert updated["failure_reason"] == original["failure_reason"]
    assert updated["markdown_path"] == original["markdown_path"]
    assert updated["error_details"] == original["error_details"]
    assert updated["occurred_at"] == original["occurred_at"]


def test_update_llm_failure_database_error(temp_db, monkeypatch):
    """Test that update_llm_failure handles database errors gracefully"""

    # Create a test failure
    failure_id = temp_db.store_llm_failure(
        company_name="Test Company",
        failure_reason="Test error",
        markdown_path="data/test.md",
        error_details="Test error",
    )

    # Mock sqlite3.connect to raise an exception
    def mock_connect(*_args, **_kwargs):
        raise Exception("Database connection failed")

    monkeypatch.setattr("sqlite3.connect", mock_connect)

    # Try to update - should handle error gracefully
    success = temp_db.update_llm_failure(failure_id, "retry")
    assert success is False
