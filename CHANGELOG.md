# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Hybrid Filtering Mode Implementation** (Jan 13, 2026 - Issue #208, PR #211)
  - Implemented Option 3 (Hybrid mode) chosen by Wes
  - Companies in curated software list now ALWAYS filtered for engineering roles in moderate mode
  - Added hybrid logic to should_filter_job() in company_classifier.py (lines 749-757)
  - New filter reason: `curated_software_company_moderate`
  - Result: All 6 problematic companies now filtered (Blue J, Raya, Venn, BairesDev, BuildOps, Extreme Networks)
  - Product roles at software companies still come through (verified with tests)
  - Added 2 comprehensive tests: test_curated_software_company_filtered_hybrid_mode, test_curated_software_company_product_not_filtered
  - All 17 filtering tests passing

- **Company Classifier Improvements** (Jan 12, 2026 - Issue #208, PR #209)
  - Added 6 problematic software companies to curated list: Blue J, BuildOps, Raya, Venn, BairesDev, Extreme Networks
  - Improved software indicator keywords: Labs, Dev, Build, Systems, Networks, Tech, Solutions, Digital, App, Web
  - Fixed aggressive mode bug: hardware companies (Boston Dynamics, Figure) no longer filtered in aggressive mode
  - Added hardware company check before aggressive filtering logic (lines 715-718 in company_classifier.py)
  - Updated test for new filter reason string: `hardware_company_engineering_allowed`
  - Result: BuildOps and Extreme Networks filtered in moderate mode (0.70 confidence), 4 others still passed through

### Added
- **LangSmith Observability PRD** (Jan 12, 2026 - Issue #210)
  - Created PRD for integrating LangSmith observability into LLM extraction pipeline
  - Track LLM API costs per run, per company, per job found
  - Monitor performance: latency distribution, token usage, cache effectiveness
  - Debug quality issues: JSON parse failures (8% failure rate), prompt effectiveness
  - Goals: 20% cost reduction through prompt optimization, reduce failures from 8% to <2%
  - File: `docs/features/langsmith-observability-PLANNED/prd.md`

### Changed
- **Documentation Updates** (Jan 9, 2026)
  - Updated scoring system documentation to reflect 100-point base system (max 110 with bonuses)
  - Removed outdated references to 115-point system (Company Stage category was previously removed)
  - Updated README.md, CLAUDE.md, profiles/README.md, and job_scorer.py inline comments
  - Current scoring: Seniority (30) + Domain (25) + Role Type (20) + Location (15) + Technical (10) + Company Classification (±20)

### Added
- **Filter Pipeline Integration** (Dec 13, 2025 - Issues #161, #162, PR #167)
  - Integrated 3-stage filtering into company_scraper.py and processor_v2.py
  - Hard filters applied before scoring (junior/intern titles, excluded keywords)
  - Context filters applied after scoring (low seniority + contract, etc.)
  - Filtered jobs stored in database with `filter_reason` and `filtered_at` for audit
  - New stats tracking: `jobs_hard_filtered` and `jobs_context_filtered`
  - Database method `mark_job_filtered()` for tracking filtered jobs
  - Stale job filtering in digest generation using `JobValidator.validate_for_digest()`
  - Age-based filtering (jobs >60 days automatically excluded)
  - LinkedIn content-based filtering ("no longer accepting applications")
  - URL validation caching for performance
  - `--max-age-days` flag added to `send_profile_digest.py` (default: 7 days)
  - Progress indicators during URL validation and age checking phases
  - Test coverage: 9 new tests across company_scraper, processor_v2, database
- **Progress Indicators for Digest Validation** (Dec 13, 2025 - PR #169)
  - Real-time progress during stale job filtering phase
  - Shows `[N/total] Company - Job Title...` with ✓/⛔ status
  - Matches URL validation phase style for consistency
  - Provides user feedback during long-running validations

### Added
- **Firecrawl Integration for Robotics Career Pages** (Nov 29-30, 2025 - Issues #65-#69, PR #71)
  - Semi-automated workflow to scrape 10 priority robotics companies' generic career pages
  - Companies: Boston Dynamics, Figure, Sanctuary AI, Agility Robotics, 1X Technologies, Skydio, Skild AI, Dexterity, Covariant, Nuro
  - Configuration file (`config/robotics_priority_companies.json`) with rate limits, budgets, failure thresholds
  - `scrape_with_firecrawl_fallback()` method identifies generic career pages from priority companies
  - `process_firecrawl_markdown()` extracts leadership jobs from Firecrawl markdown output
  - Phase 2 workflow outputs Firecrawl MCP commands for manual execution
  - Credit budget tracking: 50 credits/week, 200/month (~$20/month cost)
  - Failure monitoring: 50% threshold with auto-disable recommendations
  - Automated GitHub issue creation for repeated scraping failures (3+ consecutive)
  - Markdown caching to `data/firecrawl_cache/` for debugging
  - Expected to discover 25-50+ additional leadership jobs per week
  - Test coverage: 21 new tests (98% scraper, 72% weekly integration)
- **7-Category Job Scoring System** (Nov 15, 2025 - Issue #56)
  - Implemented comprehensive 7-category role scoring with keyword bonuses
  - Categories: Product Leadership, Engineering Leadership, Technical Program Management, Manufacturing/NPI/Operations, Product Development/R&D, Platform/Integrations/Systems, Robotics/Automation Engineering
  - Base scores (10-20 points) + keyword bonuses (+2 per match from must_keywords & nice_keywords)
  - 100+ domain-specific keywords in `config/filter-keywords.json`
  - Software engineering leadership penalty: -5 points
  - Total scoring system: 115 points (Seniority 30 + Domain 25 + Role 20 + Location 15 + Company Stage 15 + Technical 10)
  - Grade thresholds: A (98+), B (80+), C (63+), D (46+), F (<46)
- **Historical Job Re-scoring Tool** (`src/rescore_all_jobs.py`)
  - Re-evaluate all historical jobs with updated scoring criteria
  - Dry-run mode for impact preview
  - Configurable minimum score threshold
  - Shows newly qualifying jobs, score changes, and grade transitions
  - Example results: 10 newly qualifying jobs at 70+ threshold, 2 upgraded to B grade
- **Scoring Update Documentation & Enforcement**
  - Comprehensive checklist: `docs/development/SCORING_UPDATE_CHECKLIST.md`
  - GitHub issue template: `.github/ISSUE_TEMPLATE/scoring-update.md`
  - Warning comments in `job_scorer.py` and `send_digest_to_wes.py`
  - References added to CLAUDE.md and README.md
- **Automated Scoring/Email Sync Enforcement** (3-layer protection)
  - GitHub Action (`.github/workflows/check-scoring-sync.yml`) - fails PR if email template not updated
  - Pre-commit hook (`.pre-commit-hooks/check-scoring-sync.sh`) - local warning before commit
  - Branch protection documentation (`docs/development/GITHUB_REQUIRED_CHECKS.md`)
  - Prevents email template from getting out of sync with scoring logic

### Changed
- **Email Digest Template Updated** (`src/send_digest_to_wes.py` lines 222-238)
  - Documented new 7-category scoring system
  - Shows category ranges and keyword bonus system
  - Clarifies software penalty and location scoring details
- **Robotics Scraper Output Optimization**
  - Reduced duplicate "Skipping generic career page" warnings
  - Now warns once per unique URL instead of per job row
  - Example: Gecko Robotics (16 jobs) now shows 1 warning instead of 16

- **Job Scoring - Refined Role Type Scoring** (Nov 13, 2025)
  - Implemented tiered scoring system prioritizing product/hardware roles (Issue #53)
  - Product + Hardware/Technical roles now score 20 points (top tier)
  - Product + Engineering dual roles score 18 points
  - Product Leadership increased from 10 to 15 points
  - Program/PMO Leadership added as new tier (12 points)
  - Pure software engineering leadership now receives -5 point penalty
  - Scoring aligns with Wesley's background in connected hardware, IoT, MedTech, mechatronics
  - Updated email digest template to reflect new scoring criteria
  - Tests updated to verify product roles prioritized over pure software engineering

### Added
- **Automated Weekly Company Monitoring** (Oct 30, 2025)
  - New company scraping infrastructure for monitoring Wes's 26 companies
  - `src/jobs/scrape_companies_with_firecrawl.py` - Coordinates Firecrawl MCP scraping workflow
  - `src/jobs/company_scraper.py` - Company scraping orchestration with database integration
  - `src/scrapers/firecrawl_career_scraper.py` - Firecrawl-based career page scraper
  - `src/jobs/store_company_jobs.py` - One-time import script for 14 leadership jobs
  - `src/jobs/weekly_unified_scraper.py` - Unified scraper combining emails, robotics, and companies
  - Job extraction from markdown with multiple pattern matching strategies
  - Leadership role filtering (Director, VP, Manager, etc.)
  - Integration with existing scoring and notification system
  - Semi-automated workflow requiring Claude Code for Firecrawl MCP tool calls
- Documentation for automated workflows
  - `docs/weekly-automation-workflow.md` - Complete weekly automation guide
  - `docs/system-diagram.md` - Visual architecture diagram showing all three job sources
  - `docs/unified-weekly-scraper.md` - Unified scraper documentation
- Company data management
  - `data/job_sources.csv` - 26 companies from Wes with career page URLs
  - Company database table with last_checked tracking
  - Imported 14 leadership jobs from manual scraping into database
- Setup scripts
  - `scripts/setup_unified_weekly_scraper.sh` - Cron job configuration for weekly scraping
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
- **Weekly Digest Tracking System** (Oct 30, 2025)
  - Added `digest_sent_at` field to database schema for tracking weekly digest sends
  - Updated `src/database.py` with `mark_digest_sent()` and `get_jobs_for_digest()` methods
  - Modified `src/send_digest_to_wes.py` to mark jobs as sent and prevent duplicates
  - Added `--force-resend` flag for testing digest emails
  - Fixed CC email address from incorrect "roomzz.com" to "adamkwhite@gmail.com"
  - Digest now only sends unsent jobs (no duplicates across weekly digests)
- Improved company scraper integration
  - Updated `src/jobs/company_scraper.py` to call Firecrawl and process results
  - Modified `src/scrapers/firecrawl_career_scraper.py` with improved job extraction patterns
  - Enhanced markdown parsing to handle multiple career page formats
- Updated `config/parsers.json` to register and enable new parsers
  - Added jobbank_parser configuration
  - Added recruiter_parser configuration
  - Added workintech_parser configuration
- Enhanced `src/processor_v2.py` to track sent status
  - Marks jobs as sent after email digest generation
  - Prevents duplicate jobs in future digests

### Fixed
- **SonarCloud Code Quality Issues** (Nov 13, 2025 - PR #55)
  - Fixed duplicate character classes in regex patterns (email_company_extractor.py)
  - Defined constants for duplicated string literals across 3 parsers
  - Removed unused function parameters in company_discoverer.py
  - Fixed ReDoS vulnerability in unified_scraper_v3.py by moving keyword filtering to Python
  - Corrected absolute imports to relative imports in parser_registry.py
  - Reduced SonarCloud code smell count from 53 to 43

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
