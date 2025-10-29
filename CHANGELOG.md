# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Three new email parsers for expanded job source coverage
  - **Job Bank Parser** (`src/parsers/jobbank_parser.py`) - Parses Canadian Job Bank mechanical engineering alerts
  - **Recruiter Parser** (`src/parsers/recruiter_parser.py`) - Handles LinkedIn saved jobs and direct recruiter outreach
  - **Work In Tech Parser** (`src/parsers/workintech_parser.py`) - Parses Work In Tech (getro.com) job board emails
- Parser wrapper classes for integration with parser registry
  - `src/parsers/jobbank_wrapper.py` - Wraps Job Bank parser with BaseEmailParser interface
  - `src/parsers/recruiter_wrapper.py` - Wraps Recruiter parser with BaseEmailParser interface
  - `src/parsers/workintech_wrapper.py` - Wraps Work In Tech parser with BaseEmailParser interface
- Duplicate email prevention system
  - Added `sent_to_wes` and `sent_to_wes_at` columns to jobs database
  - New script `src/send_digest_to_wes_v2.py` - Only sends unsent jobs to prevent duplicates
  - New script `src/send_all_unsent_to_wes.py` - Sends comprehensive digest of ALL unsent jobs including low-scoring ones
- Workflow documentation (`docs/development/workflow-diagram.md`)
  - System architecture overview with data flow
  - Email processing pipeline sequence diagram
  - Job scoring system breakdown (115-point system)
  - Weekly automation cron flow
  - Parser registry pattern class diagram
  - Database schema ERD

### Changed
- Updated `config/parsers.json` to register and enable new parsers
  - Added jobbank_parser configuration
  - Added recruiter_parser configuration
  - Added workintech_parser configuration
- Enhanced `src/processor_v2.py` to track sent status
  - Marks jobs as sent after email digest generation
  - Prevents duplicate jobs in future digests

### Security
- **Eliminated 5 ReDoS Vulnerabilities** (PR #14 - Oct 28, 2025)
  - All email parsers now use ReDoS-safe patterns validated by SonarCloud
  - Replaced vulnerable regex patterns with string matching and split() operations
  - Zero remaining security hotspots in SonarCloud analysis

### Fixed
- Parser integration issues resolved
  - Fixed import errors with `BaseEmailParser` vs `ParserBase`
  - Added missing `can_handle` method implementations
  - Corrected parser configuration to enable new parsers
- **ReDoS Security Vulnerabilities** (PR #14 - Oct 28, 2025)
  - Eliminated 5 Regular Expression Denial of Service vulnerabilities in email parsers
  - `jobbank_parser.py`: Replaced regex pattern with simple string matching (`" new job -"` / `" new jobs -"`)
  - `recruiter_parser.py`: Fixed 3 patterns with nested quantifiers causing catastrophic backtracking
  - `workintech_parser.py`: Replaced complex regex with `split()` for middot separator parsing
  - All parsers now use ReDoS-safe patterns validated by SonarCloud
- **CI/CD Test Infrastructure** (PR #14 - Oct 28, 2025)
  - Added `PYTHONPATH=$PWD` to pytest commands in both `ci.yml` and `security.yml`
  - Fixed import errors in test execution for both local and CI environments
  - Configured coverage to use relative paths (`relative_files = true` in pyproject.toml)
  - SonarCloud now correctly receives and parses coverage data
  - Updated `sonar-project.properties` to exclude utility scripts from coverage requirements

## [0.2.1] - 2025-10-24

### Added
- Company Monitoring API with Flask backend for Chrome extension integration
  - POST /add-company - Add companies to monitoring list
  - GET /companies - List monitored companies
  - GET /company/<id> - Get specific company details
  - POST /company/<id>/toggle - Enable/disable company monitoring
- Comprehensive test suite for Company Monitoring API
  - 5 Flask API endpoint tests (`tests/unit/test_api_simple.py`)
  - 7 Database service layer tests (`tests/unit/test_company_service.py`)
  - 100% coverage on new code (77% app.py, 85% company_service.py)
- Environment variable configuration for production deployment
  - `FLASK_DEBUG` - Controls debug mode (default: false)
  - `FLASK_CORS_ORIGINS` - Configurable CORS origins (default: chrome-extension + localhost)
- Developer documentation (`docs/development/flask-api-setup.md`)
  - Quick start guide with curl examples
  - Environment variable reference
  - Testing instructions
  - Chrome extension integration guide
  - Production deployment checklist
- Chrome extension for adding companies while browsing (`chrome-extension/`)
- Companies database table in SQLite (`data/jobs.db`)

### Changed
- Improved code coverage configuration accuracy
  - Excluded utility scripts (generate_jobs_html.py, send_digest_*.py, processor_master.py)
  - Excluded test files in src/ (test_*.py, debug_*.py)
  - Coverage reporting improved from 19% to 25%
  - Updated both pytest (`pyproject.toml`) and SonarCloud (`sonar-project.properties`) configs

### Fixed
- Flask API tests now work in CI/CD environments
  - Implemented temporary database fixtures for testing
  - Fixed `sqlite3.OperationalError: unable to open database file` in GitHub Actions
- Removed hardcoded Flask debug mode security risk
  - Replaced `debug=True` with environment variable configuration
  - Removed `# nosec B201` security bypass

### Security
- Flask debug mode now defaults to secure (false) instead of `debug=True`
- CORS origins now configurable instead of hardcoded
- Pre-commit Safety hook passing (flask-cors 4.0.2)

### Technical Details
- **PRs Merged:** #11 (Company Monitoring API), #12 (Test Coverage), #13 (Production Readiness)
- **Issues Resolved:** #10 (Flask API production readiness)
- **Quality Metrics:** SonarCloud Quality Gate PASSED (100% new code coverage, all A ratings)
- **Test Results:** 54/54 tests passing

---

## [0.2.0] - 2025-10-XX

### Added
- Built In job alert email parser (`src/parsers/builtin_parser.py`)
  - Parses Built In job alert emails with AWS tracking URL handling
  - Style-based HTML parsing for job details extraction
  - 23 comprehensive tests with 93% coverage
- Type hint support for email.message.Message (forward references)

### Changed
- Updated `src/imap_client.py` with `from __future__ import annotations` for Python 3.9+ compatibility

---

## [0.1.0] - Initial Release

### Added
- Job discovery and scoring system for robotics/hardware executives
- Email processing pipeline for LinkedIn, Supra, F6S, Artemis newsletters
- Automated web scraping of robotics/deeptech job boards (1,092 jobs weekly)
- Intelligent job scoring system (115-point scale)
- Location-aware filtering (Remote, Hybrid Ontario, Ontario cities)
- SQLite database with deduplication
- Weekly email digests with HTML job tables
- Cron-based automation

[Unreleased]: https://github.com/adamkwhite/job-agent/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/adamkwhite/job-agent/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adamkwhite/job-agent/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adamkwhite/job-agent/releases/tag/v0.1.0
