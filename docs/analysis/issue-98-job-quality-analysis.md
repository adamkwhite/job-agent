# Issue #98: Job Quality Analysis

**Date**: 2025-12-04
**Reporter**: Wes (via Adam)
**Severity**: HIGH - Losing user confidence
**Issue**: https://github.com/adamkwhite/job-agent/issues/98

## Problem Summary

Wes received 4 jobs in his digest that are no longer valid:

1. **Graymatter Robotics - Director of Hardware**
   - URL: https://jobs.ashbyhq.com/graymatter-robotics
   - Issue: "Not listed on page" - URL points to career page, not specific job
   - Scraped: Nov 21, 2025
   - Sent: Nov 30, 2025 (9 days later)
   - Source: robotics_deeptech_sheet
   - Score: 84/115 (A grade)

2. **Nimble Robotics - Head of Customer Experience**
   - URL: https://jobs.lever.co/NimbleAI/32fed95d-6209-4215-a120-a6ebcb396467
   - Issue: 404 error - job no longer exists
   - Scraped: Nov 30, 2025
   - Sent: Nov 30, 2025 (same day)
   - Source: robotics_deeptech_sheet
   - Score: 79/115 (B grade)

3. **BoomerangFX - Director – Engineering & Technology**
   - URL: https://www.linkedin.com/jobs/view/4337183154
   - Issue: "No longer accepting applications"
   - Scraped: Nov 30, 2025
   - Sent: Nov 30, 2025 (same day)
   - Source: recruiter (email)
   - Score: 82/115 (A grade)

4. **Calance - Director AI Engineering Operations & Data Engineering**
   - URL: https://www.linkedin.com/jobs/view/4323474169
   - Issue: "No longer accepting applications"
   - Scraped: Nov 30, 2025
   - Sent: Nov 30, 2025 (same day)
   - Source: recruiter (email)
   - Score: 85/115 (A grade)

## Root Causes

### 1. No URL Validation Before Sending Digest

**Current behavior**: Jobs are added to database and immediately eligible for digest
- No HTTP status code checks
- No verification that URL points to active job posting
- No detection of "no longer accepting" messages

**Impact**: Dead links and inactive jobs sent to users

### 2. LinkedIn Jobs Inaccessible Without Login

**Challenge**: LinkedIn requires authentication to view job details
- HTTP GET returns 301 redirect to login page
- Cannot programmatically check if job is still accepting applications
- Recruiter emails often include LinkedIn URLs

**Current validation**: 301 redirect appears as "success" to naive checks

### 3. Incomplete/Generic URLs in Robotics Spreadsheet

**Problem**: Graymatter URL is career page, not job posting
- URL: `https://jobs.ashbyhq.com/graymatter-robotics`
- This is the company's career page
- Actual job postings have specific IDs like `/graymatter-robotics/8f5e099e-4f3f-4d3b-9e27-ed843428b048`

**Validation attempt**: Career page returns HTTP 200, so URL appears valid
**Actual issue**: "Director of Hardware" never existed on that generic URL

### 4. No Job Staleness Detection

**Current behavior**: Jobs remain in digest pool indefinitely
- Jobs scraped weeks ago still eligible
- No "received_at" age filter
- No "last_verified" tracking

**Example**: Graymatter job scraped Nov 21, sent Nov 30 (9 days old)

### 5. Spreadsheet Data Quality Issues

**Problem**: Robotics spreadsheet may contain:
- Outdated job URLs
- Generic career page URLs instead of specific job postings
- URLs to jobs that no longer exist

**No validation**: Spreadsheet is trusted source, no verification

## Impact Analysis

**User trust**: "Wes is starting to lose confidence in the product"
- 4 invalid jobs out of how many total in digest?
- High scores (79-85) make this worse - user expects quality
- Mix of sources shows systemic issue, not isolated problem

**Data source breakdown**:
- LinkedIn (2 jobs): Cannot validate without authentication
- Robotics spreadsheet (2 jobs): Generic URL + stale data

## Immediate Fixes Needed

### 1. Pre-Send URL Validation (HIGH PRIORITY)

Before including job in digest:
```python
def validate_job_url(url: str) -> tuple[bool, str]:
    """
    Validate job URL is accessible and active

    Returns:
        (is_valid, reason)
    """
    # HTTP status check
    response = requests.head(url, allow_redirects=True, timeout=5)

    # 404 = dead link
    if response.status_code == 404:
        return (False, "404_not_found")

    # LinkedIn redirects to login - assume valid but unverifiable
    if "linkedin.com/login" in response.url:
        return (True, "linkedin_unverifiable")

    # Generic career page detection for Ashby
    if "jobs.ashbyhq.com" in url:
        # URL should have job ID: /company/uuid-format
        if url.count('/') <= 3:  # Just /company, no job ID
            return (False, "generic_career_page")

    # Generic career page detection for Lever
    if "jobs.lever.co" in url:
        if url.count('/') <= 3:  # Just /company, no job ID
            return (False, "generic_career_page")

    return (True, "valid")
```

### 2. Job Freshness Filter (HIGH PRIORITY)

Don't send jobs older than 7 days in digest:
```python
# In send_profile_digest.py
MAX_JOB_AGE_DAYS = 7

unsent_jobs = cursor.execute('''
SELECT ...
FROM job_scores js
JOIN jobs j ON js.job_id = j.id
WHERE js.profile_id = ?
  AND js.digest_sent_at IS NULL
  AND datetime(j.received_at) >= datetime('now', '-7 days')  -- NEW FILTER
ORDER BY js.fit_score DESC
''', (profile_name,))
```

### 3. Mark Invalid Jobs in Database (MEDIUM PRIORITY)

Add job validation status:
```sql
ALTER TABLE jobs ADD COLUMN validation_status TEXT DEFAULT 'pending';
ALTER TABLE jobs ADD COLUMN validation_checked_at TEXT;
ALTER TABLE jobs ADD COLUMN validation_reason TEXT;
```

Values: `pending`, `valid`, `invalid_404`, `invalid_generic_url`, `invalid_closed`

### 4. LinkedIn Job Expiration Assumption (MEDIUM PRIORITY)

LinkedIn jobs typically expire after 30 days:
- Add metadata tracking for LinkedIn sources
- Auto-flag LinkedIn jobs >30 days old as potentially stale
- Lower score or exclude from digest

### 5. Spreadsheet URL Quality Check (LOW PRIORITY - LONG TERM)

Validate robotics spreadsheet URLs on scrape:
- Check URL is specific job posting, not career page
- Verify job still listed on page
- Add "last_verified" timestamp
- Re-validate monthly

## Recommended Implementation Priority

**Phase 1 (Immediate - Next Digest)**:
1. Add 7-day freshness filter to digest query ✅ Quick win
2. Add pre-send HTTP status validation ✅ Catches 404s

**Phase 2 (This Week)**:
3. Add job validation status to database schema
4. Implement comprehensive validation function
5. Add validation check before digest send
6. Log validation failures for debugging

**Phase 3 (Next Sprint)**:
7. Add LinkedIn-specific staleness detection
8. Implement generic URL detection for Ashby/Lever
9. Add re-validation for jobs >7 days old
10. Create validation monitoring dashboard

## Test Cases to Prevent Regression

1. **404 Detection**: Mock Lever URL returning 404
2. **Generic URL Detection**: Test `https://jobs.ashbyhq.com/company` (no job ID)
3. **LinkedIn Redirect**: Mock LinkedIn login redirect
4. **Freshness Filter**: Test job >7 days old excluded from digest
5. **Valid Job**: Test job passes all validation checks

## Success Metrics

After implementing fixes:
- **Zero 404 errors** in digests sent to users
- **Zero generic career page URLs** without specific job IDs
- **No jobs >7 days old** in digest (configurable threshold)
- **Validation status tracked** for all jobs in database
- **Re-validation** of jobs before each digest send

## Notes

- LinkedIn validation will remain imperfect (requires auth)
- Should we add "Last verified: X days ago" to digest email?
- Consider webhook/scraping to detect when jobs are closed
- Spreadsheet quality is upstream issue - may need manual review

## Files to Modify

1. `src/send_profile_digest.py` - Add freshness filter
2. `src/utils/job_validator.py` - NEW: URL validation logic
3. `src/database.py` - Add validation columns
4. `tests/unit/test_job_validator.py` - NEW: Validation tests
5. `src/jobs/weekly_unified_scraper.py` - Validate on scrape
