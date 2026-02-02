# Testing Guide

This guide covers testing practices for the job-agent project, with special focus on database isolation to prevent test data from polluting production.

## Table of Contents

- [Test Database Isolation](#test-database-isolation)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Common Issues](#common-issues)
- [CI/CD Integration](#cicd-integration)

## Test Database Isolation

**CRITICAL**: All tests use isolated temporary databases to prevent production database pollution.

### The Problem We Solved

Before database isolation was implemented:
- 171 "Test Company" entries accumulated in production DB over 2 months
- Tests ran directly against `data/jobs.db`
- System Health dashboard showed 327 failures (48% were fake test data)

### The Solution

Tests now use the `DATABASE_PATH` environment variable to redirect all database operations to temporary, isolated databases that are automatically cleaned up.

## Running Tests

### Local Testing

```bash
# Run all tests with coverage
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_database.py -v

# Run with coverage for specific module
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/ --cov=src/database --cov-report=term-missing
```

### Coverage Requirements

**All new code MUST have ≥80% test coverage** (enforced by SonarCloud quality gate).

- Legacy code coverage is currently 17%, but this does **NOT** block PRs
- SonarCloud only checks coverage on NEW/CHANGED code in PRs
- Write tests in `tests/unit/` directory
- Follow existing test patterns (see `tests/unit/test_company_service.py`)

## Writing Tests

### Using Test Fixtures

The project provides two main fixtures for database testing:

#### `test_db` - Full Database Instance

Use when you need a complete `JobDatabase` object:

```python
def test_add_job(test_db):
    """test_db automatically provides isolated database."""
    job_data = {
        "title": "VP Engineering",
        "company": "Robotics Corp",
        "link": "https://example.com/job",
        "location": "Remote",
        "source": "test",
        "keywords_matched": ["robotics", "leadership"],
    }

    job_id = test_db.add_job(job_data)
    assert job_id is not None
    assert test_db.get_job_count() == 1
```

#### `test_db_path` - Database Path Only

Use when you need to create your own `JobDatabase` instance or pass the path to other services:

```python
def test_custom_init(test_db_path):
    """Use test_db_path for custom initialization."""
    db = JobDatabase(db_path=test_db_path, profile="test")
    assert db.profile == "test"

    # Or pass to services that need a path
    service = CompanyService(db_path=test_db_path)
```

### Test Structure Best Practices

```python
"""
Module-level docstring describing what's being tested
"""

import pytest
from src.database import JobDatabase

class TestFeatureName:
    """Group related tests together"""

    def test_specific_behavior(self, test_db):
        """Test one specific behavior - keep it focused"""
        # Arrange
        job_data = {...}

        # Act
        result = test_db.add_job(job_data)

        # Assert
        assert result is not None
```

### Testing Patterns

#### Testing Database Operations

```python
def test_database_operation(test_db):
    # test_db is already initialized with schema
    job_id = test_db.add_job(job_data)
    retrieved = test_db.get_job_by_id(job_id)
    assert retrieved["title"] == job_data["title"]
```

#### Testing with Migrations

```python
def test_with_migration(test_db_path):
    # Create database first
    db = JobDatabase(test_db_path)

    # Run migration
    from src.migrations import migration_003
    migration_003.migrate(test_db_path)

    # Test migration results
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(jobs)")
    columns = [row[1] for row in cursor.fetchall()]
    assert "filter_reason" in columns
    conn.close()
```

#### Testing Services

```python
def test_service(test_db_path):
    # Services often need a path, not a JobDatabase instance
    service = CompanyService(db_path=test_db_path)

    company_id = service.add_company({
        "name": "Test Corp",
        "careers_url": "https://example.com/careers"
    })

    assert company_id is not None
```

### Mocking External Dependencies

```python
def test_with_mocking(test_db, mocker):
    # Mock external API calls
    mock_scraper = mocker.patch("src.scrapers.firecrawl_career_scraper.FirecrawlCareerScraper")
    mock_scraper.return_value.scrape_jobs.return_value = []

    # Test your code without hitting real APIs
    result = scrape_company_jobs("https://example.com")
    assert result == []
```

## Common Issues

### Issue: "database is locked"

**Cause**: Multiple database connections or trying to use production DB during tests.

**Solution**: Use `test_db` or `test_db_path` fixtures instead of creating `JobDatabase()` directly.

```python
# ❌ BAD - Can cause locks
def test_something():
    db = JobDatabase()  # Uses production DB!

# ✅ GOOD - Uses isolated test DB
def test_something(test_db):
    # test_db is already isolated
```

### Issue: "Test Company" in production database

**Cause**: Tests running against production database instead of isolated test database.

**Solution**: Verify you're using test fixtures:

```python
def test_my_feature(test_db):  # ← test_db fixture required!
    assert str(test_db.db_path) != "data/jobs.db"  # Verify isolation
```

### Issue: Tests pass locally but fail in CI

**Possible causes**:
1. Test relies on data/jobs.db existing locally
2. Test modifies production database
3. Missing test fixture

**Solution**:
- Use `test_db` or `test_db_path` fixtures
- Check CI logs for DATABASE_PATH verification failures

## CI/CD Integration

### GitHub Actions Configuration

Tests in CI run with automatic database isolation:

```yaml
- name: Run tests with coverage
  env:
    DATABASE_PATH: /tmp/ci_test_jobs.db  # ← Enforced isolation
  run: |
    PYTHONPATH=$PWD pytest tests/ --cov=src
```

### Production Database Protection

CI includes a verification step that fails if `data/jobs.db` is modified:

```yaml
- name: Verify production DB not touched
  run: |
    # Checks if data/jobs.db was modified during tests
    # Fails CI if production database was touched
```

### What This Prevents

- Test data polluting production database
- "Test Company" entries accumulating
- False positives in System Health dashboard
- Production data being modified by test runs

## Environment Variables

### `DATABASE_PATH`

Controls which database file JobDatabase uses:

```bash
# Default (no env var) - uses production database
JobDatabase()  # → data/jobs.db

# With env var - uses test database
DATABASE_PATH=/tmp/test.db JobDatabase()  # → /tmp/test.db

# Explicit parameter - overrides env var
JobDatabase("/custom.db")  # → /custom.db
```

**Priority**: Explicit parameter > DATABASE_PATH env var > default (`data/jobs.db`)

## Migration Safety

Migrations include safety checks to prevent running on test databases:

```bash
# ❌ Will fail with error
DATABASE_PATH=/tmp/test.db python src/migrations/001_multi_person_scoring.py

# Output:
# ⚠️  WARNING: Detected test database path: /tmp/test.db
# Migrations should only run on production database.
```

This prevents accidental test database migrations during development.

## Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality:

- Ruff linting and formatting
- mypy type checking
- Bandit security scanning
- File validation

To skip hooks temporarily (use sparingly):

```bash
SKIP=python-safety-dependencies-check git commit -m "message"
```

## Test Organization

```
tests/
├── unit/               # Unit tests for core functionality
│   ├── test_database.py
│   ├── test_company_service.py
│   ├── test_job_scorer.py
│   └── ...
├── conftest.py        # Shared fixtures (test_db, test_db_path)
└── fixtures/          # Test data and helpers
```

## Additional Resources

- **Test Coverage Reports**: Generated in `htmlcov/` after running tests with `--cov`
- **SonarCloud**: Enforces 80% coverage on new code in PRs
- **Coverage Exemptions**: Legacy code (<17% coverage) doesn't block PRs

## Questions?

If you encounter issues or have questions about testing:

1. Check this guide's [Common Issues](#common-issues) section
2. Look at existing tests for patterns (e.g., `tests/unit/test_company_service.py`)
3. Review test output for helpful error messages
4. Check SonarCloud quality gate feedback on PRs
