# TUI Workflow Guide - Sources-First Architecture

**Last Updated**: 2026-02-13 (Issue #191)

## Overview

The Job Agent TUI uses a **sources-first workflow** that decouples scraping from digest recipients. This architecture:
- Enables efficient multi-profile digests from single scrapes
- Separates concerns: what to scrape vs. who gets results
- Matches Issue #184 multi-profile scoring architecture

## Quick Reference

```
Step 1: Select Sources → What to scrape (profile-agnostic)
Step 2: Select Action → Scrape, Digest, or Both
Step 3: Run Scraper → Execute scraping (if needed)
Step 4: Select Recipients → Who gets digest (if sending)
Step 5: Digest Options → Production, Dry-run, or Force-resend
Step 6: Confirm & Execute → Review and proceed
```

## Detailed Workflow

### Step 1: Select Job Sources

**No profile selection needed** - sources are profile-agnostic by default.

**Available Sources:**
- **Company Monitoring (68 companies)** - Default/recommended
  - Profile-agnostic: jobs scored for ALL profiles automatically
  - Uses Firecrawl MCP for JavaScript-heavy pages
  - Storage threshold: D+ grade (50+)
  - Notification threshold: A/B grade (70+)

- **Email Processing** - Requires inbox selection
  - Processes LinkedIn, Supra, F6S, Artemis, Built In newsletters
  - Prompts for inbox selection (Adam, Wes, Eli, Mario)
  - Jobs scored for ALL profiles (not just inbox owner)
  - Storage threshold: All passing filter

- **Ministry of Testing** - QA/testing job board
  - Profile-agnostic scraping
  - Automatically scored for all profiles

**Utility Options:**
- **api**: API Credits - Check LLM/Firecrawl budget status
- **c**: Companies - Review auto-discovered companies
- **h**: System Health - View error dashboard, budget, activity
- **q**: Quit

**Examples:**
```
Input: "a" or "all"     → All sources (companies, email, ministry)
Input: "1"              → Company monitoring only
Input: "1,2"            → Companies + email (prompts for inbox)
Input: "2"              → Email only (prompts for inbox)
```

#### 1b: Email Inbox Selection (if email selected)

If you select email processing, you'll be prompted to choose which inbox to connect to:

```
╭────────┬─────────────┬──────────────────────────────╮
│ Option │ Profile     │ Email Inbox                   │
├────────┼─────────────┼──────────────────────────────┤
│ 1      │ Wesley      │ wes.jobalerts@gmail.com       │
│ 2      │ Adam        │ adam.jobalerts@gmail.com      │
│ 3      │ Eli         │ eli.jobalerts@gmail.com       │
│ 4      │ Mario       │ mario.jobalerts@gmail.com     │
│ c      │ Cancel      │ Skip email processing         │
╰────────┴─────────────┴──────────────────────────────╯
```

**Important Notes:**
- Inbox selection determines **which email account to connect to** for scraping
- Jobs are **automatically scored for ALL profiles** (not just inbox owner)
- Only profiles with `email_username` configured in their profile JSON will appear

### Step 2: Select Action

Choose what to do with the selected sources:

```
╭────────┬────────────────┬─────────────────────────────────────╮
│ Option │ Action         │ Description                         │
├────────┼────────────────┼─────────────────────────────────────┤
│ 1      │ Scrape Only    │ Fetch and score jobs, store in DB   │
│ 2      │ Send Digest    │ Send email digest with stored jobs  │
│ 3      │ Scrape+Digest  │ Run scraper then send digest email  │
│ c      │ View Criteria  │ Show scoring criteria & grading     │
│ f      │ LLM Failures   │ Review failed LLM extractions       │
│ h      │ System Health  │ View health dashboard               │
│ b      │ Back           │ Return to source selection          │
│ q      │ Quit           │ Exit application                    │
╰────────┴────────────────┴─────────────────────────────────────╯
```

**When to use each:**
- **Scrape Only**: When you want to gather jobs but review before sending
- **Send Digest**: When you already have unsent jobs and want to send them
- **Scrape+Digest** (most common): Weekly workflow - scrape and immediately send

### Step 3: Run Scraper (if action includes scraping)

The scraper executes based on selected sources:

**Command Format:**
```bash
# Companies only (no profile needed)
job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --companies-only

# Email only (requires profile for inbox)
job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam --email-only

# All sources (requires profile if email included)
job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes
```

**What happens:**
1. Scraper connects to selected sources
2. Jobs extracted and parsed
3. **ALL enabled profiles are scored automatically** (Issue #184 architecture)
4. Jobs stored in `jobs` table with scores in `job_scores` table
5. Deduplication prevents duplicate jobs
6. Progress displayed in terminal

**Note**: If scraper fails, you can choose to continue anyway or return to menu.

### Step 4: Select Digest Recipients (if action includes digest)

Choose who should receive the email digest:

```
╭────────┬─────────────────────┬─────────────────────────────╮
│ Option │ Recipient           │ Email                       │
├────────┼─────────────────────┼─────────────────────────────┤
│ 1      │ Wesley van Ooyen    │ wesvanooyen@gmail.com       │
│ 2      │ Adam White          │ adamkwhite@gmail.com        │
│ 3      │ Eli ...             │ eli@example.com             │
│ 4      │ Mario ...           │ mario@example.com           │
│ a      │ All Enabled         │ Sends to 4 profiles         │
│ s      │ Skip Digest         │ Don't send any digest       │
╰────────┴─────────────────────┴─────────────────────────────╯

Note: Multiple selections allowed (e.g., '1,2' sends to Wes + Adam).
      Digest tracking is profile-specific (same job can go to multiple profiles).
```

**Examples:**
```
Input: "a" or "all"  → Sends to all 4 enabled profiles
Input: "1"           → Sends to Wesley only
Input: "1,2,4"       → Sends to Wesley, Adam, and Mario
Input: "s"           → Skip digest (scrape-only workflow)
```

**Key Concept - Profile-Specific Digest Tracking:**
- Each profile tracks which jobs **they** have received
- Same job can be sent to multiple profiles independently
- Example: Job #123 marked "sent" for Wes but not for Adam

### Step 5: Digest Options (if sending digest)

Choose how to send the digest:

```
╭────────┬──────────────┬─────────────┬──────────────┬────────────────────────╮
│ Option │ Mode         │ Sends Email?│ Marks Sent?  │ Use Case               │
├────────┼──────────────┼─────────────┼──────────────┼────────────────────────┤
│ 1      │ Production   │ ✅ Yes      │ ✅ Yes       │ Real digest            │
│ 2      │ Dry Run      │ ❌ No       │ ❌ No        │ Testing/preview        │
│ 3      │ Force Resend │ ✅ Yes      │ ❌ No        │ Re-send previous jobs  │
╰────────┴──────────────┴─────────────┴──────────────┴────────────────────────╯

Note: Use 'Dry Run' during testing to avoid marking jobs as sent.
```

**Mode Details:**
- **Production** (default for weekly workflow): Sends real emails, marks jobs as sent for each recipient
- **Dry Run** (default in TUI): Preview digest HTML, no emails sent, jobs remain unsent
- **Force Resend**: Useful for re-sending jobs after profile changes or scoring updates

### Step 6: Confirm & Execute

Review the execution plan before proceeding:

```
┌─────────────────────────────────────────────────┐
│           Execution Plan                        │
├─────────────────────────────────────────────────┤
│ Sources: Companies, Email, Ministry             │
│ Email Inbox: Wesley van Ooyen (wes@...)        │
│ Action: Scrape and Send Digest                  │
│ Digest Recipients: Adam White, Eli ...          │
│ Digest Mode: Production (real digest)           │
└─────────────────────────────────────────────────┘

Proceed with execution? [Y/n]:
```

**What gets executed:**
1. If scraping: Runs scraper for selected sources
2. If digest: Sends emails to selected recipients sequentially
3. Progress displayed in real-time
4. Final success/failure summary shown

## Common Workflows

### Weekly Scraping for All Profiles

**Goal**: Scrape companies and send digests to everyone.

```
Step 1: Select "1" (Company Monitoring)
Step 2: Select "3" (Scrape + Digest)
Step 3: [Scraper runs automatically]
Step 4: Select "a" (All Enabled Profiles)
Step 5: Select "1" (Production)
Step 6: Confirm → Execute
```

**Result**: One company scrape, 4 digests sent (efficient).

### Email Processing for Single Profile

**Goal**: Check one person's email inbox and send them a digest.

```
Step 1: Select "2" (Email Processing)
  → Select "1" (Wesley's inbox)
Step 2: Select "3" (Scrape + Digest)
Step 3: [Scraper runs]
Step 4: Select "1" (Wesley only)
Step 5: Select "1" (Production)
Step 6: Confirm → Execute
```

**Result**: Wes's email processed, digest sent to Wes only.

### Multi-Source Scrape with Selective Digests

**Goal**: Scrape everything, send to 2 specific people.

```
Step 1: Select "a" (All Sources)
  → Select "2" (Adam's inbox) [if email included]
Step 2: Select "3" (Scrape + Digest)
Step 3: [Scraper runs]
Step 4: Select "1,3" (Wesley and Eli)
Step 5: Select "1" (Production)
Step 6: Confirm → Execute
```

**Result**: All sources scraped, digests sent to Wes and Eli only.

### Dry-Run Testing Before Production

**Goal**: Test digest generation without actually sending emails.

```
Step 1: Select "1" (Company Monitoring)
Step 2: Select "3" (Scrape + Digest)
Step 3: [Scraper runs]
Step 4: Select "2" (Adam)
Step 5: Select "2" (Dry Run)
Step 6: Confirm → Execute
```

**Result**: Digest HTML generated and displayed, no email sent, jobs remain unsent.

### Scrape Now, Send Later

**Goal**: Gather jobs but review before sending.

```
# First: Scrape only
Step 1: Select "1,2" (Companies + Email)
Step 2: Select "1" (Scrape Only)
Step 3: [Scraper runs]
[Exit TUI]

# Later: Send digests
Step 1: Select "a" (All)
Step 2: Select "2" (Send Digest)
Step 4: Select "a" (All Profiles)
Step 5: Select "1" (Production)
Step 6: Confirm → Execute
```

**Result**: Jobs scraped and reviewed, then sent when ready.

## Architecture Benefits

### Why Sources-First?

**Before (Profile-First)**:
```
Problem: To send digests to all 4 profiles after company scraping:
1. Run TUI → Select Wes → Scrape companies → Send digest
2. Run TUI → Select Adam → Scrape companies → Send digest  [DUPLICATE SCRAPE!]
3. Run TUI → Select Eli → Scrape companies → Send digest    [DUPLICATE SCRAPE!]
4. Run TUI → Select Mario → Scrape companies → Send digest  [DUPLICATE SCRAPE!]

Cost: 4x scraping effort, 4x API costs (~$2.80 wasted)
```

**After (Sources-First)**:
```
Solution: Single scraping run, multiple digest recipients:
1. Run TUI → Select Companies → Scrape → Send to All Profiles

Cost: 1x scraping effort, optimal API usage
Savings: ~$2.80 per run
```

### Multi-Profile Scoring (Issue #184)

**Key Insight**: Scraping is decoupled from scoring.

```
When you scrape ANY source with ANY inbox:
├─ Jobs extracted once
├─ Jobs stored in 'jobs' table (deduplicated)
└─ Jobs scored for ALL enabled profiles automatically
    ├─ Wes's score → job_scores table (profile_id=wes)
    ├─ Adam's score → job_scores table (profile_id=adam)
    ├─ Eli's score → job_scores table (profile_id=eli)
    └─ Mario's score → job_scores table (profile_id=mario)

Result: One scrape, everyone gets personalized scores.
```

**Digest Tracking**: Profile-specific sent flags allow same job to go to multiple people.

### Efficiency Gains

| Scenario | Old Workflow | New Workflow | Savings |
|----------|--------------|--------------|---------|
| Company scrape → all profiles | 4 runs | 1 run | 75% time |
| Email + Companies → 2 profiles | 2 runs | 1 run | 50% time |
| Multi-inbox processing | Sequential | Parallel option | Variable |

## Troubleshooting

### "No email accounts configured"

**Cause**: Selected email processing but no profiles have `email_username` set.

**Fix**: Add `email_username` to profile JSON files in `profiles/`.

### "No unsent jobs available"

**Cause**: Selected "Send Digest" but all jobs already marked as sent for selected profiles.

**Fix**:
- Use "Force Resend" option to re-send jobs
- Or run scraper first to get new jobs

### Scraper fails but want to send digest anyway

**Cause**: Network issue, API timeout, or scraper error.

**Fix**: TUI prompts "Continue anyway?" - you can proceed to send digests with existing jobs.

### Digest sent to wrong people

**Cause**: Multi-select syntax confusion.

**Fix**: Use comma-separated numbers: `"1,2,4"` not `"1 2 4"` or `"124"`.

## Related Documentation

- **Multi-Profile System**: `docs/development/MULTI_PROFILE_GUIDE.md`
- **Adding Profiles**: `docs/development/ADDING_NEW_PROFILES.md`
- **Scoring Updates**: `docs/development/SCORING_UPDATE_CHECKLIST.md`
- **Issue #184**: Multi-profile scoring architecture
- **Issue #191**: TUI sources-first restructure

## Technical Implementation

### Key Functions

- **`select_sources()`** → `(sources, inbox_profile)`
  - No profile parameter (sources are profile-agnostic)
  - Returns sources list + optional inbox profile for email

- **`select_digest_recipients()`** → `list[str] | None`
  - Multi-select recipient picker
  - Returns profile IDs or `["all"]` or `None`

- **`run_scraper(sources, inbox_profile)`** → `bool`
  - Sources first, optional inbox profile
  - Only adds `--profile` flag if email processing selected

- **`send_digest(recipients, dry_run, force_resend)`** → `bool`
  - Handles list of recipients or `["all"]`
  - Sequential sending with progress reporting

### Database Schema

```sql
-- Jobs table (single source of truth)
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,
    company TEXT,
    title TEXT,
    -- ... other fields
);

-- Multi-profile scores (Issue #184)
CREATE TABLE job_scores (
    job_id INTEGER,
    profile_id TEXT,
    fit_score INTEGER,
    fit_grade TEXT,
    score_breakdown TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id)
);

-- Profile-specific digest tracking
CREATE TABLE digest_tracking (
    job_id INTEGER,
    profile_id TEXT,
    sent_at TEXT,
    PRIMARY KEY(job_id, profile_id)
);
```

**Result**: Same job can be:
- Scored differently for each profile
- Sent to multiple profiles independently
- Tracked separately for each recipient

## Future Enhancements

### Planned (not yet implemented)
- [ ] Ministry of Testing specific flag (`--ministry-only`)
- [ ] Batch digest preview (show all recipients' digests before sending)
- [ ] Digest scheduling (send at specific time)
- [ ] Profile groups (e.g., "leadership" → Wes, Eli)

### Consider
- [ ] Multi-inbox mode in TUI (currently CLI-only with `--all-inboxes`)
- [ ] Digest history viewer (what was sent when)
- [ ] Job review interface before digest (approve/reject)

---

**Last Updated**: 2026-02-13
**Author**: Claude (Issue #191 implementation)
**Status**: Production-ready, pending manual testing
