"""
Tests for multi-profile scoring database methods
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.database import JobDatabase


@pytest.fixture
def db_with_job():
    """Create a database with a test job"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_jobs.db"
        db = JobDatabase(str(db_path))

        # The JobDatabase constructor already creates tables
        # Now add a test job using the db.add_job method or direct SQL
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create job_scores table (normally done by migration)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                profile_id TEXT NOT NULL,
                fit_score INTEGER,
                fit_grade TEXT,
                score_breakdown TEXT,
                classification_metadata TEXT,
                digest_sent_at TEXT,
                notified_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(job_id, profile_id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Insert a test job using the proper schema
        import hashlib
        from datetime import datetime

        now = datetime.now().isoformat()
        job_hash = hashlib.sha256(
            b"Test Company|VP Engineering|https://example.com/job"
        ).hexdigest()

        cursor.execute(
            """
            INSERT INTO jobs (job_hash, title, company, location, link, source, received_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                job_hash,
                "VP Engineering",
                "Test Company",
                "Remote",
                "https://example.com/job",
                "test",
                now,
                now,
                now,
            ),
        )

        conn.commit()
        conn.close()

        yield db, db_path


class TestJobScoresMethods:
    """Test multi-profile scoring database methods"""

    def test_upsert_job_score_insert(self, db_with_job):
        """Test inserting a new job score"""
        db, db_path = db_with_job

        db.upsert_job_score(
            job_id=1, profile_id="wes", score=85, grade="B", breakdown='{"seniority": 30}'
        )

        # Verify it was inserted
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_scores WHERE job_id = 1 AND profile_id = 'wes'")
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[3] == 85  # fit_score
        assert row[4] == "B"  # fit_grade

    def test_upsert_job_score_update(self, db_with_job):
        """Test updating an existing job score"""
        db, db_path = db_with_job

        # Insert initial score
        db.upsert_job_score(job_id=1, profile_id="wes", score=75, grade="C", breakdown="{}")

        # Update score
        db.upsert_job_score(
            job_id=1, profile_id="wes", score=90, grade="A", breakdown='{"updated": true}'
        )

        # Verify it was updated
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fit_score, fit_grade FROM job_scores WHERE job_id = 1 AND profile_id = 'wes'"
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 90
        assert row[1] == "A"

    def test_get_job_score_exists(self, db_with_job):
        """Test getting an existing job score"""
        db, _ = db_with_job

        db.upsert_job_score(
            job_id=1, profile_id="adam", score=70, grade="C", breakdown='{"test": true}'
        )

        result = db.get_job_score(1, "adam")

        assert result is not None
        assert result["fit_score"] == 70
        assert result["fit_grade"] == "C"
        assert result["profile_id"] == "adam"

    def test_get_job_score_not_exists(self, db_with_job):
        """Test getting a non-existent job score"""
        db, _ = db_with_job

        result = db.get_job_score(999, "nonexistent")

        assert result is None

    def test_get_jobs_for_profile_digest(self, db_with_job):
        """Test getting jobs for profile digest"""
        db, _ = db_with_job

        # Add score for the job
        db.upsert_job_score(job_id=1, profile_id="wes", score=85, grade="B", breakdown="{}")

        jobs = db.get_jobs_for_profile_digest("wes", min_grade="C", limit=10)

        assert len(jobs) == 1
        assert jobs[0]["fit_score"] == 85
        assert jobs[0]["fit_grade"] == "B"

    def test_get_jobs_for_profile_digest_filters_by_grade(self, db_with_job):
        """Test that digest respects grade filter"""
        db, db_path = db_with_job

        # Add a low-grade score
        db.upsert_job_score(job_id=1, profile_id="wes", score=30, grade="F", breakdown="{}")

        # Should not return F grade when min_grade is C
        jobs = db.get_jobs_for_profile_digest("wes", min_grade="C", limit=10)

        assert len(jobs) == 0

    def test_get_jobs_for_profile_digest_excludes_sent(self, db_with_job):
        """Test that digest excludes already-sent jobs"""
        db, db_path = db_with_job

        db.upsert_job_score(job_id=1, profile_id="wes", score=85, grade="B", breakdown="{}")

        # Mark as sent
        db.mark_profile_digest_sent([1], "wes")

        # Should not return sent jobs
        jobs = db.get_jobs_for_profile_digest("wes", min_grade="C", limit=10)

        assert len(jobs) == 0

    def test_mark_profile_digest_sent(self, db_with_job):
        """Test marking jobs as sent for digest"""
        db, db_path = db_with_job

        db.upsert_job_score(job_id=1, profile_id="wes", score=85, grade="B", breakdown="{}")

        db.mark_profile_digest_sent([1], "wes")

        # Verify it was marked
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT digest_sent_at FROM job_scores WHERE job_id = 1 AND profile_id = 'wes'"
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] is not None

    def test_get_profile_stats(self, db_with_job):
        """Test getting profile statistics"""
        db, _ = db_with_job

        # Add scores with different grades
        db.upsert_job_score(job_id=1, profile_id="wes", score=95, grade="A", breakdown="{}")

        stats = db.get_profile_stats("wes")

        assert stats["profile_id"] == "wes"
        assert stats["total_scored"] == 1
        assert stats["by_grade"].get("A", 0) == 1
        assert stats["unsent_digest"] == 1

    def test_get_profile_stats_empty(self, db_with_job):
        """Test getting stats for profile with no scores"""
        db, _ = db_with_job

        stats = db.get_profile_stats("empty_profile")

        assert stats["total_scored"] == 0
        assert stats["unsent_digest"] == 0

    def test_get_jobs_for_profile_digest_location_filtering(self, db_with_job):
        """Test location score filtering in digest query"""
        db, db_path = db_with_job

        # Add job with high location score (remote = 15 points)
        db.upsert_job_score(
            job_id=1,
            profile_id="wes",
            score=85,
            grade="B",
            breakdown='{"location": 15, "seniority": 30, "role_type": 20}',
        )

        # Add another job with location score 0 (on-site outside target area)
        # First add the job to jobs table
        import hashlib
        from datetime import datetime

        now = datetime.now().isoformat()
        job_hash = hashlib.sha256(b"Company 2|Job 2|http://example.com/2").hexdigest()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (job_hash, title, company, location, link, source, received_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                job_hash,
                "Job 2",
                "Company 2",
                "Austin, TX",
                "http://example.com/2",
                "test",
                now,
                now,
                now,
            ),
        )
        job_id_2 = cursor.lastrowid
        conn.commit()
        conn.close()

        db.upsert_job_score(
            job_id=job_id_2,
            profile_id="wes",
            score=70,
            grade="C",
            breakdown='{"location": 0, "seniority": 30, "role_type": 20}',
        )

        # Without location filtering - should return both jobs
        jobs_no_filter = db.get_jobs_for_profile_digest(
            "wes", min_grade="C", min_location_score=0, limit=10
        )
        assert len(jobs_no_filter) == 2

        # With location filtering (min_location_score=8) - should return only first job
        jobs_filtered = db.get_jobs_for_profile_digest(
            "wes", min_grade="C", min_location_score=8, limit=10
        )
        assert len(jobs_filtered) == 1
        assert jobs_filtered[0]["id"] == 1  # Only the remote job
