# Ministry of Testing Integration for Mario

## Overview
Built a web scraper for Ministry of Testing job board to solve Mario's empty digest problem.

## Problem Statement
- Mario's current job sources have **0.99% success rate** (7 qualifying jobs out of 710)
- Last 7 days: **0 jobs** meeting digest criteria
- Root cause: Sources focused on robotics/product leadership, not QA/testing

## Solution: Ministry of Testing Scraper

### What We Built

**1. `src/scrapers/ministry_of_testing_scraper.py`**
- Scrapes https://www.ministryoftesting.com/jobs (138 jobs currently)
- Filters by location (Canada, Remote, Toronto, US)
- Supports pagination (up to 3 pages = ~75 jobs)
- Extracts: title, company, location, link, posted date
- Returns `OpportunityData` objects ready for database storage

**2. `scripts/test_ministry_scraper.py`**
- Test script showing integration example
- Documentation on how to add to weekly scraper
- Sample code for scoring and storage

**3. `docs/mario-setup-checklist.md`**
- Quick-start guide for Mario to set up LinkedIn/Indeed alerts
- 30-minute action plan
- Expected outcomes

**4. `docs/mario-qa-job-sources.md`**
- Comprehensive guide to 7 QA job sources
- Setup instructions for each
- Expected impact analysis

## How It Works

```python
from scrapers.ministry_of_testing_scraper import MinistryOfTestingScraper

# Initialize with Firecrawl MCP client
scraper = MinistryOfTestingScraper(firecrawl_client=firecrawl)

# Scrape Canada/Remote jobs
jobs = scraper.scrape_jobs(
    target_locations=['Canada', 'Remote', 'Toronto'],
    max_pages=3  # ~75 jobs
)

# Returns list of OpportunityData objects
# Each contains: title, company, location, link, posted_date
```

## Current Ministry of Testing Jobs (Jan 16, 2026)

From our test scrape:
- **138 total jobs** on the board
- Jobs posted: Today (Jan 16) to ~2 weeks ago
- Locations: Canada, US, UK, Europe, India, Remote
- Roles: QA Analyst, Test Engineer, Automation Engineer, Test Lead, QA Manager

**Example jobs for Mario:**
- ✅ **Quality Assurance (QA) Analyst** - Toronto, Ontario (posted today!)
- ✅ **AI Test Automation Engineer** - London, UK / Remote
- ✅ **Test Lead** - London, UK
- ✅ **QA Automation Engineer** - United States / Remote
- ✅ **Senior Software Quality Assurance Engineer** - Austin, TX (Remote)

## Integration Steps

### Option A: Quick Integration (Manual for now)
1. Run Firecrawl scrape manually using MCP tool
2. Copy jobs to database manually
3. Run Mario's digest
4. **Timeline**: 30 minutes, can do today

### Option B: Full Automation (Recommended)
1. Create Firecrawl MCP client wrapper class
2. Add Ministry of Testing scraper to weekly_unified_scraper.py
3. Configure to run weekly (or daily for Mario)
4. Automatic scoring and digest integration
5. **Timeline**: 2-3 hours development

## Expected Impact

### Before (Current State)
- 710 jobs scored for Mario all-time
- 7 qualifying jobs (0.99% success rate)
- 0 jobs in last 7 days
- Empty digests

### After (With Ministry of Testing)
- **Weekly scrape**: ~15-25 Canada/Remote jobs from Ministry of Testing
- **Plus**: LinkedIn/Indeed alerts (~40-70 jobs/week when Mario sets up)
- **Estimated qualification rate**: 5-10% for QA-specific sources
- **Expected weekly matches**: 3-8 jobs (vs 0 currently)
- **Non-empty digests**: Every week!

## Technical Details

### Scraper Features
- ✅ Firecrawl-powered (handles JavaScript rendering)
- ✅ Location filtering (Canada, Remote, US, custom)
- ✅ Pagination support (configurable pages)
- ✅ Date parsing (relative dates like "16 Jan")
- ✅ Company extraction (from title or location)
- ✅ Returns OpportunityData model (database-ready)

### Regex Pattern Used
```python
# Matches Ministry of Testing job format:
# [Title](URL)
# Location
# Date
pattern = r"\[([^\]]+)\]\((https://www\.ministryoftesting\.com/jobs/[^\)]+)\)\n\n([^\n]+)\n\n(\d{1,2}\s+\w+)"
```

### Location Matching Logic
- Case-insensitive substring matching
- Special handling for "Remote" (matches "CA (Remote)", "Remote", etc.)
- Filters: Canada, Toronto, Ontario, United States, Remote

## Next Actions

### For Adam (Development):
1. **Immediate** (30 min):
   - Manual test: Use Firecrawl MCP to scrape Ministry of Testing
   - Add 5-10 jobs to database manually
   - Run Mario's digest to verify scoring works

2. **This Week** (2-3 hours):
   - Create Firecrawl MCP client wrapper
   - Integrate into weekly_unified_scraper.py
   - Add Ministry of Testing to cron job
   - Test end-to-end automation

3. **Next Week**:
   - Monitor results
   - Adjust Mario's scoring if needed (might need to boost QA keywords)
   - Create parsers for LinkedIn/Indeed when Mario sets up alerts

### For Mario:
1. **Today** (30 min):
   - Set up LinkedIn job alerts (7 searches - see mario-setup-checklist.md)
   - Set up Indeed alerts (5 searches)
   - Optional: Glassdoor (3 searches)

2. **This Week**:
   - Forward job alert emails to Adam or setup mario.jobalerts@gmail.com
   - Review first digest (should have Ministry of Testing jobs!)

3. **Next Week**:
   - Provide feedback on job quality
   - Adjust alert keywords if needed

## Files Created

1. `/src/scrapers/ministry_of_testing_scraper.py` - Main scraper class
2. `/scripts/test_ministry_scraper.py` - Test/integration script
3. `/docs/mario-setup-checklist.md` - Quick-start guide for Mario
4. `/docs/mario-qa-job-sources.md` - Comprehensive QA job sources guide
5. `/docs/mario-ministry-of-testing-integration.md` - This file

## Success Metrics

**Week 1**:
- ✅ Ministry of Testing integrated
- ✅ 5+ jobs manually added for Mario
- ✅ Non-empty digest sent
- ✅ Mario sets up LinkedIn/Indeed alerts

**Week 2-3**:
- ✅ Weekly automation running
- ✅ Email parsers created for new sources
- ✅ 10+ jobs per week for Mario
- ✅ 2-5 B/C grade matches per week

**Week 4+**:
- ✅ Sustained weekly digests (never empty)
- ✅ Mario applying to relevant jobs
- ✅ System self-sustaining

---

**Created**: 2026-01-16
**Status**: Ready for integration
**Impact**: Solves Mario's empty digest problem
**Effort**: 30 min manual test, 2-3 hours full automation
