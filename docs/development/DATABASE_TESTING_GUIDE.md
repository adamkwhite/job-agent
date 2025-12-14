# Database Unit Testing Guide

**Complete guide to writing database migration tests that ensure data safety and achieve ≥80% code coverage.**

---

## Table of Contents

1. [Foundation: Temporary Databases](#foundation-temporary-databases)
2. [Fixtures for Test Data](#fixtures-for-test-data)
3. [The 7 Essential Migration Tests](#the-7-essential-migration-tests)
4. [Avoiding "Database is Locked" Errors](#avoiding-database-is-locked-errors)
5. [Testing Different Value Types](#testing-different-value-types)
6. [Performance Testing with Indexes](#performance-testing-with-indexes)
7. [Key Patterns to Remember](#key-patterns-to-remember)
8. [Coverage Goals](#coverage-goals)

---

## Foundation: Temporary Databases

**Always use temporary databases for tests to avoid affecting real data.**

```python
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_db(self):
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    yield db_path
    # Cleanup after test
    Path(db_path).unlink(missing_ok=True)
```

**Why**: Isolation - each test gets a fresh database, no cross-test contamination.

---

## Fixtures for Test Data

**Create fixtures that set up realistic test scenarios:**

```python
@pytest.fixture
def db_with_existing_jobs(self, temp_db):
    """Create database with existing jobs before migration"""
    db = JobDatabase(db_path=temp_db)

    # Add sample data
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
        # ... more jobs
    ]

    job_ids = []
    for job_data in jobs_data:
        # Extract score data (not stored directly by add_job)
        score = job_data.pop("score")
        grade = job_data.pop("grade")
        breakdown = job_data.pop("breakdown")

        # Add job
        job_id = db.add_job(job_data)
        if job_id:
            # Update score separately
            db.update_job_score(job_id, score, grade, breakdown)
            job_ids.append(job_id)

    return temp_db, job_ids, jobs_data
```

**Why**: Reusable test data prevents duplication and ensures consistency.

---

## The 7 Essential Migration Tests

### Test 1: Schema Changes

**Verify migration creates all expected columns with correct types and defaults.**

```python
def test_migration_adds_all_columns(self, temp_db):
    """Test that migration adds all 4 new columns"""
    # Initialize database
    db = JobDatabase(db_path=temp_db)

    # Run migration
    success = migration.migrate(db_path=temp_db)
    assert success is True

    # Verify all columns exist
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    columns = {col[1]: col for col in cursor.fetchall()}
    conn.close()

    # Check column existence
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
```

**What it proves**: Migration created all expected columns with correct types and defaults.

---

### Test 2: Data Preservation

**Prove no data loss or corruption during schema changes.**

```python
def test_migration_preserves_existing_data(self, db_with_existing_jobs):
    """Test that existing jobs are not affected by migration"""
    temp_db, job_ids, original_jobs = db_with_existing_jobs

    # Get data BEFORE migration
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company, link, fit_score FROM jobs ORDER BY id")
    before_migration = cursor.fetchall()
    conn.close()

    # Run migration
    success = migration.migrate(db_path=temp_db)
    assert success is True

    # Get data AFTER migration
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company, link, fit_score FROM jobs ORDER BY id")
    after_migration = cursor.fetchall()
    conn.close()

    # Verify data unchanged
    assert len(before_migration) == len(after_migration)
    assert before_migration == after_migration

    # Verify specific fields (extra validation)
    assert after_migration[0][1] == "VP Engineering"  # title
    assert after_migration[0][4] == 85  # fit_score
    assert after_migration[1][1] == "Director of Product"
    assert after_migration[1][4] == 75
```

**What it proves**: No data loss or corruption during schema changes.

---

### Test 3: Default Values

**Verify new columns get correct default values for existing rows.**

```python
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
```

**What it proves**: New columns get correct default values for existing rows.

---

### Test 4: Idempotency

**Prove migration is safe to re-run (important for deployments).**

```python
def test_migration_is_idempotent(self, temp_db):
    """Test that migration can be run multiple times without errors"""
    db = JobDatabase(db_path=temp_db)

    # Run migration first time
    success1 = migration.migrate(db_path=temp_db)
    assert success1 is True

    # Run migration second time (should not crash)
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
```

**What it proves**: Safe to re-run migration (critical for deployment safety).

---

### Test 5: Index Creation

**Verify performance indexes are created correctly.**

```python
def test_migration_creates_indexes(self, temp_db):
    """Test that migration creates performance indexes"""
    db = JobDatabase(db_path=temp_db)

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
```

**What it proves**: Performance indexes are created correctly.

---

### Test 6: Existing Operations Still Work

**Prove migration doesn't break existing functionality.**

```python
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
        "keywords_matched": "[]",
        "source_email": "",
    }

    new_job_id = db.add_job(new_job)
    assert new_job_id is not None

    # 2. Update job score
    db.update_job_score(new_job_id, 92, "A", '{"seniority": 30, "domain": 25, "role_type": 20}')

    # 3. Mark as notified
    db.mark_notified(new_job_id)

    # 4. Get jobs (verify count)
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
```

**What it proves**: Migration doesn't break existing functionality.

---

### Test 7: New Columns Can Be Used

**Verify new columns are functional and queryable.**

```python
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
    cursor.execute("SELECT id, filter_reason, stale_check_result FROM jobs WHERE filter_reason IS NOT NULL")
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
```

**What it proves**: New columns are functional and queryable.

---

## Avoiding "Database is Locked" Errors

**The Problem**: SQLite only allows one writer at a time.

**Common Mistake**:
```python
# ❌ WRONG - Opens connection, then db.add_job() opens another
conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

for job in jobs:
    job_id = db.add_job(job)  # Opens new connection internally - LOCK!
    cursor.execute("UPDATE ...", job_id)  # Tries to write - ERROR!
```

**The Solution**: Separate into phases and close connections:

```python
# ✅ RIGHT - Separate into phases

# Phase 1: Use JobDatabase API (no open connections)
job_ids = []
for i, job in enumerate(jobs):
    job_id = db.add_job(job)
    job_ids.append((job_id, values[i]))

# Phase 2: Close any lingering connections, then use SQL
conn = sqlite3.connect(temp_db)
cursor = conn.cursor()

for job_id, value in job_ids:
    cursor.execute("UPDATE jobs SET filter_reason = ? WHERE id = ?", (value, job_id))

conn.commit()
conn.close()
```

**Key Pattern**: Never mix `JobDatabase` API calls with an open `sqlite3.connect()` in the same loop.

---

## Testing Different Value Types

**Test all expected enum/category values:**

```python
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

    # Phase 1: Add jobs
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

    # Close to avoid database locked
    conn.close()

    # Phase 2: Update with filter reasons
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
```

**What it proves**: Column can handle all expected data values.

---

## Performance Testing with Indexes

**Verify indexes are actually being used by SQLite optimizer:**

```python
def test_query_performance_with_indexes(self, temp_db):
    """Test that index creation improves query performance"""
    db = JobDatabase(db_path=temp_db)
    migration.migrate(db_path=temp_db)

    # Add 100 jobs with various filter reasons
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
        # Set filter reason for half the jobs
        if i % 2 == 0:
            job_ids.append(job_id)

    # Update with filter reasons
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    for job_id in job_ids:
        cursor.execute(
            "UPDATE jobs SET filter_reason = ? WHERE id = ?",
            ("hard_filter_hr_role", job_id),
        )

    conn.commit()

    # Verify index is being used (check EXPLAIN QUERY PLAN)
    cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM jobs WHERE filter_reason = 'hard_filter_hr_role'")
    query_plan = cursor.fetchall()

    conn.close()

    # Query plan should mention the index
    query_plan_str = " ".join([str(row) for row in query_plan])
    assert "idx_jobs_filter_reason" in query_plan_str or "USING INDEX" in query_plan_str
```

**What it proves**: Indexes are actually being used by SQLite optimizer for better performance.

---

## Key Patterns to Remember

1. **Always use temp databases** - Never test on production DB
2. **Test before AND after migration** - Prove data preservation
3. **Test all schema aspects** - Columns, types, defaults, indexes
4. **Test functionality** - Prove existing operations still work
5. **Close connections properly** - Avoid "database is locked"
6. **Use fixtures for reusable data** - DRY principle
7. **Test edge cases** - NULL values, empty strings, large datasets
8. **Separate API calls from SQL** - Don't mix in same loop

---

## Coverage Goals

### SonarCloud Requirement: ≥80% Coverage

**CRITICAL**: SonarCloud quality gate will **FAIL** if new code has less than 80% test coverage.

**Target**: Aim for **80-90% coverage** on migration files.

### Example Coverage from Migration #003

```
src/migrations/003_filter_tracking.py    44     10    77%
```

**Covered (77%)**:
- ✅ Successful migration path
- ✅ Column existence checks
- ✅ All ALTER TABLE statements
- ✅ Index creation
- ✅ Success return

**Uncovered (acceptable)**:
- ❌ `db_path not found` error path (would need deleted DB)
- ❌ Rollback function (intentionally a no-op for SQLite)
- ❌ `__main__` block (command-line execution)

### How to Achieve 80%+ Coverage

1. **Test happy path thoroughly** - Success case covers most code
2. **Test idempotency** - Covers "column already exists" branches
3. **Test index creation** - Covers CREATE INDEX statements
4. **Test data operations** - Covers column usage
5. **Skip error paths** - Database missing, rollback (acceptable to leave uncovered)

### Running Coverage Locally

```bash
# Run tests with coverage report
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_database_migration_003.py -v --cov=src/migrations --cov-report=term-missing

# View detailed HTML report
open htmlcov/index.html
```

### When Coverage Falls Below 80%

**SonarCloud will block your PR**. To fix:

1. Check which lines are uncovered in the report
2. Add tests for uncovered happy paths
3. For error paths: Consider if they're testable
4. Document why certain lines can't be covered (e.g., SQLite limitations)

**Example**: If `ALTER TABLE` error path is uncovered, you'd need to intentionally corrupt the database - often not worth the complexity.

---

## Complete Example

See `tests/unit/test_database_migration_003.py` for a complete working example with all 7 essential tests achieving 77% coverage.

**Key Takeaway**: Database tests prove your migration is safe for production. They give you confidence that when you deploy, you won't lose data or break functionality. The 80% coverage requirement ensures comprehensive testing before code reaches production.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
