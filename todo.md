# TODO

## High Priority

### Monitoring & Observability
- [x] Set up monitoring for cron job failures (PR #333)
- [x] Add email alerts if weekly scraper fails (PR #333)

### Code Quality (SonarCloud)
- [x] ~~Overnight batch A: trivial fixes (S3626, S125, S1481)~~ — all resolved
- [x] ~~Overnight batch B: company_scraper.py unused params (S1172)~~ — all resolved
- [x] **Issue #294: All complexity reductions complete** — 5 files reduced, PRs #304-308 merged
- [x] Issue #295: feedback_parser.py regex — S5869/S6019 fixed (PR #325)
- [x] S1192 string duplication in tui.py — 6 constants extracted (PR #321)
- [x] All S3776 complexity issues resolved — tui.py, firecrawl_career_scraper.py, rescore_jobs.py, job_validator.py, send_profile_digest.py (PRs #322-324, #327, #330)

## Medium Priority

### Features
- [ ] Daily digest option (Issue #3)
- [x] Selective job description enrichment for improved scoring accuracy (Issue #316, PRs #326, #328)
- [ ] Add 'Clear Digest Tracking' to TUI for easy job resending (Issue #137)

### Backlog (tracked in GitHub Issues)
- ~~Issue #317: Batch processing + DB storage for company list scraper CLI~~ (PR #332)
- Issue #29: End-to-end testing with multiple profiles
- Issue #79: Enhanced statistics tracking for scraper observability
- Issue #168: Skip known-stale jobs during scraping
- Issue #180: Performance monitoring dashboard for company scraping costs
- Issue #185: Document multi-profile scoring optimization strategy
- Issue #193: Company Location Management in TUI
- ~~Issue #319: Improve website extraction accuracy in company list scraper~~ (PR #331)

## Completed This Session (Feb 2026)

### Issue #294 - Complexity Reductions (Feb 19-20, 2026)
- [x] Refactor 5 files with complexity 15-19 → 5-10
- [x] Create comprehensive complexity guidelines: `docs/development/COMPLEXITY_GUIDELINES.md`
- [x] Update CLAUDE.md with complexity policy and guidelines reference
- [x] Document extract-method pattern with real examples from refactoring
- [x] Establish 50-line rule as leading indicator for complexity
- [x] **Result**: All PRs passing CI, ready for merge ✅

**PRs Created:**
- PR #304: database.py (17→5) - **Merged** ✅
- PR #305: firecrawl_career_scraper.py (16→≤15) - **Merged** ✅
- PR #306: linkedin_parser.py (17→≤15) - **Merged** ✅
- PR #307: testdevjobs_scraper.py (19→10) - **Merged** ✅
- PR #308: wellfound_parser.py (19→8) + guidelines docs - **Merged** ✅

### Issue Triage
- [x] Closed #9 (company list scraper umbrella — 6/11 done, remaining → #317, #318, #319)
- [x] Closed #4 (configurable weights — superseded by profiles/*.json)
- [x] Closed #28 (cron update — superseded by --all-inboxes architecture)
- [x] Closed #50 (recruiter attribution — won't fix; disabled 4 zero-value companies)
- [x] Closed #83 (Firecrawl automation — fully implemented)
- [x] Closed #93, #94 (LLM validation/deployment — superseded, in production)
- [x] Updated #78: re-scoped to company-level credit optimization
- [x] Closed #78 (two-tier scoring — incorrect Firecrawl assumption) → replaced by #316

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
