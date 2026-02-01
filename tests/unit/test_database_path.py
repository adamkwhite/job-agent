"""
Tests for DATABASE_PATH environment variable functionality.

Verifies that JobDatabase correctly uses DATABASE_PATH for test isolation
and prevents production database pollution during test execution.
"""

import os
import tempfile
from pathlib import Path

from src.database import JobDatabase


class TestDatabasePathEnvironmentVariable:
    """Test DATABASE_PATH environment variable behavior"""

    def test_default_path_no_env(self, mocker):
        """Test that JobDatabase uses default path when no env var set"""
        # Mock init_database to prevent actual database creation
        mock_init = mocker.patch.object(JobDatabase, "init_database")

        # Save and remove DATABASE_PATH
        old_path = os.environ.pop("DATABASE_PATH", None)

        try:
            db = JobDatabase()
            # Verify path is set to default
            assert str(db.db_path) == "data/jobs.db"
            # Verify init was called (but mocked so no file created)
            mock_init.assert_called_once()
        finally:
            # Restore environment
            if old_path:
                os.environ["DATABASE_PATH"] = old_path

    def test_env_var_override(self):
        """Test that DATABASE_PATH env var overrides default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = str(Path(tmpdir) / "custom.db")
            old_path = os.environ.get("DATABASE_PATH")

            try:
                os.environ["DATABASE_PATH"] = test_path
                db = JobDatabase()
                assert str(db.db_path) == test_path
            finally:
                if old_path:
                    os.environ["DATABASE_PATH"] = old_path
                else:
                    os.environ.pop("DATABASE_PATH", None)

    def test_explicit_parameter_override(self):
        """Test that explicit db_path parameter overrides env var"""
        with tempfile.TemporaryDirectory() as tmpdir:
            explicit_path = str(Path(tmpdir) / "explicit.db")
            env_path = str(Path(tmpdir) / "env.db")

            old_path = os.environ.get("DATABASE_PATH")

            try:
                os.environ["DATABASE_PATH"] = env_path
                db = JobDatabase(db_path=explicit_path)
                assert str(db.db_path) == explicit_path
            finally:
                if old_path:
                    os.environ["DATABASE_PATH"] = old_path
                else:
                    os.environ.pop("DATABASE_PATH", None)

    def test_fixture_isolation(self, test_db):
        """Test that test_db fixture provides isolated database"""
        # test_db fixture should not point to production database
        assert str(test_db.db_path) != "data/jobs.db"
        assert "tmp" in str(test_db.db_path).lower() or "temp" in str(test_db.db_path).lower()

    def test_fixture_creates_schema(self, test_db):
        """Test that test_db fixture creates database schema"""
        # Verify jobs table exists
        import sqlite3

        conn = sqlite3.connect(test_db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='jobs'
        """)
        assert cursor.fetchone() is not None, "jobs table should exist"

        conn.close()

    def test_fixture_path_isolation(self, test_db_path):
        """Test that test_db_path fixture provides isolated path"""
        assert test_db_path != "data/jobs.db"
        assert "tmp" in test_db_path.lower() or "temp" in test_db_path.lower()

    def test_fixtures_are_independent(self, test_db, test_db_path):
        """Test that test_db and test_db_path are independent fixtures"""
        # Each fixture creates its own isolated database
        # This is expected behavior for maximum test isolation
        assert str(test_db.db_path) != "data/jobs.db"
        assert test_db_path != "data/jobs.db"
        # Both should be in temp directories
        assert "tmp" in str(test_db.db_path).lower() or "temp" in str(test_db.db_path).lower()
        assert "tmp" in test_db_path.lower() or "temp" in test_db_path.lower()


class TestProductionDatabaseProtection:
    """Test that production database is protected during tests"""

    def test_production_db_not_modified_by_test_db(self, test_db):
        """Test that using test_db doesn't touch production database"""
        # Add a job to test database
        job_data = {
            "title": "Test Job",
            "company": "Test Company",
            "location": "Remote",
            "link": "https://example.com/test",
            "keywords_matched": ["test"],
            "source": "test",
        }

        test_db.add_job(job_data)

        # Verify production database path is different
        assert str(test_db.db_path) != "data/jobs.db"

    def test_env_var_set_during_fixture_execution(self, test_db_path):
        """Test that DATABASE_PATH env var is set during test execution"""
        current_env_path = os.environ.get("DATABASE_PATH")
        assert current_env_path == test_db_path


class TestBackwardCompatibility:
    """Test that existing code continues to work"""

    def test_no_parameters_uses_env_or_default(self, mocker):
        """Test JobDatabase() with no parameters works as expected"""
        # Mock init_database to prevent actual database creation
        _mock_init = mocker.patch.object(JobDatabase, "init_database")

        old_path = os.environ.get("DATABASE_PATH")

        try:
            # Without env var, should use default
            os.environ.pop("DATABASE_PATH", None)
            db1 = JobDatabase()
            assert str(db1.db_path) == "data/jobs.db"

            # With env var, should use env var
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = str(Path(tmpdir) / "test.db")
                os.environ["DATABASE_PATH"] = test_path
                db2 = JobDatabase()
                assert str(db2.db_path) == test_path

        finally:
            if old_path:
                os.environ["DATABASE_PATH"] = old_path
            else:
                os.environ.pop("DATABASE_PATH", None)

    def test_profile_parameter_still_works(self, test_db_path):
        """Test that profile parameter still works with new path logic"""
        db = JobDatabase(db_path=test_db_path, profile="test_profile")
        assert db.profile == "test_profile"
        assert str(db.db_path) == test_db_path
