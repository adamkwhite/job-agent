"""
Unit tests for LLM extraction database methods
"""

import sqlite3

import pytest

from src.database import JobDatabase


@pytest.fixture
def temp_db(test_db_path):
    """Create a temporary database for testing using centralized test_db_path"""
    db = JobDatabase(str(test_db_path))
    return db, test_db_path


class TestLLMExtractionFailures:
    """Test LLM extraction failure tracking"""

    def test_store_llm_failure_basic(self, temp_db):
        """Test storing a basic LLM failure"""
        db, _ = temp_db

        failure_id = db.store_llm_failure(
            company_name="Test Company",
            careers_url="https://example.com/careers",
            markdown_path="/tmp/test.md",
            failure_reason="Timeout",
            error_details="Request exceeded 30s limit",
        )

        assert failure_id is not None
        assert failure_id > 0

    def test_store_llm_failure_minimal(self, temp_db):
        """Test storing failure with only required fields"""
        db, _ = temp_db

        failure_id = db.store_llm_failure(company_name="Test Company")

        assert failure_id is not None

    def test_get_llm_failures_pending(self, temp_db):
        """Test retrieving pending failures"""
        db, _ = temp_db

        # Store multiple failures with different review_actions
        db.store_llm_failure(company_name="Company A", failure_reason="Timeout")
        db.store_llm_failure(company_name="Company B", failure_reason="Parse error")

        failures = db.get_llm_failures(review_action="pending")

        assert len(failures) == 2
        assert all(f["review_action"] == "pending" for f in failures)
        assert failures[0]["company_name"] in ["Company A", "Company B"]

    def test_get_llm_failures_all(self, temp_db):
        """Test retrieving all failures"""
        db, _ = temp_db

        db.store_llm_failure(company_name="Company A")
        db.store_llm_failure(company_name="Company B")
        db.store_llm_failure(company_name="Company C")

        failures = db.get_llm_failures()

        assert len(failures) == 3

    def test_get_llm_failures_limit(self, temp_db):
        """Test limit parameter works"""
        db, _ = temp_db

        for i in range(10):
            db.store_llm_failure(company_name=f"Company {i}")

        failures = db.get_llm_failures(limit=5)

        assert len(failures) == 5

    def test_llm_failure_ordered_by_date(self, temp_db):
        """Test failures are returned newest first"""
        db, db_path = temp_db

        # Store failures at different times
        db.store_llm_failure(company_name="Old Company")
        db.store_llm_failure(company_name="New Company")

        failures = db.get_llm_failures()

        # Newest should be first (DESC order)
        assert failures[0]["company_name"] == "New Company"
        assert failures[1]["company_name"] == "Old Company"

    def test_llm_failure_allows_multiple_per_company(self, temp_db):
        """Test that same company can have multiple failures at different times"""
        db, db_path = temp_db

        # Store first failure
        db.store_llm_failure(company_name="Test Company", failure_reason="Timeout")

        # Store second failure for same company (will have different timestamp)
        db.store_llm_failure(company_name="Test Company", failure_reason="Parse error")

        failures = db.get_llm_failures()
        # Should have two records with different timestamps
        assert len(failures) == 2
        assert all(f["company_name"] == "Test Company" for f in failures)


class TestExtractionMetrics:
    """Test extraction comparison metrics tracking"""

    def test_store_extraction_metrics(self, temp_db):
        """Test storing extraction metrics"""
        db, _ = temp_db

        metrics_id = db.store_extraction_metrics(
            company_name="Test Company",
            regex_jobs_found=10,
            regex_leadership_jobs=3,
            regex_with_location=8,
            llm_jobs_found=12,
            llm_leadership_jobs=4,
            llm_with_location=11,
            llm_api_cost=0.015,
            overlap_count=9,
            regex_unique=1,
            llm_unique=3,
        )

        assert metrics_id is not None
        assert metrics_id > 0

    def test_get_extraction_metrics_by_company(self, temp_db):
        """Test retrieving metrics for specific company"""
        db, _ = temp_db

        db.store_extraction_metrics(
            company_name="Company A",
            regex_jobs_found=10,
            regex_leadership_jobs=3,
            regex_with_location=8,
            llm_jobs_found=12,
            llm_leadership_jobs=4,
            llm_with_location=11,
            llm_api_cost=0.015,
            overlap_count=9,
            regex_unique=1,
            llm_unique=3,
        )

        db.store_extraction_metrics(
            company_name="Company B",
            regex_jobs_found=5,
            regex_leadership_jobs=1,
            regex_with_location=4,
            llm_jobs_found=6,
            llm_leadership_jobs=2,
            llm_with_location=5,
            llm_api_cost=0.01,
            overlap_count=4,
            regex_unique=1,
            llm_unique=2,
        )

        metrics = db.get_extraction_metrics(company_name="Company A")

        assert len(metrics) == 1
        assert metrics[0]["company_name"] == "Company A"
        assert metrics[0]["regex_jobs_found"] == 10
        assert metrics[0]["llm_api_cost"] == 0.015

    def test_get_extraction_metrics_all(self, temp_db):
        """Test retrieving all metrics"""
        db, _ = temp_db

        db.store_extraction_metrics(
            company_name="Company A",
            regex_jobs_found=10,
            regex_leadership_jobs=3,
            regex_with_location=8,
            llm_jobs_found=12,
            llm_leadership_jobs=4,
            llm_with_location=11,
            llm_api_cost=0.015,
            overlap_count=9,
            regex_unique=1,
            llm_unique=3,
        )

        db.store_extraction_metrics(
            company_name="Company B",
            regex_jobs_found=5,
            regex_leadership_jobs=1,
            regex_with_location=4,
            llm_jobs_found=6,
            llm_leadership_jobs=2,
            llm_with_location=5,
            llm_api_cost=0.01,
            overlap_count=4,
            regex_unique=1,
            llm_unique=2,
        )

        metrics = db.get_extraction_metrics()

        assert len(metrics) == 2

    def test_extraction_metrics_unique_constraint(self, temp_db):
        """Test UNIQUE constraint on (company_name, scrape_date)"""
        db, db_path = temp_db

        # Store first metrics
        db.store_extraction_metrics(
            company_name="Test Company",
            regex_jobs_found=10,
            regex_leadership_jobs=3,
            regex_with_location=8,
            llm_jobs_found=12,
            llm_leadership_jobs=4,
            llm_with_location=11,
            llm_api_cost=0.015,
            overlap_count=9,
            regex_unique=1,
            llm_unique=3,
        )

        # Store again for same company on same day - should replace
        db.store_extraction_metrics(
            company_name="Test Company",
            regex_jobs_found=20,
            regex_leadership_jobs=5,
            regex_with_location=15,
            llm_jobs_found=22,
            llm_leadership_jobs=6,
            llm_with_location=20,
            llm_api_cost=0.02,
            overlap_count=18,
            regex_unique=2,
            llm_unique=4,
        )

        metrics = db.get_extraction_metrics(company_name="Test Company")

        # Should only have one record (REPLACE on conflict)
        assert len(metrics) == 1
        # Should have updated values
        assert metrics[0]["regex_jobs_found"] == 20


class TestJobsExtractionColumns:
    """Test new extraction_method and extraction_cost columns on jobs table"""

    def test_extraction_columns_exist(self, temp_db):
        """Test that extraction_method and extraction_cost columns exist"""
        db, db_path = temp_db

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]

        assert "extraction_method" in columns
        assert "extraction_cost" in columns

        conn.close()

    def test_add_job_with_extraction_fields(self, temp_db):
        """Test adding job with extraction_method and extraction_cost"""
        db, _ = temp_db

        job_data = {
            "title": "Software Engineer",
            "company": "Test Corp",
            "location": "Remote",
            "link": "https://example.com/job/123",
            "description": "Test job description",
            "salary": "$100k-$150k",
            "job_type": "Full-time",
            "posted_date": "2025-12-06",
            "source": "company_scraper",
            "source_email": None,
            "keywords_matched": '["software", "engineer"]',
            "raw_email_content": None,
            "fit_score": 85,
            "fit_grade": "B",
            "score_breakdown": '{"seniority": 15, "domain": 20}',
            "extraction_method": "llm",
            "extraction_cost": 0.015,
        }

        job_id = db.add_job(job_data)

        assert job_id is not None
        assert job_id > 0
