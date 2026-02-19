# TODO

## High Priority

### Monitoring & Observability
- [ ] Set up monitoring for cron job failures
- [ ] Add email alerts if weekly scraper fails

### Code Quality (SonarCloud)
- [ ] Overnight batch A: trivial fixes (S3626, S125, S1481, S6965) — tui.py, company_service.py, app.py, 4 scrapers/parsers
- [ ] Overnight batch B: company_scraper.py unused params (S1172) — 5 parameters
- [ ] Overnight batch C: TUI string constants (S1192) — 7 repeated literals
- [ ] Overnight batch D: moderate complexity reductions (16–19) — database.py, testdevjobs scraper, wellfound, linkedin, firecrawl scraper
- [ ] Overnight batch E: feedback_parser.py regex — S5869 x3 (duplicate chars) + S6019 (logic bug)

### Code Quality (Tests)
- [ ] Add tests for company scraping modules
  - `src/scrapers/firecrawl_career_scraper.py`
  - `src/jobs/company_scraper.py`

## Medium Priority

### Features
- [ ] Daily digest option (Issue #3)
- [ ] Two-tier scoring: skip low-hit-rate companies to save Firecrawl credits (Issue #78)
- [ ] Add 'Clear Digest Tracking' to TUI for easy job resending (Issue #137)

### Backlog (tracked in GitHub Issues)
- Issue #9: Generic company list scraper enhancements
- Issue #29: End-to-end testing with multiple profiles
- Issue #79: Enhanced statistics tracking for scraper observability
- Issue #168: Skip known-stale jobs during scraping
- Issue #180: Performance monitoring dashboard for company scraping costs
- Issue #185: Document multi-profile scoring optimization strategy
- Issue #193: Company Location Management in TUI

## Completed This Session (Feb 2026)

### Issue Triage
- [x] Closed #4 (configurable weights — superseded by profiles/*.json)
- [x] Closed #28 (cron update — superseded by --all-inboxes architecture)
- [x] Closed #50 (recruiter attribution — won't fix; disabled 4 zero-value companies)
- [x] Closed #83 (Firecrawl automation — fully implemented)
- [x] Closed #93, #94 (LLM validation/deployment — superseded, in production)
- [x] Updated #78: re-scoped to company-level credit optimization

### Overnight Agent (PRs #286–289)
- [x] Reduce testdevjobs scraper complexity 24→5 (PR #286)
- [x] Reduce health checker complexity 16→14 (PR #287)
- [x] Reduce TUI digest selection complexity 22→13 (PR #288)
- [x] Fix regex S5869 in email_company_extractor.py (PR #289)

### CI / Dev Workflow
- [x] Draft PR workflow: push branch + open draft PR immediately, mark ready when done (PR #284)
- [x] Skip SonarCloud on draft PRs — local SonarLint covers quality during active development
- [x] Add `ready_for_review` trigger so SonarCloud fires automatically on `gh pr ready`
- [x] Add concurrency cancellation to CI and security workflows (new push cancels stale run)

### Code Quality & Coverage
- [x] Fix database schema migration order — 3 indexes moved after ALTER TABLE guards (PR #282)
- [x] Add ALTER TABLE guards for 7 post-initial columns (PR #282)
- [x] Add `TestDatabaseIncrementalMigration` tests to cover ALTER TABLE branches (PR #282)
- [x] **Result**: 263 test failures → 0, coverage 67% → 80% ✅

### TUI Refactoring
- [x] Reduce `main()` cognitive complexity 30→8 via three helper functions (PR #281)
- [x] Extract `PYTHON_EXECUTABLE` constant (PR #280, fixes #277)

## Completed (Jan 2026)
- [x] Fix test import errors — 1597 tests passing, 80% coverage ✅

## Completed (Nov 2025)
- [x] Firecrawl integration for robotics priority companies (PR #71)
- [x] Company scraper with auto-disable, budget tracking, rate limiting
- [x] Automated weekly company monitoring system
