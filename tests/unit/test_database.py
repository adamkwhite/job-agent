"""
Tests for JobDatabase

Tests SQLite database operations for job storage and deduplication:
- Database initialization and schema creation
- Job hash generation and deduplication
- Job insertion and retrieval
- Scoring updates
- Digest tracking
- Statistics
"""

import json
import sqlite3
import tempfile
from pathlib import Path

from src.database import JobDatabase


class TestJobDatabaseInit:
    """Test JobDatabase initialization"""

    def test_init_creates_database(self):
        """Test database file is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _ = JobDatabase(str(db_path))

            assert db_path.exists()

    def test_init_creates_parent_directory(self):
        """Test parent directory is created if missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "nested" / "dir" / "test.db"
            _ = JobDatabase(str(db_path))

            assert db_path.parent.exists()
            assert db_path.exists()

    def test_init_creates_schema(self):
        """Test database schema is created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _ = JobDatabase(str(db_path))

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
            assert cursor.fetchone() is not None

            # Check columns exist
            cursor.execute("PRAGMA table_info(jobs)")
            columns = {col[1] for col in cursor.fetchall()}

            required_columns = {
                "id",
                "job_hash",
                "title",
                "company",
                "location",
                "link",
                "fit_score",
                "fit_grade",
                "score_breakdown",
                "digest_sent_at",
            }

            assert required_columns.issubset(columns)

            conn.close()

    def test_init_creates_indexes(self):
        """Test indexes are created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _ = JobDatabase(str(db_path))

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}

            expected_indexes = {
                "idx_job_hash",
                "idx_received_at",
                "idx_company",
                "idx_fit_score",
                "idx_digest_sent_at",
            }

            assert expected_indexes.issubset(indexes)

            conn.close()


class TestJobHashGeneration:
    """Test job hash generation for deduplication"""

    def test_generate_job_hash_consistent(self):
        """Test same inputs produce same hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")

            assert hash1 == hash2

    def test_generate_job_hash_case_insensitive(self):
        """Test hash is case-insensitive"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash("software engineer", "google", "https://job.com/123")

            assert hash1 == hash2

    def test_generate_job_hash_strips_whitespace(self):
        """Test hash strips leading/trailing whitespace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash(
                "  Software Engineer  ", "  Google  ", "  https://job.com/123  "
            )

            assert hash1 == hash2

    def test_generate_job_hash_different_titles(self):
        """Test different titles produce different hashes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash("Senior Engineer", "Google", "https://job.com/123")

            assert hash1 != hash2

    def test_generate_job_hash_different_companies(self):
        """Test different companies produce different hashes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash("Software Engineer", "Facebook", "https://job.com/123")

            assert hash1 != hash2

    def test_generate_job_hash_different_links(self):
        """Test different links produce different hashes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            hash1 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/123")
            hash2 = db.generate_job_hash("Software Engineer", "Google", "https://job.com/456")

            assert hash1 != hash2


class TestJobExists:
    """Test job existence checking"""

    def test_job_exists_returns_false_for_new_hash(self):
        """Test job_exists returns False for new hash"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_hash = db.generate_job_hash("New Job", "Company", "https://link.com")
            assert not db.job_exists(job_hash)

    def test_job_exists_returns_true_for_existing_job(self):
        """Test job_exists returns True after job is added"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            db.add_job(job_data)

            job_hash = db.generate_job_hash(
                job_data["title"], job_data["company"], job_data["link"]
            )
            assert db.job_exists(job_hash)


class TestAddJob:
    """Test adding jobs to database"""

    def test_add_job_returns_job_id(self):
        """Test add_job returns job ID on success"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            job_id = db.add_job(job_data)

            assert job_id is not None
            assert isinstance(job_id, int)
            assert job_id > 0

    def test_add_job_returns_none_for_duplicate(self):
        """Test add_job returns None for duplicate job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            job_id1 = db.add_job(job_data)
            job_id2 = db.add_job(job_data)

            assert job_id1 is not None
            assert job_id2 is None

    def test_add_job_stores_all_fields(self):
        """Test add_job stores all provided fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "location": "Remote",
                "link": "https://job.com/123",
                "description": "Great job",
                "salary": "$100k-150k",
                "job_type": "Full-time",
                "posted_date": "2025-01-01",
                "source": "linkedin",
                "source_email": "jobs@linkedin.com",
                "keywords_matched": ["python", "engineering"],
                "raw_email_content": "Email body here",
            }

            job_id = db.add_job(job_data)

            # Retrieve and verify
            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = dict(cursor.fetchone())

            assert row["title"] == "Software Engineer"
            assert row["company"] == "Google"
            assert row["location"] == "Remote"
            assert row["link"] == "https://job.com/123"
            assert row["description"] == "Great job"
            assert row["salary"] == "$100k-150k"
            assert row["source"] == "linkedin"

            keywords = json.loads(row["keywords_matched"])
            assert keywords == ["python", "engineering"]

            conn.close()

    def test_add_job_sets_timestamps(self):
        """Test add_job sets created_at and updated_at"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            job_id = db.add_job(job_data)

            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT created_at, updated_at FROM jobs WHERE id = ?", (job_id,))
            row = dict(cursor.fetchone())

            assert row["created_at"] != ""
            assert row["updated_at"] != ""

            conn.close()


class TestMarkNotified:
    """Test marking jobs as notified"""

    def test_mark_notified_sets_timestamp(self):
        """Test mark_notified sets notified_at timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            job_id = db.add_job(job_data)
            db.mark_notified(job_id)

            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT notified_at FROM jobs WHERE id = ?", (job_id,))
            row = dict(cursor.fetchone())

            assert row["notified_at"] is not None
            assert row["notified_at"] != ""

            conn.close()


class TestMarkDigestSent:
    """Test marking jobs as sent in digest"""

    def test_mark_digest_sent_sets_timestamp(self):
        """Test mark_digest_sent sets digest_sent_at timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
            }

            job_id1 = db.add_job(job_data1)
            job_id2 = db.add_job(job_data2)

            db.mark_digest_sent([job_id1, job_id2])

            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT digest_sent_at FROM jobs WHERE id IN (?, ?)", (job_id1, job_id2))
            rows = [dict(row) for row in cursor.fetchall()]

            assert all(row["digest_sent_at"] is not None for row in rows)
            assert all(row["digest_sent_at"] != "" for row in rows)

            conn.close()


class TestUpdateJobScore:
    """Test updating job scores"""

    def test_update_job_score_sets_fields(self):
        """Test update_job_score sets score, grade, and breakdown"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "VP Engineering",
                "company": "Robotics Co",
                "link": "https://job.com/123",
            }

            job_id = db.add_job(job_data)

            breakdown = json.dumps(
                {
                    "seniority": 30,
                    "domain": 25,
                    "role_type": 20,
                    "location": 15,
                    "company_stage": 10,
                    "technical": 5,
                }
            )

            db.update_job_score(job_id, 105, "A", breakdown)

            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT fit_score, fit_grade, score_breakdown FROM jobs WHERE id = ?", (job_id,)
            )
            row = dict(cursor.fetchone())

            assert row["fit_score"] == 105
            assert row["fit_grade"] == "A"
            assert row["score_breakdown"] == breakdown

            conn.close()


class TestGetRecentJobs:
    """Test retrieving recent jobs"""

    def test_get_recent_jobs_returns_list(self):
        """Test get_recent_jobs returns list of dicts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data = {
                "title": "Software Engineer",
                "company": "Google",
                "link": "https://job.com/123",
            }

            db.add_job(job_data)

            jobs = db.get_recent_jobs()

            assert isinstance(jobs, list)
            assert len(jobs) == 1
            assert isinstance(jobs[0], dict)

    def test_get_recent_jobs_respects_limit(self):
        """Test get_recent_jobs respects limit parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            for i in range(5):
                job_data = {
                    "title": f"Job {i}",
                    "company": "Company",
                    "link": f"https://job.com/{i}",
                }
                db.add_job(job_data)

            jobs = db.get_recent_jobs(limit=3)

            assert len(jobs) == 3

    def test_get_recent_jobs_orders_by_received_at(self):
        """Test get_recent_jobs orders by received_at DESC"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            for i in range(3):
                job_data = {
                    "title": f"Job {i}",
                    "company": "Company",
                    "link": f"https://job.com/{i}",
                }
                db.add_job(job_data)

            jobs = db.get_recent_jobs()

            # Most recent first (Job 2, Job 1, Job 0)
            assert jobs[0]["title"] == "Job 2"
            assert jobs[1]["title"] == "Job 1"
            assert jobs[2]["title"] == "Job 0"


class TestGetJobsForDigest:
    """Test retrieving jobs for digest"""

    def test_get_jobs_for_digest_excludes_sent(self):
        """Test get_jobs_for_digest excludes jobs with digest_sent_at"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
            }

            job_id1 = db.add_job(job_data1)
            _ = db.add_job(job_data2)

            db.mark_digest_sent([job_id1])

            jobs = db.get_jobs_for_digest()

            assert len(jobs) == 1
            assert jobs[0]["title"] == "Job 2"

    def test_get_jobs_for_digest_orders_by_score(self):
        """Test get_jobs_for_digest orders by fit_score DESC"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
            }

            job_id1 = db.add_job(job_data1)
            job_id2 = db.add_job(job_data2)

            db.update_job_score(job_id1, 75, "C", "{}")
            db.update_job_score(job_id2, 95, "A", "{}")

            jobs = db.get_jobs_for_digest()

            # Higher score first
            assert jobs[0]["title"] == "Job 2"
            assert jobs[1]["title"] == "Job 1"


class TestGetUnnotifiedJobs:
    """Test retrieving unnotified jobs"""

    def test_get_unnotified_jobs_excludes_notified(self):
        """Test get_unnotified_jobs excludes jobs with notified_at"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
            }

            job_id1 = db.add_job(job_data1)
            _ = db.add_job(job_data2)

            db.mark_notified(job_id1)

            jobs = db.get_unnotified_jobs()

            assert len(jobs) == 1
            assert jobs[0]["title"] == "Job 2"


class TestGetStats:
    """Test database statistics"""

    def test_get_stats_returns_dict(self):
        """Test get_stats returns dict with correct keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            stats = db.get_stats()

            assert isinstance(stats, dict)
            assert "total_jobs" in stats
            assert "notified_jobs" in stats
            assert "unnotified_jobs" in stats
            assert "jobs_by_source" in stats

    def test_get_stats_counts_jobs(self):
        """Test get_stats counts total jobs correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            for i in range(3):
                job_data = {
                    "title": f"Job {i}",
                    "company": "Company",
                    "link": f"https://job.com/{i}",
                }
                db.add_job(job_data)

            stats = db.get_stats()

            assert stats["total_jobs"] == 3

    def test_get_stats_counts_notified(self):
        """Test get_stats counts notified jobs correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
            }

            job_id1 = db.add_job(job_data1)
            db.add_job(job_data2)

            db.mark_notified(job_id1)

            stats = db.get_stats()

            assert stats["notified_jobs"] == 1
            assert stats["unnotified_jobs"] == 1

    def test_get_stats_groups_by_source(self):
        """Test get_stats groups jobs by source"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = JobDatabase(str(Path(tmpdir) / "test.db"))

            job_data1 = {
                "title": "Job 1",
                "company": "Company A",
                "link": "https://job.com/1",
                "source": "linkedin",
            }
            job_data2 = {
                "title": "Job 2",
                "company": "Company B",
                "link": "https://job.com/2",
                "source": "linkedin",
            }
            job_data3 = {
                "title": "Job 3",
                "company": "Company C",
                "link": "https://job.com/3",
                "source": "supra",
            }

            db.add_job(job_data1)
            db.add_job(job_data2)
            db.add_job(job_data3)

            stats = db.get_stats()

            assert stats["jobs_by_source"]["linkedin"] == 2
            assert stats["jobs_by_source"]["supra"] == 1
