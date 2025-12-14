"""Test multi-profile scoring for duplicate jobs"""

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from database import JobDatabase


class TestMultiProfileDuplicateScoring:
    """Test that duplicate jobs get scored for all profiles"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Initialize database schema (creates jobs table)
        JobDatabase(profile="wes", db_path=db_path)

        # Create job_scores table (normally created by migration)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                UNIQUE(job_id, profile_id)
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_duplicate_job_scored_for_second_profile(self, temp_db, mocker):
        """Test that when a job is a duplicate, it still gets scored for the current profile"""
        # Setup: Create a job as Wes
        wes_db = JobDatabase(profile="wes", db_path=temp_db)

        job_dict = {
            "title": "VP of Engineering",
            "company": "TestRobotics",
            "location": "Remote",
            "link": "https://test.com/jobs/123",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        # Wes adds the job
        wes_job_id = wes_db.add_job(job_dict)
        assert wes_job_id is not None, "Job should be added for Wes"

        # Wes scores the job
        wes_db.upsert_job_score(
            job_id=wes_job_id,
            profile_id="wes",
            score=85,
            grade="B+",
            breakdown=json.dumps({"seniority": 25, "domain": 20}),
        )

        # Verify Wes has a score
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'wes'")
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should have 1 score"
        conn.close()

        # Now Mario runs and encounters the same job (duplicate)
        mario_db = JobDatabase(profile="mario", db_path=temp_db)

        # When Mario tries to add the same job, it should return None (duplicate)
        mario_job_id = mario_db.add_job(job_dict)
        assert mario_job_id is None, "Job should be detected as duplicate for Mario"

        # But Mario should still be able to score it using get_job_id_by_hash
        job_hash = mario_db.generate_job_hash(
            job_dict["title"], job_dict["company"], job_dict["link"]
        )
        existing_job_id = mario_db.get_job_id_by_hash(job_hash)
        assert existing_job_id == wes_job_id, "Should find the existing job by hash"

        # Mario scores the duplicate job
        mario_db.upsert_job_score(
            job_id=existing_job_id,
            profile_id="mario",
            score=75,
            grade="C+",
            breakdown=json.dumps({"seniority": 20, "domain": 15}),
        )

        # Verify both Wes and Mario have scores for the same job
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'wes'")
        wes_count = cursor.fetchone()[0]
        assert wes_count == 1, "Wes should still have 1 score"

        cursor.execute("SELECT COUNT(*) FROM job_scores WHERE profile_id = 'mario'")
        mario_count = cursor.fetchone()[0]
        assert mario_count == 1, "Mario should now have 1 score"

        cursor.execute("SELECT COUNT(DISTINCT job_id) FROM job_scores")
        unique_jobs = cursor.fetchone()[0]
        assert unique_jobs == 1, "Should be 1 unique job with 2 scores"

        cursor.execute("SELECT COUNT(*) FROM job_scores")
        total_scores = cursor.fetchone()[0]
        assert total_scores == 2, "Should have 2 total scores (Wes + Mario)"

        conn.close()

    def test_get_job_id_by_hash_returns_none_for_nonexistent(self, temp_db):
        """Test that get_job_id_by_hash returns None for non-existent jobs"""
        db = JobDatabase(profile="wes", db_path=temp_db)

        # Generate hash for a job that doesn't exist
        job_hash = db.generate_job_hash(
            "Nonexistent Job", "Nonexistent Company", "https://fake.com/job"
        )

        job_id = db.get_job_id_by_hash(job_hash)
        assert job_id is None, "Should return None for non-existent job"

    def test_get_job_id_by_hash_finds_existing_job(self, temp_db):
        """Test that get_job_id_by_hash finds existing jobs by hash"""
        db = JobDatabase(profile="wes", db_path=temp_db)

        # Add a job
        job_dict = {
            "title": "Director of Product",
            "company": "RoboCorp",
            "location": "Toronto, ON",
            "link": "https://robocorp.com/careers/123",
            "source": "company_monitoring",
            "type": "direct_job",
            "received_at": datetime.now().isoformat(),
        }

        job_id = db.add_job(job_dict)
        assert job_id is not None, "Job should be added"

        # Find it by hash
        job_hash = db.generate_job_hash(job_dict["title"], job_dict["company"], job_dict["link"])
        found_id = db.get_job_id_by_hash(job_hash)

        assert found_id == job_id, "Should find the job by hash"
