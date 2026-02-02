"""
Database module for job storage and deduplication
"""

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class JobDatabase:
    """Manages SQLite database for job listings"""

    def __init__(self, db_path: str | None = None, profile: str | None = None):
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "data/jobs.db")

        # CRITICAL: Prevent production database usage during tests
        import sys

        if "pytest" in sys.modules and "data/jobs.db" in db_path:
            raise RuntimeError(
                f"❌ BLOCKED: Attempted to use production database during tests!\n"
                f"db_path={db_path}\n"
                f"DATABASE_PATH environment variable must be set to a test path.\n"
                f"This is a safety check to prevent test data pollution."
            )

        self.db_path = Path(db_path)
        self.profile = profile
        # Only create parent directory if not the production data/ directory during tests
        if "pytest" in sys.modules and str(self.db_path.parent).endswith("data"):
            raise RuntimeError(
                f"❌ BLOCKED: Attempted to create data/ directory during tests!\n"
                f"db_path={self.db_path}\n"
                f"parent={self.db_path.parent}"
            )
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

        # Migration: Add LLM extraction tracking columns
        if "extraction_method" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN extraction_method TEXT")

        if "extraction_cost" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN extraction_cost REAL")

        # Migration: Add URL validation tracking columns
        if "url_status" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN url_status TEXT")

        if "url_checked_at" not in columns:
            cursor.execute("ALTER TABLE jobs ADD COLUMN url_checked_at TEXT")

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

        # Create LLM extraction failures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_extraction_failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                careers_url TEXT,
                markdown_path TEXT,
                failure_reason TEXT,
                error_details TEXT,
                occurred_at TEXT NOT NULL,
                reviewed_at TEXT,
                review_action TEXT,
                UNIQUE(company_name, occurred_at)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_failures_company ON llm_extraction_failures(company_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_failures_reviewed ON llm_extraction_failures(review_action)
        """)

        # Create extraction metrics comparison table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extraction_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                scrape_date TEXT NOT NULL,
                regex_jobs_found INTEGER,
                regex_leadership_jobs INTEGER,
                regex_with_location INTEGER,
                llm_jobs_found INTEGER,
                llm_leadership_jobs INTEGER,
                llm_with_location INTEGER,
                llm_api_cost REAL,
                overlap_count INTEGER,
                regex_unique INTEGER,
                llm_unique INTEGER,
                UNIQUE(company_name, scrape_date)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_metrics_company ON extraction_metrics(company_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_metrics_date ON extraction_metrics(scrape_date)
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

    def get_job_id_by_hash(self, job_hash: str) -> int | None:
        """
        Get job ID by hash (for scoring duplicates across profiles)

        Args:
            job_hash: Hash of the job

        Returns:
            Job ID if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM jobs WHERE job_hash = ?", (job_hash,))
        result = cursor.fetchone()

        conn.close()
        return result[0] if result else None

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

    def mark_job_filtered(self, job_id: int, filter_reason: str):
        """Mark job as filtered with reason"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE jobs
            SET filter_reason = ?, filtered_at = ?, updated_at = ?
            WHERE id = ?
        """,
            (filter_reason, now, now, job_id),
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

    def update_url_validation(self, job_hash: str, url_status: str):
        """Update URL validation status for a job

        Args:
            job_hash: Job hash identifier
            url_status: Status from validation (valid, stale_*, 404_not_found, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE jobs
            SET url_status = ?, url_checked_at = ?, updated_at = ?
            WHERE job_hash = ?
        """,
            (url_status, now, now, job_hash),
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
        self,
        job_id: int,
        profile_id: str,
        score: int,
        grade: str,
        breakdown: str,
        classification_metadata: str | None = None,
    ):
        """Insert or update score for a specific job and profile

        Args:
            job_id: Job ID to score
            profile_id: Profile ID to score for
            score: Fit score (0-115+)
            grade: Fit grade (A/B/C/D/F)
            breakdown: JSON string of score breakdown by category
            classification_metadata: Optional JSON string of company classification data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO job_scores (
                job_id, profile_id, fit_score, fit_grade, score_breakdown,
                classification_metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, profile_id) DO UPDATE SET
                fit_score = excluded.fit_score,
                fit_grade = excluded.fit_grade,
                score_breakdown = excluded.score_breakdown,
                classification_metadata = excluded.classification_metadata,
                updated_at = excluded.updated_at
        """,
            (job_id, profile_id, score, grade, breakdown, classification_metadata, now, now),
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
        self,
        profile_id: str,
        min_grade: str = "C",
        min_location_score: int = 0,
        limit: int = 100,
        max_age_days: int = 7,
    ) -> list[dict]:
        """Get jobs for digest that haven't been sent to this profile

        Args:
            profile_id: Profile to get jobs for
            min_grade: Minimum grade to include (A, B, C, D, F)
            min_location_score: Minimum location score (0-15, default 0 = no filtering)
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
              AND (j.url_status IS NULL OR j.url_status = 'valid' OR j.url_status = 'linkedin' OR j.url_status = 'generic_page' OR j.url_status = 'rate_limited')
              AND (
                  (js.fit_grade = 'A' AND ? >= 1) OR
                  (js.fit_grade = 'B' AND ? >= 2) OR
                  (js.fit_grade = 'C' AND ? >= 3) OR
                  (js.fit_grade = 'D' AND ? >= 4) OR
                  (js.fit_grade = 'F' AND ? >= 5)
              )
              AND COALESCE(CAST(json_extract(js.score_breakdown, '$.location') AS INTEGER), 0) >= ?
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
                min_location_score,
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

    def store_llm_failure(
        self,
        company_name: str,
        careers_url: str | None = None,
        markdown_path: str | None = None,
        failure_reason: str | None = None,
        error_details: str | None = None,
    ) -> int:
        """Store LLM extraction failure for later review

        Args:
            company_name: Name of the company
            careers_url: URL of the careers page
            markdown_path: Path to cached markdown file
            failure_reason: Short description of failure
            error_details: Full error message/stack trace

        Returns:
            ID of the failure record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        occurred_at = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO llm_extraction_failures
            (company_name, careers_url, markdown_path, failure_reason, error_details, occurred_at, review_action)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """,
            (company_name, careers_url, markdown_path, failure_reason, error_details, occurred_at),
        )

        failure_id = cursor.lastrowid
        conn.commit()
        conn.close()

        if failure_id is None:
            raise RuntimeError("Failed to insert LLM failure record")
        return failure_id

    def get_llm_failures(self, review_action: str | None = None, limit: int = 100) -> list[dict]:
        """Get LLM extraction failures for review

        Args:
            review_action: Filter by review action ('pending', 'retry', 'skip')
            limit: Maximum number of failures to return

        Returns:
            List of failure dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if review_action:
            cursor.execute(
                """
                SELECT * FROM llm_extraction_failures
                WHERE review_action = ?
                ORDER BY occurred_at DESC
                LIMIT ?
            """,
                (review_action, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM llm_extraction_failures
                ORDER BY occurred_at DESC
                LIMIT ?
            """,
                (limit,),
            )

        failures = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return failures

    def update_llm_failure(self, failure_id: int, review_action: str) -> bool:
        """Update review action for an LLM extraction failure

        Args:
            failure_id: ID of the failure record to update
            review_action: Action taken ('retry', 'skip', 'pending')

        Returns:
            True if update successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE llm_extraction_failures
                SET review_action = ?,
                    reviewed_at = datetime('now')
                WHERE id = ?
            """,
                (review_action, failure_id),
            )

            conn.commit()
            rows_updated = cursor.rowcount
            conn.close()

            return rows_updated > 0
        except Exception as e:
            print(f"Error updating LLM failure: {e}")
            return False

    def store_extraction_metrics(
        self,
        company_name: str,
        regex_jobs_found: int,
        regex_leadership_jobs: int,
        regex_with_location: int,
        llm_jobs_found: int,
        llm_leadership_jobs: int,
        llm_with_location: int,
        llm_api_cost: float,
        overlap_count: int,
        regex_unique: int,
        llm_unique: int,
    ) -> int:
        """Store extraction comparison metrics

        Args:
            company_name: Name of the company
            regex_jobs_found: Total jobs found by regex
            regex_leadership_jobs: Leadership jobs found by regex
            regex_with_location: Regex jobs with valid location
            llm_jobs_found: Total jobs found by LLM
            llm_leadership_jobs: Leadership jobs found by LLM
            llm_with_location: LLM jobs with valid location
            llm_api_cost: Cost of LLM API call in USD
            overlap_count: Jobs found by both methods
            regex_unique: Jobs only found by regex
            llm_unique: Jobs only found by LLM

        Returns:
            ID of the metrics record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        scrape_date = datetime.now().date().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO extraction_metrics
            (company_name, scrape_date, regex_jobs_found, regex_leadership_jobs, regex_with_location,
             llm_jobs_found, llm_leadership_jobs, llm_with_location, llm_api_cost,
             overlap_count, regex_unique, llm_unique)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                company_name,
                scrape_date,
                regex_jobs_found,
                regex_leadership_jobs,
                regex_with_location,
                llm_jobs_found,
                llm_leadership_jobs,
                llm_with_location,
                llm_api_cost,
                overlap_count,
                regex_unique,
                llm_unique,
            ),
        )

        metrics_id = cursor.lastrowid
        conn.commit()
        conn.close()

        if metrics_id is None:
            raise RuntimeError("Failed to insert extraction metrics record")
        return metrics_id

    def get_extraction_metrics(self, company_name: str | None = None, days: int = 30) -> list[dict]:
        """Get extraction comparison metrics

        Args:
            company_name: Filter by company name (optional)
            days: Number of days to look back

        Returns:
            List of metrics dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if company_name:
            cursor.execute(
                """
                SELECT * FROM extraction_metrics
                WHERE company_name = ?
                  AND scrape_date >= date('now', '-' || ? || ' days')
                ORDER BY scrape_date DESC
            """,
                (company_name, days),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM extraction_metrics
                WHERE scrape_date >= date('now', '-' || ? || ' days')
                ORDER BY scrape_date DESC
            """,
                (days,),
            )

        metrics = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return metrics


if __name__ == "__main__":
    # Test the database
    db = JobDatabase()
    print("Database initialized successfully")
    print("Stats:", db.get_stats())
