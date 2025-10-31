"""
Database module for job storage and deduplication
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path


class JobDatabase:
    """Manages SQLite database for job listings"""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Create database schema if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                link TEXT NOT NULL,
                description TEXT,
                salary TEXT,
                job_type TEXT,
                posted_date TEXT,
                source TEXT,
                source_email TEXT,
                received_at TEXT NOT NULL,
                notified_at TEXT,
                digest_sent_at TEXT,
                keywords_matched TEXT,
                raw_email_content TEXT,
                fit_score INTEGER,
                fit_grade TEXT,
                score_breakdown TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_hash ON jobs(job_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_received_at ON jobs(received_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)
        """)

        # Migration: Add scoring columns if they don't exist
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]

        if "fit_score" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN fit_score INTEGER")

        if "fit_grade" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN fit_grade TEXT")

        if "score_breakdown" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN score_breakdown TEXT")

        if "digest_sent_at" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN digest_sent_at TEXT")

        # Create index after column exists
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fit_score ON jobs(fit_score)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest_sent_at ON jobs(digest_sent_at)
        """)

        conn.commit()
        conn.close()

    def generate_job_hash(self, title: str, company: str, link: str) -> str:
        """Generate unique hash for job deduplication"""
        # Normalize and combine key fields
        normalized = f"{title.lower().strip()}|{company.lower().strip()}|{link.strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def job_exists(self, job_hash: str) -> bool:
        """Check if job already exists in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE job_hash = ?", (job_hash,))
        count = cursor.fetchone()[0]

        conn.close()
        return count > 0

    def add_job(self, job_data: dict) -> int | None:
        """
        Add job to database if it doesn't already exist

        Args:
            job_data: Dictionary containing job details

        Returns:
            Job ID if added, None if duplicate
        """
        job_hash = self.generate_job_hash(job_data["title"], job_data["company"], job_data["link"])

        if self.job_exists(job_hash):
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO jobs (
                job_hash, title, company, location, link, description,
                salary, job_type, posted_date, source, source_email,
                received_at, keywords_matched, raw_email_content,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                job_hash,
                job_data.get("title", ""),
                job_data.get("company", ""),
                job_data.get("location", ""),
                job_data.get("link", ""),
                job_data.get("description", ""),
                job_data.get("salary", ""),
                job_data.get("job_type", ""),
                job_data.get("posted_date", ""),
                job_data.get("source", ""),
                job_data.get("source_email", ""),
                job_data.get("received_at", now),
                json.dumps(job_data.get("keywords_matched", [])),
                job_data.get("raw_email_content", ""),
                now,
                now,
            ),
        )

        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return job_id

    def mark_notified(self, job_id: int):
        """Mark job as notified"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE jobs
            SET notified_at = ?, updated_at = ?
            WHERE id = ?
        """,
            (now, now, job_id),
        )

        conn.commit()
        conn.close()

    def mark_digest_sent(self, job_ids: list[int]):
        """Mark jobs as included in digest"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        for job_id in job_ids:
            cursor.execute(
                """
                UPDATE jobs
                SET digest_sent_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (now, now, job_id),
            )

        conn.commit()
        conn.close()

    def update_job_score(self, job_id: int, score: int, grade: str, breakdown: str):
        """Update job with fit score and grade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE jobs
            SET fit_score = ?, fit_grade = ?, score_breakdown = ?, updated_at = ?
            WHERE id = ?
        """,
            (score, grade, breakdown, now, job_id),
        )

        conn.commit()
        conn.close()

    def get_recent_jobs(self, limit: int = 10) -> list[dict]:
        """Get most recent jobs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM jobs
            ORDER BY received_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jobs

    def get_jobs_for_digest(self, limit: int = 100) -> list[dict]:
        """Get jobs that haven't been sent in digest yet"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM jobs
            WHERE digest_sent_at IS NULL
            ORDER BY fit_score DESC, received_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jobs

    def get_unnotified_jobs(self) -> list[dict]:
        """Get jobs that haven't been notified yet"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM jobs
            WHERE notified_at IS NULL
            ORDER BY received_at DESC
        """)

        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jobs

    def get_stats(self) -> dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE notified_at IS NOT NULL")
        notified_jobs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM jobs
            GROUP BY source
        """)
        jobs_by_source = dict(cursor.fetchall())

        conn.close()

        return {
            "total_jobs": total_jobs,
            "notified_jobs": notified_jobs,
            "unnotified_jobs": total_jobs - notified_jobs,
            "jobs_by_source": jobs_by_source,
        }


if __name__ == "__main__":
    # Test the database
    db = JobDatabase()
    print("Database initialized successfully")
    print("Stats:", db.get_stats())
