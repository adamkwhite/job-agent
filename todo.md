# TODO

## Open Features
- [ ] Company Location Management in TUI (Issue #193)
## Open Backlog (Low Priority)
- Issue #79: Enhanced statistics tracking for scraper observability

## Recently Completed (Mar 13, 2026)
- [x] Migrate cron jobs from WSL to Hostinger VPS (PR #381)
  - VPS: Ubuntu 25.10, `ssh hostinger`, timezone America/Toronto
  - Scraper at 6am ET, backup at 3am ET
  - Deploy script: `scripts/deploy_to_vps.sh`
  - Fixed lxml dependency conflict (6.0.2 → >=5.3,<6)
  - Tracked `backup_database.sh` (was excluded by global gitignore)
- [x] WSL auto-start via Windows Task Scheduler (kept as convenience)

## Previously Completed (Mar 12, 2026)
- [x] Company performance dashboard in TUI (Issue #180, PR #379)
  - Database aggregation methods for scraping metrics
  - Top/bottom performer tables with failure rates, time window switching
- [x] RLS Job Board scraper — Rands Leadership Slack (PR #377)
  - JSON API integration, field mapping, multi-profile scoring
  - Integrated into weekly unified scraper pipeline
- [x] Shared scraper utilities extracted to `utils/db_retry.py`
  - `retry_db_operation()`, `store_single_job()`, `score_single_job()`, `print_profile_score_summary()`
  - Protocol types for structural typing without inheritance
  - Eliminated cross-scraper code duplication (SonarCloud 5.7% → 0%)
- [x] Simplified backup to daily-only retention, 7-day keep (PR #376)
- [x] Cleaned up: test profile, stale logs, hallucinated URLs, Figure AI re-enabled
- [x] RLS Job Board PRD (local doc, not public GH issue)

## Previously Completed (Mar 9, 2026)
- [x] TUI onboarding wizard with PromptKit DI (Issue #349, PR #368)
- [x] Daily scraping + frequency-aware digests (Issue #3)
  - Cron: daily 6am full scrape, daily digests always, weekly digests on Mondays
  - `--frequency daily|weekly` CLI flag, per-profile max_age_days (daily=2, weekly=7)
- [x] Remove job aggregator sites from company monitoring — S.i. Systems deleted (Issue #363)
- [x] Fix inline link extraction for Ashby-hosted career pages (PR #364)
  - 1Password, Harvey, Wealthsimple, Boston Dynamics, Trexo Robotics affected
  - Cleaned up 16 bad DB entries; resent corrected digests to Mark B + Mark Lennox

## Previously Completed (Mar 8, 2026)
- [x] Switch default LLM to Gemini 2.5 Flash, $5/mo budget (Issue #345, PR #353)
- [x] TUI extraction metrics dashboard (Issue #118, PR #354)
- [x] Unified company review — merged discovered + failures flows (PR #358)
- [x] Company dedup with fuzzy name matching + junk name filter (PR #359)
- [x] Human-readable LLM failure reasons in TUI (PR #360)
- [x] Show careers URL in company review table (PR #361)
- [x] Inline company actions — a#/d#/r# from list view (PR #362)
- [x] Fixed pytest collection errors in tests/exploration/ (PR #358)
- [x] Multiple TUI bug fixes: column name, source email, failure details (PRs #355-357)

## Previously Completed (Mar 7-8, 2026)
- [x] Interactive profile onboarding script (Issue #346, PR #348)
- [x] New profile: Mark Lennox — Sr. Director/VP, SaaS generalist, North Toronto
- [x] Cron updated: Monday 6am + automated digest sending enabled (PR #347)

## Previously Completed (Mar 7, 2026)
- [x] Firecrawl fallback when primary scraper returns 0 jobs (Issue #342)
- [x] Populate extraction_metrics table with per-run scraping stats (Issue #343)
- [x] Crawl4AI career scraper backend (PR #338)
- [x] Fix missing role categories + wire scraper_backend in multi-inbox mode (PR #341)
- [x] Skip no-commit-to-branch hook in CI (PR #340)

## Previously Completed (Mar 3, 2026)
- [x] Add PlaywrightCareerScraper as default scraping backend (PR #337)
- [x] Extract BaseCareerScraper from FirecrawlCareerScraper (PR #336)
- [x] New profile: Mark Biciunas — Director/VP eng leadership, SaaS/EdTech, B-grade digest
- [x] Backfilled scores + sent first digest to Mark

## Previously Completed (Feb 28, 2026)
- [x] Fix website extraction accuracy in company list scraper (PR #331, Issue #319)
- [x] Add batch processing + DB storage to company list scraper (PR #332, Issue #317)
- [x] Add monitoring and alerting for weekly scraper failures (PR #333)
- [x] Add structured logging to company list scraper (PR #334, Issue #318)
- [x] Update README to match current architecture (PR #334)

## Previously Completed
- [x] All SonarCloud complexity/quality issues resolved (PRs #304-308, #321-327, #330)
- [x] Multi-profile scoring architecture (Issue #184)
- [x] Job description enrichment for scoring accuracy (Issue #316, PRs #326, #328)
- [x] Draft PR workflow with SonarCloud integration (PR #284)
- [x] Database migration guards and test coverage to 80% (PR #282)
- [x] Firecrawl company monitoring system (PR #71)
