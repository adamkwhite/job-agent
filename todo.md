# TODO

## High Priority

### Testing Infrastructure
- [ ] Fix test import errors - tests are failing to import from `src` module
  - Error: `ModuleNotFoundError: No module named 'src'`
  - All 5 test files affected: test_builtin_parser.py, test_jobbank_parser.py, test_processor_v2.py, test_recruiter_parser.py, test_workintech_parser.py
  - PYTHONPATH is set but tests still fail - may need pytest.ini configuration or conftest.py
  - Blocking: Cannot verify test coverage or run quality checks

### Company Scraping Automation
- [ ] Consider full automation options for company scraping:
  - Option 1: Set up Firecrawl API key and call REST API directly from Python
  - Option 2: Implement Playwright-based scraper for JavaScript-heavy sites
  - Option 3: Keep current semi-automated workflow (minimal maintenance burden)
- [ ] Document weekly company scraping workflow for user/maintainer
- [ ] Test full end-to-end scraping of all 26 companies (currently tested with 2)

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
