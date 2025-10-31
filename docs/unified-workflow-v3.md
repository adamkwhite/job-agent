# Unified Workflow V3 - Complete Redesign

## Overview

Complete redesign of the job discovery system around a **single unified workflow** for all sources.

**Before (V1/V2)**: Different paths for different sources
- Emails → Extract jobs from email content → Score → Store
- CSV → Scrape career pages → Score → Store
- Browser Extension → Manual tracking

**After (V3)**: Single path for all sources
- **All Sources** → Extract company URLs → Scrape career pages → Score → Notify → Store

## Benefits

1. **Simplicity**: One scraping path, not three
2. **Robustness**: Career pages change less than email formats
3. **Better Data**: Full job descriptions from source, not email summaries
4. **Unified**: Same scoring, same notifications, same storage for all sources
5. **Maintainability**: Fix scraping once, works for all sources

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: INGEST - Collect Company URLs                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Source: Email                                                │
│   → EmailCompanyExtractor                                    │
│   → Parse email for company name + career page URL          │
│   → Output: Company{name, careers_url, source='email'}      │
│                                                              │
│ Source: CSV (job_sources.csv)                               │
│   → CSV loader                                               │
│   → Read company list with career URLs                      │
│   → Output: Company{name, careers_url, source='csv'}        │
│                                                              │
│ Source: Browser Extension                                    │
│   → API query to companies table                            │
│   → Get recently added companies                            │
│   → Output: Company{name, careers_url, source='browser'}    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: SCRAPE - Get Jobs from Career Pages                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ For each Company:                                            │
│   → Call mcp__firecrawl-mcp__firecrawl_scrape              │
│   → Extract markdown content                                 │
│   → Parse jobs: {title, company, location, link}            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: SCORE (Basic) - With Available Data                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ For each job:                                                │
│   → Score with: title, company, location                    │
│   → 115-point system (existing scorer)                      │
│   → Assign grade: A/B/C/D/F                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: ENHANCE (Conditional) - For Promising Jobs          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ If score >= 70 (C+ grade):                                  │
│   → Fetch full JD from job.link (Firecrawl)                │
│   → Re-score with full job description                      │
│   → More accurate domain/keyword matching                   │
│                                                              │
│ Else:                                                        │
│   → Skip (not worth API cost)                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 5: NOTIFY (Real-Time) - For Excellent Jobs             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ If score >= 80 (A/B grade):                                 │
│   → Send SMS via Twilio                                     │
│   → Send email alert via Gmail                              │
│   → Mark as notified (notified_at timestamp)                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 6: STORE - Save to Database                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ For all jobs:                                                │
│   → Generate hash (title + company + link)                  │
│   → Check if exists (duplicate prevention)                  │
│   → Store with score, grade, breakdown                      │
│   → Skip if duplicate                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 7: DIGEST (Weekly) - Summary Email                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Weekly (or on-demand):                                       │
│   → Query: WHERE digest_sent_at IS NULL                     │
│   → Generate HTML email with all unsent jobs                │
│   → Send to wesvanooyen@gmail.com                           │
│   → Mark all jobs as sent (digest_sent_at timestamp)        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## File Structure

```
src/
├── models/
│   ├── __init__.py
│   └── company.py                   # Company data model (NEW)
│
├── extractors/
│   ├── __init__.py
│   └── email_company_extractor.py   # Extract company URLs from emails (NEW)
│
├── jobs/
│   └── unified_scraper_v3.py        # Main unified scraper (NEW)
│
├── agents/
│   └── job_scorer.py                # Existing scorer (unchanged)
│
├── database.py                       # Existing database (unchanged)
├── notifier.py                       # Existing notifier (unchanged)
└── imap_client.py                    # Existing IMAP client (unchanged)
```

## Usage

### Run All Sources

```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py
```

This will:
1. Process last 100 emails → extract company URLs
2. Load 26 companies from CSV
3. Query browser extension companies
4. Scrape all career pages
5. Score and store jobs
6. Send real-time notifications for 80+ jobs

### Run Specific Source

```bash
# Only emails
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py --email-only

# Only CSV
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py --csv-only --email-limit 50

# Only browser extension
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py --browser-only
```

### Custom Thresholds

```bash
# Notify at 70+ instead of 80+
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py --notify-threshold 70

# Enhanced scoring at 60+ instead of 70+
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/unified_scraper_v3.py --enhanced-threshold 60
```

## Email Company Extraction

The `EmailCompanyExtractor` handles different email formats:

### LinkedIn
- Looks for: "at Company Name" or "@ Company Name"
- Constructs: `linkedin.com/company/{slug}/jobs`

### Supra Product Leadership
- Looks for: Company names with links
- Uses provided career page URL if available

### Built In
- Parses HTML for company names in specific divs
- Constructs: `builtin.com/jobs?search={company}`

### F6S / Artemis / Generic
- Searches for career/jobs/hiring URLs in email body
- Extracts company name from domain

## Two-Pass Scoring

### Pass 1: Basic Scoring (All Jobs)
- Uses: title, company, location
- Fast: No additional API calls
- Filters out obvious mismatches

### Pass 2: Enhanced Scoring (70+ Jobs Only)
- Fetches full job description via Firecrawl
- Re-scores with complete data
- More accurate domain/keyword matching
- Cost-effective: Only for promising jobs

**Example**:
- Job A: "Engineer" at "Acme Corp", Remote → Score: 65 → **Skip enhanced scoring**
- Job B: "Director of Engineering" at "Boston Dynamics", Remote → Score: 85 → **Fetch JD** → Re-score: 92

## Duplicate Prevention

Three levels:

1. **Database Hash**: SHA256(title + company + link)
   - Same job from email + CSV → Stored once

2. **Digest Tracking**: `digest_sent_at` field
   - Job appears in digest once
   - Weekly digests never duplicate

3. **Notification Tracking**: `notified_at` field
   - Real-time alert sent once
   - No duplicate SMS/emails

## Migration from V2

**What stays the same:**
- ✅ Database schema (digest_sent_at already added)
- ✅ Job scoring system (115 points, A-F grades)
- ✅ Notification system (SMS + Email)
- ✅ Weekly digest emails
- ✅ CSV company list

**What changes:**
- ❌ Old email parsers (extract full job details)
- ✅ New email company extractor (extract company URLs only)
- ✅ New unified scraper (single workflow)
- ✅ Two-pass scoring (basic + enhanced)

**Migration path:**
1. Test V3 with `--csv-only` (26 companies)
2. Verify scraping + scoring works
3. Add email company extraction
4. Run full workflow
5. Compare results with V2
6. Deprecate old processors once confident

## Performance

**V2 Performance** (current):
- Process 100 emails: ~30 seconds
- Extract job details from emails
- Score 50-100 jobs
- Store and notify

**V3 Performance** (estimated):
- Process 100 emails: ~10 seconds (just extract company URLs)
- Scrape 26-50 career pages: ~5-10 minutes (Firecrawl)
- Score 100-500 jobs
- Enhanced scoring for ~30 jobs (70+): ~2-3 minutes
- **Total**: ~10-15 minutes weekly

**Cost savings:**
- Fewer email parser updates needed
- No wasted API calls on low-scoring jobs
- Better data = better decisions

## Testing

### Unit Tests Needed
- [ ] EmailCompanyExtractor for each email type
- [ ] CSV company loader
- [ ] Company data model
- [ ] Unified scraper (mocked Firecrawl)

### Integration Tests Needed
- [ ] End-to-end with real emails
- [ ] Firecrawl scraping with real career pages
- [ ] Two-pass scoring accuracy
- [ ] Notification delivery
- [ ] Database deduplication

### Manual Testing
- [x] CSV loading (26 companies loaded)
- [ ] Email company extraction
- [ ] Firecrawl career page scraping
- [ ] Job extraction from markdown
- [ ] Basic scoring
- [ ] Enhanced scoring (70+ jobs)
- [ ] Real-time notifications (80+ jobs)
- [ ] Weekly digest

## Next Steps

1. **Test with real Firecrawl** - Scrape 2-3 companies end-to-end
2. **Validate email extraction** - Process recent emails, verify company extraction
3. **Compare with V2** - Run both systems side-by-side
4. **Update cron job** - Switch from V2 to V3
5. **Monitor for 1 week** - Verify results match expectations
6. **Deprecate V2** - Remove old processors

## Summary

V3 represents a **fundamental architectural shift**:
- From "parse jobs from different sources differently"
- To "get company URLs, then scrape career pages uniformly"

This makes the system:
- **Simpler** - one scraping path
- **More robust** - career pages are stable
- **Better data** - full JDs from source
- **Cost-effective** - two-pass scoring
- **Maintainable** - fix once, works everywhere

The unified workflow is now ready for testing and deployment.
