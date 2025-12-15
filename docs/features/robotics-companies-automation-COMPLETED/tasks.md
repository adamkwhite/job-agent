# Tasks: Automated Robotics Company Monitoring

## Relevant Files

### New Files to Create
- `src/utils/career_url_parser.py` - URL parsing utility to extract career page URLs from job posting URLs
- `src/utils/company_extractor.py` - Extract unique companies and job counts from robotics spreadsheet
- `scripts/extract_robotics_companies.py` - Main script to extract top 20 companies and populate database
- `src/monitoring/company_performance.py` - Performance metrics and cost tracking for companies
- `tests/unit/test_career_url_parser.py` - Unit tests for URL parsing patterns
- `tests/unit/test_company_extractor.py` - Unit tests for company extraction logic
- `tests/integration/test_robotics_automation.py` - Integration tests for full workflow

### Existing Files to Modify
- `src/notifier.py` - Add `send_scraping_failure_alert()` method for email notifications
- `src/database.py` - Add methods for failure tracking and performance metrics queries
- `src/jobs/company_scraper.py` - Review failure handling logic (may need updates)
- `docs/features/robotics-companies-automation-PLANNED/prd.md` - Update with implementation learnings

### Configuration Files
- `config/robotics-companies-settings.json` - Company selection criteria and budget limits (new)

### Notes
- URL parsing patterns should support Workday, Greenhouse, Lever, and generic ATS platforms
- Test with existing cached Firecrawl data before live scraping
- Maintain backward compatibility with existing company monitoring (27 companies)
- Follow project's pytest testing patterns (see existing `tests/unit/test_company_service.py`)

## Tasks

- [ ] 1.0 Create Career URL Parser Infrastructure
  - [ ] 1.1 Create `src/utils/career_url_parser.py` with `CareerURLParser` class
  - [ ] 1.2 Implement Workday URL pattern parsing (extract base URL before `/job/` path)
  - [ ] 1.3 Implement Greenhouse URL pattern parsing (extract domain + base path before `/jobs/`)
  - [ ] 1.4 Implement Lever URL pattern parsing (extract domain + company path before `/jobs/`)
  - [ ] 1.5 Implement generic URL pattern parsing (fallback to domain + `/careers` or `/jobs`)
  - [ ] 1.6 Add `parse()` method that returns career URL or None if unparseable
  - [ ] 1.7 Add `validate_url()` method to check if URL is accessible (optional HEAD request)
  - [ ] 1.8 Create `tests/unit/test_career_url_parser.py` with 80%+ coverage
  - [ ] 1.9 Test parser on sample job URLs from robotics spreadsheet (10+ examples)
  - [ ] 1.10 Document URL parsing patterns in code comments with examples

- [ ] 2.0 Implement Company Extraction Script
  - [ ] 2.1 Create `src/utils/company_extractor.py` with `CompanyExtractor` class
  - [ ] 2.2 Implement `fetch_spreadsheet()` to download robotics Google Sheets CSV
  - [ ] 2.3 Implement `count_jobs_per_company()` to build company → job count mapping
  - [ ] 2.4 Implement `get_top_companies()` to return top N companies by job volume
  - [ ] 2.5 Implement `derive_career_urls()` using CareerURLParser for each company
  - [ ] 2.6 Add filtering to exclude companies already in database (check existing companies table)
  - [ ] 2.7 Create `scripts/extract_robotics_companies.py` main script with CLI arguments
  - [ ] 2.8 Add `--limit N` argument to control how many companies to extract (default: 20)
  - [ ] 2.9 Add `--dry-run` flag to preview results without database insertion
  - [ ] 2.10 Implement `populate_companies_table()` to batch insert companies into database
  - [ ] 2.11 Add transaction handling for atomic database operations (all-or-nothing)
  - [ ] 2.12 Add logging for each step (fetching, parsing, inserting) with timestamps
  - [ ] 2.13 Handle manual URL lookup workflow: output list of companies needing manual URLs
  - [ ] 2.14 Add `--manual-urls` argument to accept JSON file with manually looked-up URLs
  - [ ] 2.15 Create `tests/unit/test_company_extractor.py` with mocked CSV data
  - [ ] 2.16 Test dry-run mode to ensure no database changes occur
  - [ ] 2.17 Test with actual robotics spreadsheet to verify top 20 companies extraction
  - [ ] 2.18 Document script usage in docstring with examples (`--help` output)

- [ ] 3.0 Implement Performance Monitoring and Cost Tracking
  - [ ] 3.1 Create `src/monitoring/company_performance.py` with `CompanyPerformanceTracker` class
  - [ ] 3.2 Implement `calculate_company_metrics()` to compute jobs/scrapes/cost for a company
  - [ ] 3.3 Add query for jobs discovered per company in last N days (parameterizable)
  - [ ] 3.4 Add query for Firecrawl scrapes attempted/successful for company
  - [ ] 3.5 Implement cost calculation: estimate Firecrawl credits used per company (1 credit/scrape)
  - [ ] 3.6 Implement `cost_per_job` metric calculation (total cost / unique jobs)
  - [ ] 3.7 Add `get_low_performers()` method to identify companies with cost > $0.50/job
  - [ ] 3.8 Implement `generate_monthly_report()` for all companies with metrics summary
  - [ ] 3.9 Add database methods to `src/database.py` for performance queries
  - [ ] 3.10 Create `get_company_scrape_history()` query (last_checked timestamps, failures)
  - [ ] 3.11 Create `get_company_job_stats()` query (total jobs, date range filtering)
  - [ ] 3.12 Add logging for performance calculations with structured output (JSON)
  - [ ] 3.13 Test metrics calculation with sample data (mock 20 companies, 100 jobs)
  - [ ] 3.14 Create `scripts/generate_company_report.py` CLI tool to run reports on-demand
  - [ ] 3.15 Add monthly report output format (CSV and/or JSON)
  - [ ] 3.16 Document metrics definitions and calculation formulas in code

- [ ] 4.0 Add Failure Handling and Email Notifications
  - [ ] 4.1 Add `failure_count` column to companies table (default: 0)
  - [ ] 4.2 Add `last_failure_date` column to companies table for tracking
  - [ ] 4.3 Update `src/database.py` with schema migration for new columns
  - [ ] 4.4 Implement `increment_failure_count()` method in database class
  - [ ] 4.5 Implement `reset_failure_count()` method (called on successful scrape)
  - [ ] 4.6 Implement `disable_company()` method to set active=0 when failure_count >= 5
  - [ ] 4.7 Modify `src/jobs/company_scraper.py` to call increment_failure_count() on errors
  - [ ] 4.8 Modify `src/jobs/company_scraper.py` to call reset_failure_count() on success
  - [ ] 4.9 Add check in company_scraper to auto-disable after 5 failures
  - [ ] 4.10 Extend `src/notifier.py` with `send_scraping_failure_alert()` method
  - [ ] 4.11 Implement email template for scraping failures (company, URL, error, timestamp)
  - [ ] 4.12 Add email notification call in company_scraper on immediate failures
  - [ ] 4.13 Use existing SMTP configuration from .env (SMTP_HOST, SMTP_PORT, etc.)
  - [ ] 4.14 Add structured logging for all failure events (company, error type, stack trace)
  - [ ] 4.15 Test failure handling with mock scraping errors (simulate 5 consecutive failures)
  - [ ] 4.16 Test email notification delivery (send test email to verify SMTP works)
  - [ ] 4.17 Add database query to get recently disabled companies (active=0, failure_count >= 5)
  - [ ] 4.18 Document failure handling workflow in code comments

- [ ] 5.0 Integration Testing and Documentation
  - [ ] 5.1 Create `tests/integration/test_robotics_automation.py` for end-to-end workflow
  - [ ] 5.2 Test full pipeline: fetch spreadsheet → extract companies → populate DB
  - [ ] 5.3 Test URL parsing success rate (should be ≥80% for top 20 companies)
  - [ ] 5.4 Test deduplication: ensure companies already in DB are skipped
  - [ ] 5.5 Test dry-run mode doesn't modify database
  - [ ] 5.6 Test manual URL workflow: extract unparseable companies, accept manual JSON
  - [ ] 5.7 Run `scripts/extract_robotics_companies.py --dry-run` on production data
  - [ ] 5.8 Manually verify top 20 companies list matches expectations
  - [ ] 5.9 Manually look up career URLs for any companies with parsing failures
  - [ ] 5.10 Create `config/manual-company-urls.json` with manually verified URLs
  - [ ] 5.11 Run `scripts/extract_robotics_companies.py` with actual database insertion
  - [ ] 5.12 Verify 20 companies inserted into companies table with active=1
  - [ ] 5.13 Run `unified_weekly_scraper.py --companies-only` to test Firecrawl scraping
  - [ ] 5.14 Monitor first scraping cycle logs for errors
  - [ ] 5.15 Verify jobs extracted and scored for new companies
  - [ ] 5.16 Test failure handling by simulating scraping error (manual trigger)
  - [ ] 5.17 Verify email notification received for test failure
  - [ ] 5.18 Generate first monthly performance report and review metrics
  - [ ] 5.19 Update PRD with actual implementation learnings and metrics
  - [ ] 5.20 Document script usage in project CLAUDE.md (add to automation section)
  - [ ] 5.21 Create troubleshooting guide for common issues (URL parsing failures, SMTP errors)
  - [ ] 5.22 Add example commands to CLAUDE.md for running extraction script
  - [ ] 5.23 Update weekly scraper cron job documentation to include new companies

## Implementation Notes

### URL Parsing Patterns Reference

```python
# Workday example
# Input:  https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics/job/Waltham-MA/12345
# Output: https://bostondynamics.wd1.myworkdayjobs.com/Boston_Dynamics

# Greenhouse example
# Input:  https://job-boards.greenhouse.io/figureai/jobs/4123456
# Output: https://job-boards.greenhouse.io/figureai

# Lever example
# Input:  https://jobs.lever.co/kuka/abc-123-xyz
# Output: https://jobs.lever.co/kuka
```

### Database Schema Changes

```sql
-- Add to companies table for failure tracking
ALTER TABLE companies ADD COLUMN failure_count INTEGER DEFAULT 0;
ALTER TABLE companies ADD COLUMN last_failure_date TEXT;
```

### Testing Strategy

1. **Unit Tests**: Focus on URL parsing patterns and company extraction logic
2. **Integration Tests**: Test full workflow with mocked spreadsheet data
3. **Manual Testing**: Run on actual robotics spreadsheet with dry-run first
4. **Production Validation**: Monitor first 1-2 scraping cycles closely

### Success Validation Checklist

After implementation, verify:
- [ ] 20 companies added to database
- [ ] All companies have active=1 status
- [ ] Career URLs are valid and accessible
- [ ] URL parsing achieved ≥80% success rate
- [ ] Manual URLs documented in config file
- [ ] First Firecrawl scraping cycle succeeds for ≥16/20 companies (80%)
- [ ] Performance metrics show reasonable cost per job
- [ ] Failure handling works (test with simulated error)
- [ ] Email notifications delivered successfully
- [ ] No disruption to existing 27 companies in monitoring

### Budget Monitoring

**Firecrawl Cost Estimation:**
- Current: 27 companies at ~50 credits/week = ~$20/month
- After automation: 47 companies at ~87 credits/week = ~$35/month
- Increase: ~$15/month
- Monitor weekly and disable low performers if needed

**Performance Targets:**
- Cost per unique job: ≤$0.50
- Scraping success rate: ≥80%
- Jobs discovered per week: +10% increase
