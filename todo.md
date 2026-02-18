# TODO

## High Priority

### Monitoring & Observability
- [ ] Set up monitoring for cron job failures
- [ ] Add email alerts if weekly scraper fails
- [ ] Create dashboard for job scraping metrics (jobs found, scored, sent)

### Code Quality
- [ ] Add tests for company scraping modules
  - `src/scrapers/firecrawl_career_scraper.py`
  - `src/jobs/company_scraper.py`
  - `src/jobs/scrape_companies_with_firecrawl.py`
- [ ] Add type hints to scraping modules

## Medium Priority

### Features
- [ ] Configurable scoring weights (Issue #4)
- [ ] Daily digest option (Issue #3)
- [ ] Resume customization automation
- [ ] Interview preparation automation

### Documentation
- [ ] Add examples of successful company scraping runs
- [ ] Document Firecrawl MCP tool usage patterns
- [ ] Create troubleshooting guide for common scraping issues

## Completed This Session (Feb 2026)

### CI / Dev Workflow
- [x] Draft PR workflow: push branch + open draft PR immediately, mark ready when done (PR #284)
- [x] Skip SonarCloud on draft PRs — local SonarLint covers quality during active development
- [x] Add `ready_for_review` trigger so SonarCloud fires automatically on `gh pr ready`
- [x] Add concurrency cancellation to CI and security workflows (new push cancels stale run)

### Code Quality & Coverage
- [x] Fix database schema migration order — 3 indexes moved after ALTER TABLE guards (PR #282)
- [x] Add ALTER TABLE guards for 7 post-initial columns (filter_reason, stale_check, url_validated, etc.)
- [x] Fix `test_weekly_unified_scraper_all_inboxes` mock for `_scrape_shared_testdevjobs` (PR #282)
- [x] Sync `pyproject.toml` coverage omit list with `sonar.coverage.exclusions` (PR #282)
- [x] Add `TestDatabaseIncrementalMigration` tests to cover ALTER TABLE branches (PR #282)
- [x] **Result**: 263 test failures → 0, coverage 67% → 80% ✅

### TUI Refactoring
- [x] Reduce `main()` cognitive complexity 30 → 8 via three helper functions (PR #281)
  - `_handle_utility_action()`, `_handle_secondary_action()`, `_execute_workflow()`
- [x] Extract `PYTHON_EXECUTABLE` constant (PR #280, fixes #277)

## Completed (Jan 2026)
- [x] Fix test import errors — 1597 tests passing, 80% coverage ✅

## Completed (Nov 2025)
- [x] Firecrawl integration for robotics priority companies (PR #71)
- [x] Company scraper with auto-disable, budget tracking, rate limiting
- [x] Automated weekly company monitoring system
