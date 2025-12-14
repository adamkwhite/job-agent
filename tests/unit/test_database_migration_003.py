"""
Unit tests for database migration 003 - Filter Tracking Fields

Tests verify that:
1. Migration adds all 4 new columns correctly
2. Existing data is preserved after migration
3. Default values are set correctly
4. Existing database operations still work
5. New columns can be populated and queried
6. Migration is idempotent (can run multiple times)
7. Indexes are created for performance
"""

import importlib.util
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from database import JobDatabase

# Add src to path for migrations import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import with renaming to avoid syntax issues with numeric prefix
migration_path = (
    Path(__file__).parent.parent.parent / "src" / "migrations" / "003_filter_tracking.py"
)
spec = importlib.util.spec_from_file_location("migration_003", migration_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Could not load migration from {migration_path}")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class TestMigration003FilterTracking:
    """Test filter tracking migration (#003)"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        yield db_path
        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def db_with_existing_jobs(self, temp_db):
        """Create database with existing jobs before migration"""
        db = JobDatabase(db_path=temp_db)

        # Add sample jobs before migration
        jobs_data = [
            {
                "title": "VP Engineering",
                "company": "Robotics Corp",
                "link": "https://example.com/job1",
                "location": "Remote",
                "source": "linkedin",
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "keywords_matched": "[]",
                "source_email": "test@example.com",
                "score": 85,
                "grade": "A",
                "breakdown": '{"seniority": 30, "domain": 25}',
            },
            {
                "title": "Director of Product",
                "company": "Hardware Inc",
                "link": "https://example.com/job2",
                "location": "Toronto, ON",
                "source": "supra",
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "keywords_matched": "[]",
                "source_email": "test@example.com",
                "score": 75,
                "grade": "B",
                "breakdown": '{"seniority": 25, "domain": 20}',
            },
        ]

        job_ids = []
        for job_data in jobs_data:
            # Extract score data
            score = job_data.pop("score")
            grade = job_data.pop("grade")
            breakdown = job_data.pop("breakdown")

            # Add job
            job_id = db.add_job(job_data)
            if job_id:
                # Update score
                db.update_job_score(job_id, score, grade, breakdown)
                job_ids.append(job_id)

        return temp_db, job_ids, jobs_data

    def test_migration_adds_all_columns(self, temp_db):
        """Test that migration adds all 4 new columns"""
        # Initialize database
        JobDatabase(db_path=temp_db)

        # Run migration
        success = migration.migrate(db_path=temp_db)
        assert success is True

        # Verify all columns exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = {col[1]: col for col in cursor.fetchall()}
        conn.close()

        assert "filter_reason" in columns
        assert "filtered_at" in columns
        assert "manual_review_flag" in columns
        assert "stale_check_result" in columns

        # Verify data types
        assert columns["filter_reason"][2] == "TEXT"  # type
        assert columns["filtered_at"][2] == "TEXT"
        assert columns["manual_review_flag"][2] == "INTEGER"
        assert columns["stale_check_result"][2] == "TEXT"

        # Verify default values
        assert columns["manual_review_flag"][4] == "0"  # default value
        assert columns["stale_check_result"][4] == "'not_checked'"

    def test_migration_preserves_existing_data(self, db_with_existing_jobs):
        """Test that existing jobs are not affected by migration"""
        temp_db, job_ids, original_jobs = db_with_existing_jobs

        # Get data before migration
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, company, link, fit_score FROM jobs ORDER BY id")
        before_migration = cursor.fetchall()
        conn.close()

        # Run migration
        success = migration.migrate(db_path=temp_db)
        assert success is True

        # Get data after migration
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, company, link, fit_score FROM jobs ORDER BY id")
        after_migration = cursor.fetchall()
        conn.close()

        # Verify data unchanged
        assert len(before_migration) == len(after_migration)
        assert before_migration == after_migration

        # Verify specific fields
        assert after_migration[0][1] == "VP Engineering"  # title
        assert after_migration[0][4] == 85  # fit_score
        assert after_migration[1][1] == "Director of Product"
        assert after_migration[1][4] == 75

    def test_migration_sets_correct_defaults(self, db_with_existing_jobs):
        """Test that new columns have correct default values for existing jobs"""
        temp_db, job_ids, _ = db_with_existing_jobs

        # Run migration

        migration.migrate(db_path=temp_db)

        # Check defaults on existing jobs
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filter_reason, filtered_at, manual_review_flag, stale_check_result FROM jobs"
        )
        results = cursor.fetchall()
        conn.close()

        for row in results:
            filter_reason, filtered_at, manual_review_flag, stale_check_result = row
            assert filter_reason is None  # NULL by default
            assert filtered_at is None  # NULL by default
            assert manual_review_flag == 0  # DEFAULT 0
            assert stale_check_result == "not_checked"  # DEFAULT 'not_checked'

    def test_migration_is_idempotent(self, temp_db):
        """Test that migration can be run multiple times without errors"""
        JobDatabase(db_path=temp_db)

        # Run migration first time
        success1 = migration.migrate(db_path=temp_db)
        assert success1 is True

        # Run migration second time
        success2 = migration.migrate(db_path=temp_db)
        assert success2 is True

        # Verify columns still exist and are correct
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        assert "filter_reason" in columns
        assert "filtered_at" in columns
        assert "manual_review_flag" in columns
        assert "stale_check_result" in columns

    def test_migration_creates_indexes(self, temp_db):
        """Test that migration creates performance indexes"""
        JobDatabase(db_path=temp_db)

        migration.migrate(db_path=temp_db)

        # Check indexes exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "idx_jobs_filter_reason" in indexes
        assert "idx_jobs_stale_check_result" in indexes
        assert "idx_jobs_manual_review_flag" in indexes

    def test_existing_operations_still_work(self, db_with_existing_jobs):
        """Test that existing database operations work after migration"""
        temp_db, existing_job_ids, _ = db_with_existing_jobs

        # Run migration

        migration.migrate(db_path=temp_db)

        # Test existing operations
        db = JobDatabase(db_path=temp_db)

        # 1. Add new job
        new_job = {
            "title": "Head of Robotics",
            "company": "Automation Co",
            "link": "https://example.com/job3",
            "location": "Remote",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
            "fit_score": 90,
            "fit_grade": "A",
            "score_breakdown": '{"seniority": 30, "domain": 25}',
            "keywords_matched": "[]",
            "source_email": "",
        }

        new_job_id = db.add_job(new_job)
        assert new_job_id is not None

        # 2. Update job score
        db.update_job_score(new_job_id, 92, "A", '{"seniority": 30, "domain": 25, "role_type": 20}')

        # 3. Mark as notified
        db.mark_notified(new_job_id)

        # 4. Get jobs
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3  # 2 existing + 1 new

        # 5. Verify deduplication still works
        duplicate_job = new_job.copy()
        duplicate_id = db.add_job(duplicate_job)
        assert duplicate_id is None  # Should be rejected as duplicate

    def test_new_columns_can_be_populated(self, db_with_existing_jobs):
        """Test that new filter tracking columns can be set and queried"""
        temp_db, job_ids, _ = db_with_existing_jobs

        # Run migration

        migration.migrate(db_path=temp_db)

        # Populate new columns
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Simulate filtering first job
        cursor.execute(
            """
            UPDATE jobs
            SET filter_reason = ?,
                filtered_at = ?,
                manual_review_flag = ?,
                stale_check_result = ?
            WHERE id = ?
        """,
            (
                "hard_filter_hr_role",
                datetime.now().isoformat(),
                0,
                "fresh",
                job_ids[0],
            ),
        )

        # Simulate flagging second job for review
        cursor.execute(
            """
            UPDATE jobs
            SET manual_review_flag = ?,
                stale_check_result = ?
            WHERE id = ?
        """,
            (1, "not_checked", job_ids[1]),
        )

        conn.commit()

        # Query filtered jobs
        cursor.execute(
            "SELECT id, filter_reason, stale_check_result FROM jobs WHERE filter_reason IS NOT NULL"
        )
        filtered_jobs = cursor.fetchall()

        # Query jobs needing review
        cursor.execute("SELECT id FROM jobs WHERE manual_review_flag = 1")
        review_jobs = cursor.fetchall()

        conn.close()

        # Verify
        assert len(filtered_jobs) == 1
        assert filtered_jobs[0][1] == "hard_filter_hr_role"
        assert filtered_jobs[0][2] == "fresh"

        assert len(review_jobs) == 1
        assert review_jobs[0][0] == job_ids[1]

    def test_filter_reason_values(self, temp_db):
        """Test various filter_reason values can be stored"""
        db = JobDatabase(db_path=temp_db)

        migration.migrate(db_path=temp_db)

        # Test all expected filter reasons
        filter_reasons = [
            "hard_filter_junior",
            "hard_filter_intern",
            "hard_filter_coordinator",
            "hard_filter_associate_low_seniority",
            "hard_filter_hr_role",
            "hard_filter_finance_role",
            "hard_filter_legal_role",
            "hard_filter_sales_marketing",
            "hard_filter_administrative",
            "context_filter_software_engineering",
            "context_filter_contract_low_seniority",
            "stale_job_age",
            "stale_no_longer_accepting_applications",
        ]

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        job_ids = []
        for i, reason in enumerate(filter_reasons):
            job = {
                "title": f"Test Job {i}",
                "company": f"Company {i}",
                "link": f"https://example.com/job{i}",
                "location": "Remote",
                "source": "test",
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "keywords_matched": "[]",
                "source_email": "test@example.com",
            }

            job_id = db.add_job(job)
            job_ids.append((job_id, reason))

        # Close conn to avoid database locked issues
        conn.close()

        # Reopen and update
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        for job_id, reason in job_ids:
            cursor.execute(
                "UPDATE jobs SET filter_reason = ?, filtered_at = ? WHERE id = ?",
                (reason, datetime.now().isoformat(), job_id),
            )

        conn.commit()

        # Verify all reasons stored
        cursor.execute("SELECT DISTINCT filter_reason FROM jobs WHERE filter_reason IS NOT NULL")
        stored_reasons = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert stored_reasons == set(filter_reasons)

    def test_stale_check_result_values(self, temp_db):
        """Test stale_check_result can store all expected values"""
        db = JobDatabase(db_path=temp_db)

        migration.migrate(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        test_values = ["not_checked", "fresh", "stale"]

        job_ids = []
        for i, value in enumerate(test_values):
            job = {
                "title": f"Stale Test Job {i}",
                "company": f"Stale Company {i}",
                "link": f"https://example.com/stale{i}",
                "location": "Remote",
                "source": "test",
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "keywords_matched": "[]",
                "source_email": "test@example.com",
            }

            job_id = db.add_job(job)
            job_ids.append((job_id, value))

        # Close conn to avoid database locked issues
        conn.close()

        # Reopen and update
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        for job_id, value in job_ids:
            cursor.execute("UPDATE jobs SET stale_check_result = ? WHERE id = ?", (value, job_id))

        conn.commit()

        # Query each value
        for value in test_values:
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE stale_check_result = ?", (value,))
            count = cursor.fetchone()[0]
            assert count >= 1, f"Expected at least 1 job with stale_check_result='{value}'"

        conn.close()

    def test_query_performance_with_indexes(self, temp_db):
        """Test that index creation improves query performance"""
        db = JobDatabase(db_path=temp_db)

        migration.migrate(db_path=temp_db)

        # Add 100 jobs with various filter reasons
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        job_ids = []
        for i in range(100):
            job = {
                "title": f"Performance Test Job {i}",
                "company": f"Perf Company {i}",
                "link": f"https://example.com/perf{i}",
                "location": "Remote",
                "source": "test",
                "type": "direct_job",
                "received_at": datetime.now().isoformat(),
                "keywords_matched": "[]",
                "source_email": "test@example.com",
            }

            job_id = db.add_job(job)
            # Track jobs that need filter_reason set
            if i % 2 == 0:
                job_ids.append(job_id)

        # Close conn to avoid database locked issues
        conn.close()

        # Reopen and update
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        for job_id in job_ids:
            cursor.execute(
                "UPDATE jobs SET filter_reason = ? WHERE id = ?",
                ("hard_filter_hr_role", job_id),
            )

        conn.commit()

        # Verify index is being used (check EXPLAIN QUERY PLAN)
        cursor.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM jobs WHERE filter_reason = 'hard_filter_hr_role'"
        )
        query_plan = cursor.fetchall()

        conn.close()

        # Query plan should mention the index
        query_plan_str = " ".join([str(row) for row in query_plan])
        assert "idx_jobs_filter_reason" in query_plan_str or "USING INDEX" in query_plan_str
