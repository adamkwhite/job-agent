"""
Database module for job storage and deduplication
"""

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class JobDatabase:
    """Manages SQLite database for job listings"""

    def __init__(self, db_path: str = "data/jobs.db", profile: str | None = None):
        self.db_path = Path(db_path)
        self.profile = profile
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

        if "profile" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN profile TEXT")
            # Set default profile for existing jobs (assume they're for Wes)
            cursor.execute("UPDATE jobs SET profile = 'wes' WHERE profile IS NULL")

        # Create index after column exists
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fit_score ON jobs(fit_score)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_digest_sent_at ON jobs(digest_sent_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_profile ON jobs(profile)
        """)

        conn.commit()
        conn.close()

    def generate_job_hash(self, title: str, company: str, link: str) -> str:
        """Generate unique hash for job deduplication"""
        # Normalize link - extract job ID for LinkedIn URLs to ignore tracking parameters
        normalized_link = link.strip()
        link_lower = link.lower()
        if "linkedin.com" in link_lower and "/jobs/view/" in link_lower:
            # Extract job ID from LinkedIn URL (e.g., /jobs/view/4318329363)
            match = re.search(r"/jobs/view/(\d+)", link, re.IGNORECASE)
            if match:
                # Use normalized form: just the job ID
                normalized_link = f"linkedin.com/jobs/view/{match.group(1)}"

        # Normalize and combine key fields
        normalized = f"{title.lower().strip()}|{company.lower().strip()}|{normalized_link.lower()}"
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
                profile, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                self.profile,
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

    def get_all_jobs(self) -> list[dict]:
        """Get all jobs from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM jobs ORDER BY received_at DESC")

        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jobs

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

    # ===== Multi-Person Scoring Methods =====

    def upsert_job_score(
        self, job_id: int, profile_id: str, score: int, grade: str, breakdown: str
    ):
        """Insert or update score for a specific job and profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO job_scores (
                job_id, profile_id, fit_score, fit_grade, score_breakdown,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, profile_id) DO UPDATE SET
                fit_score = excluded.fit_score,
                fit_grade = excluded.fit_grade,
                score_breakdown = excluded.score_breakdown,
                updated_at = excluded.updated_at
        """,
            (job_id, profile_id, score, grade, breakdown, now, now),
        )

        conn.commit()
        conn.close()

    def get_job_score(self, job_id: int, profile_id: str) -> dict | None:
        """Get score for a specific job and profile"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM job_scores
            WHERE job_id = ? AND profile_id = ?
        """,
            (job_id, profile_id),
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_jobs_for_profile_digest(
        self, profile_id: str, min_grade: str = "C", limit: int = 100, max_age_days: int = 7
    ) -> list[dict]:
        """Get jobs for digest that haven't been sent to this profile

        Args:
            profile_id: Profile to get jobs for
            min_grade: Minimum grade to include (A, B, C, D, F)
            limit: Max jobs to return
            max_age_days: Only include jobs from last N days (default 7, reduced from 14 to improve quality)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Map grades to numeric for comparison
        grade_order = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}
        min_grade_num = grade_order.get(min_grade, 3)

        cursor.execute(
            """
            SELECT j.id, j.job_hash, j.title, j.company, j.location, j.link,
                   j.description, j.salary, j.job_type, j.posted_date, j.source,
                   j.source_email, j.received_at, j.notified_at, j.keywords_matched,
                   j.created_at, j.updated_at,
                   js.fit_score, js.fit_grade, js.score_breakdown,
                   js.digest_sent_at as profile_digest_sent_at
            FROM jobs j
            JOIN job_scores js ON j.id = js.job_id
            WHERE js.profile_id = ?
              AND js.digest_sent_at IS NULL
              AND j.received_at >= datetime('now', '-' || ? || ' days')
              AND (
                  (js.fit_grade = 'A' AND ? >= 1) OR
                  (js.fit_grade = 'B' AND ? >= 2) OR
                  (js.fit_grade = 'C' AND ? >= 3) OR
                  (js.fit_grade = 'D' AND ? >= 4) OR
                  (js.fit_grade = 'F' AND ? >= 5)
              )
            ORDER BY js.fit_score DESC, j.received_at DESC
            LIMIT ?
        """,
            (
                profile_id,
                max_age_days,
                min_grade_num,
                min_grade_num,
                min_grade_num,
                min_grade_num,
                min_grade_num,
                limit,
            ),
        )

        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs

    def mark_profile_digest_sent(self, job_ids: list[int], profile_id: str):
        """Mark jobs as sent in digest for a specific profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        for job_id in job_ids:
            cursor.execute(
                """
                UPDATE job_scores
                SET digest_sent_at = ?, updated_at = ?
                WHERE job_id = ? AND profile_id = ?
            """,
                (now, now, job_id, profile_id),
            )

        conn.commit()
        conn.close()

    def get_profile_stats(self, profile_id: str) -> dict:
        """Get statistics for a specific profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM job_scores WHERE profile_id = ?
        """,
            (profile_id,),
        )
        total_scored = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT fit_grade, COUNT(*) as count
            FROM job_scores
            WHERE profile_id = ?
            GROUP BY fit_grade
        """,
            (profile_id,),
        )
        by_grade = dict(cursor.fetchall())

        cursor.execute(
            """
            SELECT COUNT(*) FROM job_scores
            WHERE profile_id = ? AND digest_sent_at IS NULL
        """,
            (profile_id,),
        )
        unsent = cursor.fetchone()[0]

        conn.close()

        return {
            "profile_id": profile_id,
            "total_scored": total_scored,
            "by_grade": by_grade,
            "unsent_digest": unsent,
        }


if __name__ == "__main__":
    # Test the database
    db = JobDatabase()
    print("Database initialized successfully")
    print("Stats:", db.get_stats())
