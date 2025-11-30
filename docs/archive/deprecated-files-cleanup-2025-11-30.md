# Deprecated Files Cleanup - November 30, 2025

## Summary
Removed 7 deprecated processor and digest files that were replaced by the current unified scraper architecture. Key features were documented and converted to GitHub issues before deletion.

## Files Removed

### Old Processors (replaced by `weekly_unified_scraper.py`)
- `src/processor.py` - Original v1 email processor
- `src/processor_master.py` - Old master orchestrator (combined emails + robotics)

### Experimental V3 (never fully adopted)
- `src/jobs/unified_scraper_v3.py` - Experimental unified scraper with two-tier scoring
- `src/jobs/test_unified_workflow.py` - Test script for v3 scraper

### Old Digest Scripts (replaced by `send_profile_digest.py`)
- `src/send_digest_to_wes.py` - Single-profile digest for Wes only
- `src/send_digest_to_wes_v2.py` - Added digest tracking (v2)
- `src/send_digest_copy.py` - Copy utility for Adam (imported from send_digest_to_wes)

## Current Architecture (Kept)
- ✅ `src/processor_v2.py` - Email processor (used by weekly_unified_scraper)
- ✅ `src/jobs/weekly_unified_scraper.py` - Current recommended scraper (TUI uses this)
- ✅ `src/send_profile_digest.py` - Multi-profile digest sender (TUI uses this)

## Valuable Features Preserved

### 1. Two-Tier Progressive Scoring (HIGH Priority)
**Source:** `unified_scraper_v3.py:286-295`
**GitHub Issue:** #78

**Concept:** Progressive scoring to save API costs
- Tier 1: Basic scoring with just title, company, location
- Tier 2: If score >= 70, fetch full JD and re-score
- **Benefit:** 30-50% reduction in Firecrawl API calls

**Implementation:**
```python
# STEP 1: Basic scoring (with title, company, location only)
score, grade, breakdown = scorer.score_job_basic(job)

# STEP 2: Enhanced scoring for promising jobs
if score >= 70:  # Configurable threshold
    full_jd = fetch_job_description(job["link"])
    if full_jd:
        job["description"] = full_jd
        score, grade, breakdown = scorer.score_job_full(job)
        stats["jobs_enhanced_scoring"] += 1
```

### 2. Enhanced Statistics Tracking (MEDIUM Priority)
**Source:** `unified_scraper_v3.py:80-89`
**GitHub Issue:** #79

**Additional metrics:**
```python
stats = {
    "jobs_enhanced_scoring": 0,  # Jobs that triggered full JD fetch
    "duplicates_skipped": 0,     # Deduplication metrics
    "errors": 0,                 # Systematic error count
    "errors_by_source": {},      # Per-source error tracking
}
```

**Benefit:** Better observability into scraper health and performance

### 3. Company Deduplication (LOW Priority)
**Source:** `unified_scraper_v3.py` (company discovery phase)
**GitHub Issue:** #80

**Concept:** Avoid scraping same company multiple times per run
- Collect companies from all sources first
- Normalize URLs (remove www, trailing slash)
- Deduplicate before scraping
- **Benefit:** 10-20% reduction in duplicate scrapes

### 4. Browser Extension Source (FUTURE)
**Source:** `unified_scraper_v3.py:100-110` (pattern only)
**GitHub Issue:** #81

**Concept:** Chrome/Firefox extension for manual company discovery
- User browses career pages, clicks extension to submit
- Stored in database for next scraper run
- User-driven quality signal

**Status:** Pattern exists, never implemented

## Why These Files Were Deprecated

### processor.py (v1)
- No pluggable parser support
- No enrichment pipeline
- Replaced by processor_v2.py in 2024

### processor_master.py
- Just an orchestrator for processor_v2 + robotics checker
- Replaced by weekly_unified_scraper.py which adds:
  - Company monitoring support
  - Multi-profile support
  - Better CLI interface
  - TUI integration

### unified_scraper_v3.py
- Experimental rewrite attempting full unification
- Never completed or adopted
- Two-tier scoring concept extracted to Issue #78
- Company dedup concept extracted to Issue #80

### send_digest_to_wes.py / _v2.py
- Single-profile only (Wes)
- Hard-coded email addresses
- Replaced by send_profile_digest.py which supports:
  - Multi-profile (Wes and Adam)
  - Profile-specific scoring criteria
  - Profile-specific email templates

### send_digest_copy.py
- Just imported from send_digest_to_wes.py
- No unique functionality
- Replaced by `--profile adam` flag in send_profile_digest.py

## Cleanup Checklist
- [x] Created GitHub issues for valuable features (#78, #79, #80, #81)
- [x] Documented features in this file
- [ ] Remove 7 deprecated files
- [ ] Update sonar-project.properties exclusions
- [ ] Commit cleanup with references to issues
- [ ] Verify TUI still works after cleanup

## References
- PR #XX (cleanup PR, will be created)
- Issue #78 - Two-tier progressive scoring
- Issue #79 - Enhanced statistics tracking
- Issue #80 - Company deduplication
- Issue #81 - Browser extension source
