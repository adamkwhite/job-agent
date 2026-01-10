# TODO

## High Priority

### Testing Infrastructure
- [x] ~~Fix test import errors~~ - **RESOLVED** (Jan 9, 2026)
  - Issue was in gitignored `tests/exploration/` directory (experimental tests)
  - Production test suite (1184 tests in `tests/unit/` and `tests/integration/`) working correctly
  - Fixed exploration tests to use `from src.*` imports instead of incorrect sys.path manipulation
  - Added pytest.importorskip to handle optional dependencies gracefully
  - **Result**: 1184 tests passing, 2 skipped, 66% coverage ✅

### Company Scraping Automation
- [x] ~~Scraper implementation~~ - **COMPLETED** (Nov 2025)
  - ✅ Firecrawl API integration via Python
  - ✅ Production: `src/jobs/weekly_unified_scraper.py` (Email + Company monitoring)
  - ✅ Company scraper: `src/jobs/company_scraper.py` + `src/scrapers/firecrawl_career_scraper.py`
  - ✅ Configuration: `config/robotics_priority_companies.json` (16 companies)
  - ✅ Features: Auto-disable after 5 failures, budget tracking, rate limiting
  - ✅ **Current workflow**: Manual execution via TUI (`./run-tui.sh`)
  - ✅ Removed: Deprecated robotics sheet scraper (Issue #174)
  - 🔧 Fixed: Removed broken cron job (pointed to non-existent wrapper script)

## Medium Priority

### Monitoring & Observability
- [ ] Set up monitoring for cron job failures
- [ ] Add email alerts if weekly scraper fails
- [ ] Create dashboard for job scraping metrics (jobs found, scored, sent)

### Code Quality
- [ ] Add tests for new company scraping functionality
  - scrape_companies_with_firecrawl.py
  - company_scraper.py
  - firecrawl_career_scraper.py
- [ ] Improve test coverage (currently at ~25%)
- [ ] Add type hints to new scraping modules

## Low Priority

### Features
- [ ] Configurable scoring weights (Issue #4)
- [ ] Daily digest option (Issue #3)
- [ ] Resume customization automation
- [ ] Interview preparation automation

### Documentation
- [ ] Add examples of successful company scraping runs
- [ ] Document Firecrawl MCP tool usage patterns
- [ ] Create troubleshooting guide for common scraping issues

## Completed This Session (Nov 29-30, 2025)
- [x] Implemented Firecrawl integration for robotics priority companies (Issues #65-#69, PR #71)
- [x] Created configuration system (`config/robotics_priority_companies.json`) with 10 priority companies
- [x] Added generic career page detection to robotics scraper
- [x] Implemented semi-automated Phase 2 Firecrawl workflow with MCP commands
- [x] Built markdown processor to extract leadership jobs from Firecrawl output
- [x] Added credit budget tracking (50/week, 200/month)
- [x] Implemented failure monitoring with 50% threshold
- [x] Added automated GitHub issue creation for scraping failures
- [x] Created 21 new tests (98% scraper coverage, 72% weekly integration)
- [x] Pushed feature branch and created PR #71
- [x] All CI/CD checks passing

## Completed This Session (Oct 30, 2025)
- [x] Implemented automated weekly company monitoring system
- [x] Created Firecrawl-based scraping workflow
- [x] Integrated company scraping with unified weekly scraper
- [x] Added digest tracking to prevent duplicate emails
- [x] Fixed CC email address in digest sender
- [x] Imported 14 leadership jobs from manual scraping
- [x] Created comprehensive workflow documentation
- [x] Tested scraping with Ascension and Miovision
