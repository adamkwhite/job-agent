"""Tests for URL validation tracking in database."""

import sqlite3
from datetime import datetime

import pytest


@pytest.fixture
def temp_db(test_db):
    """Create a temporary database for testing using centralized test_db."""
    return test_db


@pytest.fixture
def sample_job(temp_db):
    """Create a sample job for testing."""
    job_data = {
        "title": "Test Engineer",
        "company": "Test Corp",
        "location": "Remote",
        "link": "https://example.com/job/123",
        "keywords_matched": ["test", "engineer"],
        "source": "test_source",
    }
    job_id = temp_db.add_job(job_data)

    # Get the job hash
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT job_hash FROM jobs WHERE id = ?", (job_id,))
    job_hash = cursor.fetchone()[0]
    conn.close()

    return job_hash


class TestURLValidation:
    """Test URL validation tracking."""

    def test_update_url_validation_valid(self, temp_db, sample_job):
        """Test updating URL status to valid."""
        temp_db.update_url_validation(sample_job, "valid")

        # Verify the status was updated
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url_status, url_checked_at FROM jobs WHERE job_hash = ?",
            (sample_job,),
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "valid"
        assert result[1] is not None  # Should have a timestamp

    def test_update_url_validation_stale(self, temp_db, sample_job):
        """Test updating URL status to stale."""
        temp_db.update_url_validation(sample_job, "stale")

        # Verify the status was updated
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_status FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "stale"

    def test_update_url_validation_404(self, temp_db, sample_job):
        """Test updating URL status to 404."""
        temp_db.update_url_validation(sample_job, "404")

        # Verify the status was updated
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_status FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "404"

    def test_update_url_validation_connection_error(self, temp_db, sample_job):
        """Test updating URL status to connection_error."""
        temp_db.update_url_validation(sample_job, "connection_error")

        # Verify the status was updated
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_status FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "connection_error"

    def test_update_url_validation_invalid_response(self, temp_db, sample_job):
        """Test updating URL status to invalid_response."""
        temp_db.update_url_validation(sample_job, "invalid_response")

        # Verify the status was updated
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_status FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "invalid_response"

    def test_update_url_validation_timestamp(self, temp_db, sample_job):
        """Test that url_checked_at timestamp is set correctly."""
        before = datetime.now()
        temp_db.update_url_validation(sample_job, "valid")
        after = datetime.now()

        # Verify the timestamp is between before and after
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_checked_at FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        checked_at = datetime.fromisoformat(result[0])
        assert before <= checked_at <= after

    def test_update_url_validation_updates_updated_at(self, temp_db, sample_job):
        """Test that updated_at timestamp is also updated."""
        # Get original updated_at
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT updated_at FROM jobs WHERE job_hash = ?", (sample_job,))
        original_updated_at = cursor.fetchone()[0]
        conn.close()

        # Wait a tiny bit to ensure timestamp changes
        import time

        time.sleep(0.01)

        # Update URL validation
        temp_db.update_url_validation(sample_job, "valid")

        # Get new updated_at
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT updated_at FROM jobs WHERE job_hash = ?", (sample_job,))
        new_updated_at = cursor.fetchone()[0]
        conn.close()

        assert new_updated_at > original_updated_at

    def test_update_url_validation_multiple_times(self, temp_db, sample_job):
        """Test updating URL validation multiple times."""
        # First update
        temp_db.update_url_validation(sample_job, "valid")

        # Second update
        temp_db.update_url_validation(sample_job, "stale")

        # Verify the latest status
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT url_status FROM jobs WHERE job_hash = ?", (sample_job,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "stale"

    def test_update_url_validation_nonexistent_job(self, temp_db):
        """Test updating URL validation for a nonexistent job."""
        # Should not raise an error, just do nothing
        temp_db.update_url_validation("nonexistent_hash", "valid")

        # Verify no error occurred
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE url_status = 'valid'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0


class TestURLValidationInDatabase:
    """Test that URL validation columns exist and work correctly."""

    def test_url_status_column_exists(self, temp_db):
        """Test that url_status column exists in database."""
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        assert "url_status" in columns

    def test_url_checked_at_column_exists(self, temp_db):
        """Test that url_checked_at column exists in database."""
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        assert "url_checked_at" in columns

    def test_url_validation_persists_in_database(self, temp_db, sample_job):
        """Test that URL validation data persists correctly in database."""
        # Update validation status
        temp_db.update_url_validation(sample_job, "stale")

        # Create a new database connection to verify persistence
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url_status, url_checked_at
            FROM jobs
            WHERE job_hash = ?
        """,
            (sample_job,),
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "stale"
        assert result[1] is not None
