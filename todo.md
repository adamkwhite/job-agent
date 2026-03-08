# TODO

## Open Features
- [ ] Daily digest option (Issue #3)
- [ ] Company Location Management in TUI (Issue #193)

## Open Backlog (Low Priority)
- Issue #79: Enhanced statistics tracking for scraper observability
- Issue #118: TUI metrics dashboard (LLM vs Regex extraction)
- Issue #180: Performance monitoring dashboard for company scraping costs

## In Progress
- [ ] LLM model comparison for cost reduction (Issue #345) — `--llm-model` CLI flag implemented
- [ ] TUI onboarding wizard (Issue #349)

## Recently Completed (Mar 8, 2026)
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
