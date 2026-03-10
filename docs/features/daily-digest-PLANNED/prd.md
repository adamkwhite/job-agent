# PRD: Daily Scraping & Digest Frequency

## Overview

Convert the job-agent from weekly-only scraping and digests to daily full scraping with per-profile digest frequency control. Profiles can opt into `daily` or `weekly` digest cadence independently.

## Problem Statement

**Current State:**
- Full scrape pipeline (emails + companies + ministry) runs once per week (Monday 6am)
- All profiles receive digests on the same weekly schedule
- `send_frequency` field exists in profile JSON but is completely unused by code
- Jobs posted mid-week aren't discovered until the following Monday
- Users miss time-sensitive opportunities (roles filled within days of posting)

**Pain Points:**
1. Week-long lag between job posting and discovery for career page jobs
2. Email-sourced jobs (LinkedIn alerts arrive daily) sit unprocessed for up to 7 days
3. No flexibility for profiles that want more frequent updates
4. Competitive disadvantage — other candidates apply days earlier

**Desired State:**
- Full scrape pipeline runs daily (6am)
- Each profile controls its own digest frequency (`daily` or `weekly`)
- Daily profiles receive new jobs within 24 hours of discovery
- Weekly profiles continue receiving Monday digests (no disruption)
- Zero additional configuration burden for existing users

## Goals

### Primary Goals
1. **Reduce discovery lag:** Jobs discovered within 24 hours of posting instead of up to 7 days
2. **Per-profile frequency:** Honor the existing `send_frequency` profile field
3. **Backward compatible:** Weekly profiles see no change in behavior

### Secondary Goals
1. **Cost monitoring:** Track API cost increase from 7x scraping frequency
2. **Empty digest handling:** Daily profiles gracefully skip days with no new jobs (no empty emails)

## Success Criteria

- [ ] Cron runs daily at 6am with full scrape (emails + companies + ministry)
- [ ] Profiles with `send_frequency: "daily"` receive digests after each scrape
- [ ] Profiles with `send_frequency: "weekly"` receive digests only on Mondays
- [ ] Daily digests include only jobs from the last 2 days (not full 7-day window)
- [ ] No duplicate jobs sent (existing `digest_sent_at` tracking works correctly)
- [ ] No empty digest emails sent (skip when 0 new jobs)
- [ ] LLM/Firecrawl costs remain within budget ($5/mo Gemini, Firecrawl as fallback only)
- [ ] `--frequency` CLI flag works for manual testing

## Requirements

### Functional Requirements

1. **Frequency-Aware Digest Sending**
   - FR-1: `send_profile_digest.py --all` shall read each profile's `digest_frequency` to determine `max_age_days` (daily=2, weekly=7)
   - FR-2: New `--frequency <daily|weekly>` CLI arg shall filter which profiles receive digests
   - FR-3: `send_all_digests()` shall accept `frequency_filter` parameter
   - FR-4: `_prevalidate_jobs_for_all_profiles()` shall use per-profile `max_age_days` instead of a single value
   - FR-5: Existing `--max-age-days` CLI arg shall override profile-based defaults when explicitly provided

2. **Cron Automation**
   - FR-6: `run_unified_scraper.sh` shall run full scrape daily (not just Mondays)
   - FR-7: After scraping, script shall send digests with `--frequency daily`
   - FR-8: On Mondays (day-of-week=1), script shall also send digests with `--frequency weekly`
   - FR-9: `setup_unified_weekly_scraper.sh` shall install cron at `0 6 * * *` (daily 6am)

3. **Profile Configuration**
   - FR-10: Profile `digest.send_frequency` field shall control digest cadence (already validated by Pydantic)
   - FR-11: Default frequency shall remain `"weekly"` for backward compatibility
   - FR-12: No profile JSON changes required — users update when ready

### Non-Functional Requirements

- NF-1: No database schema changes required
- NF-2: No changes to scraping pipeline (`weekly_unified_scraper.py`)
- NF-3: No changes to TUI (interactive flow is manual/on-demand)
- NF-4: Existing `digest_sent_at IS NULL` tracking prevents duplicates regardless of frequency

## Technical Design

### Architecture

The change is minimal because the existing architecture already separates scraping from digest sending, and the `digest_sent_at` tracking is frequency-agnostic.

```
Daily Cron (6am)
  |
  +-- Full scrape (emails + companies + ministry)
  |     (no changes needed)
  |
  +-- send_profile_digest.py --all --frequency daily
  |     -> filters to daily profiles
  |     -> max_age_days=2 per profile
  |
  +-- [Monday only] send_profile_digest.py --all --frequency weekly
        -> filters to weekly profiles
        -> max_age_days=7 per profile
```

### Key Insight: `digest_sent_at IS NULL` Is the Real Filter

The `max_age_days` parameter is a lookback window, not a deduplication mechanism. The `digest_sent_at IS NULL` clause in `get_jobs_for_profile_digest()` ensures jobs are never double-sent. This means:
- Daily profiles with `max_age_days=2` will get any unsent jobs from the last 2 days
- If a job was already sent yesterday, it won't appear again (NULL check)
- Using 2 instead of 1 provides a safety buffer for jobs scraped near midnight

### Files Changed

| File | Change |
|------|--------|
| `src/send_profile_digest.py` | Add `--frequency` arg, frequency filtering in `send_all_digests()`, per-profile `max_age_days` in `_prevalidate_jobs_for_all_profiles()` |
| `scripts/run_unified_scraper.sh` | Daily schedule, split digest calls (daily always, weekly on Mondays) |
| `scripts/setup_unified_weekly_scraper.sh` | Change cron from `0 6 * * 1` to `0 6 * * *` |
| `tests/unit/test_digest_frequency.py` | New: frequency filtering and per-profile age window tests |

### Files NOT Changed

| File | Reason |
|------|--------|
| `src/database.py` | Already supports `max_age_days` + `digest_sent_at IS NULL` |
| `src/utils/profile_manager.py` | Already has `digest_frequency` property |
| `src/models/pydantic_models.py` | Already validates `daily`/`weekly` enum |
| `src/jobs/weekly_unified_scraper.py` | Scraping is frequency-agnostic |
| `src/tui.py` | Interactive mode doesn't need frequency awareness |
| Profile JSONs | Configuration-only; users flip `send_frequency` when ready |

## Cost Impact

| Resource | Weekly (current) | Daily (new) | Notes |
|----------|-----------------|-------------|-------|
| Email scraping (IMAP) | 1x/week | 7x/week | Free |
| Company scraping (Playwright) | 1x/week | 7x/week | Free, ~68 companies |
| LLM extraction (Gemini Flash) | ~$1/week | ~$5/week | $5/mo budget — monitor closely |
| Firecrawl fallback | Rare | Rare (7x more chances) | Paid, fallback only |
| Ministry scraper | 1x/week | 7x/week | Free |

**Mitigation:** The `--skip-recent-hours` flag already exists in company scraper. If costs spike, add `--skip-recent-hours 20` to daily cron to avoid re-scraping companies checked less than 20 hours ago.

## Risks

1. **LLM cost overrun** — 7x increase in Gemini API calls. Mitigated by $5/mo budget cap and `--skip-recent-hours`.
2. **Empty daily digests** — On days with no new jobs, daily profiles get no email. This is correct behavior (code already handles gracefully).
3. **Email forwarding lag** — LinkedIn alerts may batch. The `digest_sent_at IS NULL` filter handles this regardless of timing.
4. **Rate limiting** — Daily scraping of 68+ career pages. Playwright has no rate limits; Firecrawl fallback is rare.

## Testing Plan

1. Unit tests for frequency filtering (`--frequency daily` only sends to daily profiles)
2. Unit tests for per-profile `max_age_days` (daily=2, weekly=7)
3. Dry-run daily digest for a test profile
4. Verify no duplicates after switching from weekly to daily
5. Monitor LLM costs for first week after deployment
