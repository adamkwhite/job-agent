# Weekly Automation Workflow

## Overview

The job agent runs weekly automation to scrape jobs from three sources:
1. **Email-based sources** (LinkedIn, Supra, Built In, etc.) - Fully automated
2. **Robotics/Deeptech Google Sheet** (1,092 jobs) - Fully automated
3. **Wes's 26 Companies** - Semi-automated (requires Claude Code assistance)

## Schedule

**Every Monday at 9:00 AM** (via cron job)

## What Runs Automatically

### Unified Weekly Scraper
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py
```

This script:
1. Processes last 100 emails for new job alerts
2. Scrapes robotics/deeptech sheet for leadership roles (70+ score)
3. Identifies the 26 companies that need scraping
4. **Outputs list of companies for manual Firecrawl scraping**

### What Happens Next

**Emails & Robotics**: Jobs are automatically scored, stored, and notifications sent for A/B grade jobs (80+).

**Company Monitoring**: Requires Claude Code to:
1. Call Firecrawl MCP tool for each company's career page
2. Process markdown results
3. Store leadership jobs in database

## Manual Company Scraping Workflow

### Step 1: Get Scraping Plan

```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/scrape_companies_with_firecrawl.py --plan-only
```

This outputs:
- List of 26 companies to scrape
- Career page URL for each
- MCP tool command to use

### Step 2: Scrape Companies (Claude Code)

For each company, Claude Code calls:

```python
mcp__firecrawl-mcp__firecrawl_scrape(
    url="<company_careers_url>",
    formats=["markdown"]
)
```

### Step 3: Process Results (Claude Code)

```python
from src.jobs.scrape_companies_with_firecrawl import CompanyScraperWithFirecrawl

scraper = CompanyScraperWithFirecrawl()
stats = scraper.process_company_markdown(
    company_name="Company Name",
    careers_url="https://company.com/careers",
    markdown_content=firecrawl_result["markdown"],
    min_score=50,
    notify_threshold=80
)
```

This will:
- Extract job listings from markdown
- Filter for leadership roles only
- Score each job (0-115 points)
- Store jobs scoring 50+ (D grade or better)
- Send notifications for 80+ jobs (A/B grade)
- Skip duplicates

## Weekly Digest

After scraping completes, send the weekly digest:

```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_digest_to_wes.py
```

This sends email to Wesley with:
- All unsent jobs from database
- Top matches highlighted (80+ score)
- Interactive HTML attachment with filters
- Jobs automatically marked as sent

## Database Tracking

The system tracks:
- `notified_at`: Real-time SMS/email notifications sent during scraping
- `digest_sent_at`: Weekly digest emails sent to Wesley
- Jobs only appear in digest once (prevents duplicates)

## Current Status

**Fully Automated**:
- ✅ Email processing (LinkedIn, Supra, Built In, etc.)
- ✅ Robotics sheet scraping (1,092 jobs weekly)
- ✅ Job scoring and storage
- ✅ Real-time notifications (A/B grade)
- ✅ Weekly digest emails

**Semi-Automated** (requires Claude Code):
- ⚠️ Company career page scraping (26 companies)
- Requires Firecrawl MCP tool calls
- Cannot be run from Python directly

## Why Company Scraping Requires Manual Steps

**Technical Limitation**: The Firecrawl MCP tool can only be called by Claude Code, not from Python subprocess.

**Solutions Considered**:
1. ❌ Call `claude mcp` via subprocess - fails (no `claude` command in PATH)
2. ❌ Direct HTTP API calls to Firecrawl - requires API key management
3. ✅ **Current approach**: Claude Code assists with weekly scraping

**Benefits of Current Approach**:
- Reliable scraping of JavaScript-heavy career pages
- Manual oversight ensures quality
- Can handle different page formats
- No API key management needed

## Future Improvements

### Option 1: Full Automation via Firecrawl API
- Set up Firecrawl API key
- Call Firecrawl REST API directly from Python
- Removes need for Claude Code assistance

### Option 2: Alternative Scrapers
- Implement Playwright-based scraper
- Use BeautifulSoup for static pages
- May struggle with JavaScript-heavy sites

### Option 3: Hybrid Approach (Current)
- Keep current semi-automated workflow
- Document process clearly
- Runs once per week, low maintenance burden

## Weekly Checklist

**Automated Steps** (Monday 9am via cron):
- [x] Process 100 latest emails
- [x] Scrape robotics sheet (1,092 jobs)
- [x] Filter for leadership roles
- [x] Score and store jobs
- [x] Send real-time notifications (80+ jobs)

**Manual Steps** (Claude Code assists):
- [ ] Run scraping plan: `scrape_companies_with_firecrawl.py --plan-only`
- [ ] For each company: Call Firecrawl MCP tool
- [ ] Process markdown results
- [ ] Store leadership jobs (50+ score)

**Final Step**:
- [ ] Send weekly digest: `send_digest_to_wes.py`
- [ ] Verify digest sent to wesvanooyen@gmail.com

## Monitoring

**Check cron logs**:
```bash
tail -f logs/unified_weekly_scraper.log
```

**Check database stats**:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python -c "
from src.database import JobDatabase
db = JobDatabase()
stats = db.get_stats()
print(f'Total jobs: {stats[\"total_jobs\"]}')
print(f'By source: {stats[\"jobs_by_source\"]}')
"
```

**Check for unsent jobs**:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python -c "
from src.database import JobDatabase
db = JobDatabase()
unsent = db.get_jobs_for_digest(limit=100)
print(f'Unsent jobs: {len(unsent)}')
"
```

## Summary

The job agent provides **weekly automated job discovery** across three major sources, with intelligent scoring, deduplication, and multi-channel notifications. The only manual step is company career page scraping, which requires Claude Code assistance once per week.

**Current Performance**:
- 84 jobs in database
- 26 companies monitored weekly
- 5 A/B grade matches in last digest
- 100% deduplication rate
- Weekly digest automatically sent
