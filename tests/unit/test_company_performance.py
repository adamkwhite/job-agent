"""Tests for company performance database methods (Issue #180)"""

import sqlite3

import pytest

from database import JobDatabase


@pytest.fixture
def perf_db(tmp_path):
    """Create a temp database with extraction_metrics table"""
    db_path = str(tmp_path / "test.db")
    db = JobDatabase(db_path=db_path)

    # Ensure extraction_metrics table exists
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS extraction_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            scrape_date TEXT,
            regex_jobs_found INTEGER DEFAULT 0,
            regex_leadership_jobs INTEGER DEFAULT 0,
            regex_with_location INTEGER DEFAULT 0,
            llm_jobs_found INTEGER DEFAULT 0,
            llm_leadership_jobs INTEGER DEFAULT 0,
            llm_with_location INTEGER DEFAULT 0,
            llm_api_cost REAL DEFAULT 0.0,
            overlap_count INTEGER DEFAULT 0,
            regex_unique INTEGER DEFAULT 0,
            llm_unique INTEGER DEFAULT 0,
            scraper_backend TEXT DEFAULT 'playwright',
            careers_url TEXT DEFAULT '',
            total_jobs_found INTEGER DEFAULT 0,
            fetch_success INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

    return db, db_path


def _insert_metric(
    db_path: str,
    company: str,
    scrape_date: str,
    total_jobs: int = 10,
    fetch_success: int = 1,
) -> None:
    """Helper to insert a metric row directly"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO extraction_metrics
            (company_name, scrape_date, total_jobs_found, fetch_success, scraper_backend)
        VALUES (?, ?, ?, ?, 'playwright')
        """,
        (company, scrape_date, total_jobs, fetch_success),
    )
    conn.commit()
    conn.close()


class TestGetCompanyPerformanceSummary:
    def test_empty_returns_empty(self, perf_db: tuple) -> None:
        db, _ = perf_db
        assert db.get_company_performance_summary(days=30) == []

    def test_single_company_aggregation(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        _insert_metric(db_path, "Acme", "2099-01-01", total_jobs=10)
        _insert_metric(db_path, "Acme", "2099-01-02", total_jobs=20)
        _insert_metric(db_path, "Acme", "2099-01-03", total_jobs=15)

        # Use very large days window to capture future dates
        results = db.get_company_performance_summary(days=99999)
        assert len(results) == 1
        assert results[0]["company_name"] == "Acme"
        assert results[0]["scrape_count"] == 3
        assert results[0]["total_jobs"] == 45
        assert results[0]["avg_jobs_per_scrape"] == 15.0

    def test_multiple_companies_ordered_by_total_jobs(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        _insert_metric(db_path, "SmallCo", "2099-01-01", total_jobs=2)
        _insert_metric(db_path, "BigCo", "2099-01-01", total_jobs=50)

        results = db.get_company_performance_summary(days=99999)
        assert len(results) == 2
        assert results[0]["company_name"] == "BigCo"
        assert results[1]["company_name"] == "SmallCo"

    def test_failure_rate_calculation(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        _insert_metric(db_path, "Flaky", "2099-01-01", total_jobs=5, fetch_success=1)
        _insert_metric(db_path, "Flaky", "2099-01-02", total_jobs=0, fetch_success=0)
        _insert_metric(db_path, "Flaky", "2099-01-03", total_jobs=0, fetch_success=0)

        results = db.get_company_performance_summary(days=99999)
        assert len(results) == 1
        # 2 out of 3 failed = 66.7%
        assert results[0]["failure_count"] == 2
        assert results[0]["failure_rate"] == pytest.approx(66.7, abs=0.1)

    def test_zero_job_scrapes_counted(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        # Successful fetch but 0 jobs
        _insert_metric(db_path, "Empty", "2099-01-01", total_jobs=0, fetch_success=1)
        _insert_metric(db_path, "Empty", "2099-01-02", total_jobs=5, fetch_success=1)

        results = db.get_company_performance_summary(days=99999)
        assert results[0]["zero_job_scrapes"] == 1


class TestGetUnderperformingCompanies:
    def test_high_failure_rate_flagged(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        # 3 scrapes, 2 failures = 67% failure rate
        _insert_metric(db_path, "Broken", "2099-01-01", total_jobs=5, fetch_success=1)
        _insert_metric(db_path, "Broken", "2099-01-02", total_jobs=0, fetch_success=0)
        _insert_metric(db_path, "Broken", "2099-01-03", total_jobs=0, fetch_success=0)

        results = db.get_underperforming_companies(days=99999, min_scrapes=3)
        assert len(results) == 1
        assert results[0]["company_name"] == "Broken"

    def test_low_yield_flagged(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        # 3 scrapes, avg 0.3 jobs
        _insert_metric(db_path, "LowYield", "2099-01-01", total_jobs=0, fetch_success=1)
        _insert_metric(db_path, "LowYield", "2099-01-02", total_jobs=1, fetch_success=1)
        _insert_metric(db_path, "LowYield", "2099-01-03", total_jobs=0, fetch_success=1)

        results = db.get_underperforming_companies(days=99999, min_scrapes=3)
        assert len(results) == 1
        assert results[0]["company_name"] == "LowYield"

    def test_min_scrapes_filter(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        # Only 2 scrapes, both failures — but min_scrapes=3
        _insert_metric(db_path, "TooFew", "2099-01-01", total_jobs=0, fetch_success=0)
        _insert_metric(db_path, "TooFew", "2099-01-02", total_jobs=0, fetch_success=0)

        results = db.get_underperforming_companies(days=99999, min_scrapes=3)
        assert len(results) == 0

    def test_healthy_company_excluded(self, perf_db: tuple) -> None:
        db, db_path = perf_db
        _insert_metric(db_path, "Healthy", "2099-01-01", total_jobs=20, fetch_success=1)
        _insert_metric(db_path, "Healthy", "2099-01-02", total_jobs=15, fetch_success=1)
        _insert_metric(db_path, "Healthy", "2099-01-03", total_jobs=18, fetch_success=1)

        results = db.get_underperforming_companies(days=99999, min_scrapes=3)
        assert len(results) == 0

    def test_empty_when_all_healthy(self, perf_db: tuple) -> None:
        db, _ = perf_db
        assert db.get_underperforming_companies(days=99999) == []
