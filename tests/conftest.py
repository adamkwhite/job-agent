"""
Pytest configuration for job-agent tests.

This conftest.py adds the project root to sys.path to ensure
that tests can import from the src package correctly.
"""

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Add project root to Python path so tests can import src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Ensure DATABASE_PATH is set for test isolation
# This prevents accidental production database usage
if "pytest" in sys.modules and "DATABASE_PATH" not in os.environ:
    # Set default test database path if not already set
    default_test_path = str(Path(tempfile.gettempdir()) / "pytest_test_jobs.db")
    os.environ["DATABASE_PATH"] = default_test_path
    print(f"⚠️  DATABASE_PATH not set, using default: {default_test_path}")

from src.database import JobDatabase  # noqa: E402


@pytest.fixture(scope="function")
def test_db() -> Generator[JobDatabase, None, None]:
    """
    Provides isolated test database for each test.

    Creates a temporary database in a temp directory and sets DATABASE_PATH
    environment variable to ensure all JobDatabase() calls use the test path.
    Each test gets a fresh, isolated database.

    Yields:
        JobDatabase: Initialized test database instance

    Example:
        def test_add_job(test_db):
            test_db.add_job({"title": "Test", "company": "Acme"})
            assert test_db.get_job_count() == 1
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_jobs.db"
        old_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(db_path)

        try:
            db = JobDatabase(str(db_path))
            yield db
        finally:
            # Restore original environment
            if old_path is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = old_path


@pytest.fixture(scope="function")
def test_db_path() -> Generator[str, None, None]:
    """
    Provides test database path without initialization.

    Useful when you need to create JobDatabase manually or pass path to
    functions that create their own database connection.

    Yields:
        str: Path to temporary test database

    Example:
        def test_custom_init(test_db_path):
            db = JobDatabase(test_db_path, profile="test")
            assert db.profile == "test"
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_jobs.db"
        old_path = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(db_path)

        try:
            yield str(db_path)
        finally:
            # Restore original environment
            if old_path is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = old_path
