# Job Agent System - How It Works

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                      JOB SOURCES (Input)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. EMAIL SOURCES (Automated)                                   │
│     ├─ LinkedIn job alerts                                      │
│     ├─ Supra Product Leadership newsletter                      │
│     ├─ Built In job alerts                                      │
│     ├─ F6S, Artemis, WorkInTech, etc.                          │
│     └─ Status: ✅ WORKING - Auto-scraped from email            │
│                                                                 │
│  2. ROBOTICS SHEET (Automated)                                  │
│     ├─ Google Sheets with 1,092 robotics/deeptech jobs        │
│     └─ Status: ✅ WORKING - Auto-scraped weekly                │
│                                                                 │
│  3. WES'S 26 COMPANIES (Manual/Semi-automated)                  │
│     ├─ CSV list of 26 companies (Miovision, Stryker, etc.)    │
│     ├─ Stored in database (companies table)                    │
│     └─ Status: ⚠️  READY BUT NOT AUTOMATED                     │
│         - Requires manual Firecrawl MCP calls                   │
│         - Jobs found but NOT stored in database yet             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                              ↓

┌─────────────────────────────────────────────────────────────────┐
│                   PROCESSING (What Happens)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Unified Weekly Scraper runs:                                   │
│                                                                 │
│  1. Email Processor → Parses emails → Extracts jobs            │
│  2. Robotics Scraper → Scrapes Google Sheet → Filters jobs     │
│  3. Company Scraper → Shows URLs → Says "ready for Firecrawl"  │
│                                                                 │
│  Then for each job:                                             │
│  ├─ Score it (0-115 points)                                     │
│  ├─ Assign grade (A/B/C/D/F)                                    │
│  ├─ Check for duplicates (by hash)                              │
│  └─ Store in database if new                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                              ↓

┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (Storage)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  jobs.db (SQLite database)                                      │
│                                                                 │
│  Currently contains: 70 jobs                                    │
│  ├─ 23 from LinkedIn                                            │
│  ├─ 22 from Supra                                               │
│  ├─ 9 from Built In                                             │
│  ├─ 7 from Recruiters                                           │
│  ├─ 5 from Robotics Sheet                                       │
│  ├─ 4 from WorkInTech                                           │
│  └─ 0 from Wes's 26 companies ⚠️                                │
│                                                                 │
│  Each job has:                                                  │
│  ├─ Title, company, location, link                              │
│  ├─ fit_score, fit_grade                                        │
│  ├─ notified_at (for real-time alerts)                          │
│  └─ digest_sent_at (for weekly digest)                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                              ↓

┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT (What Wes Gets)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. REAL-TIME ALERTS (During scraping)                          │
│     ├─ When: Job scores 80+ (A/B grade)                         │
│     ├─ How: SMS + Email immediately                             │
│     └─ Tracked by: notified_at field                            │
│                                                                 │
│  2. WEEKLY DIGEST (Manual/scheduled)                            │
│     ├─ When: You run send_digest_to_wes.py                      │
│     ├─ What: All unsent jobs from database                      │
│     ├─ Includes: HTML email + jobs.html attachment              │
│     └─ Tracked by: digest_sent_at field                         │
│                                                                 │
│  3. COMPANY DIGEST (Separate - not in database!)                │
│     ├─ When: We manually scraped Wes's companies                │
│     ├─ What: 3 jobs scoring 50+ from 26 companies               │
│     ├─ File: company_digest.html                                │
│     └─ ⚠️  These 14 jobs NOT in database!                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## The Problem You're Seeing

**Company monitoring is set up but not integrated:**

1. ✅ CSV file exists with 26 companies
2. ✅ Companies imported into database (companies table)
3. ✅ Company scraper written
4. ✅ Unified scraper includes company monitoring
5. ⚠️  **BUT**: Company jobs require manual Firecrawl MCP calls
6. ⚠️  **AND**: We scraped them manually earlier but didn't store in database
7. ❌ **RESULT**: Those 14 company jobs only exist in company_digest.html

## Simple Summary

**What's working automatically:**
- ✅ Email jobs → Database → Weekly digest
- ✅ Robotics sheet jobs → Database → Weekly digest

**What's NOT working automatically:**
- ❌ Wes's 26 companies → Manual Firecrawl → **NOT in database** → Separate email

**The disconnect:**
When we ran the unified scraper today, it processed emails and robotics, but for companies it just said "ready for Firecrawl" and didn't actually scrape or store anything.

The 14 jobs from Wes's companies were found in an earlier manual scraping session and sent in a separate email (`company_digest.html`) but never stored in the database.
