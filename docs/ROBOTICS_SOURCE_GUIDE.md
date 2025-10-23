# Robotics/Deeptech Job Source - Complete Guide

## Overview

The robotics/deeptech Google Sheets source contains **1,092 jobs** from top robotics companies (Boston Dynamics, Skydio, Waymo, Figure AI, etc.). This is the **highest-quality source** for Wesley's profile, with 171 leadership roles scoring significantly better than LinkedIn/Supra sources.

**Performance Comparison:**
- **LinkedIn/Supra**: Mostly F/D grades (35-42 pts) - Software PM roles at SaaS companies
- **Robotics Sheet**: 10 A/B grade jobs (70-87 pts) - Hardware engineering leadership

---

## What Was Built

### 1. Weekly Scraper Job ✅
**File**: `src/jobs/weekly_robotics_scraper.py`

Automated scraper that:
- Scrapes 500+ robotics jobs from Google Sheets
- Filters for leadership roles (Director+, VP, Head of)
- Scores against Wesley's profile
- Only stores/notifies for B+ grade jobs (70+)
- Handles duplicates automatically

**Usage:**
```bash
# Run manually (default: B+ grade, leadership only)
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py

# A-grade only (85+)
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 85

# Include IC roles
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --all-roles
```

### 2. Cron Scheduler ✅
**File**: `scripts/setup_weekly_scraper_cron.sh`

Automated scheduling for weekly runs.

**Setup:**
```bash
# Run setup script (adds cron job for every Monday at 9am)
./scripts/setup_weekly_scraper_cron.sh

# View your crontab
crontab -l

# View logs
tail -f logs/weekly_scraper.log
```

**Cron Schedule**: Every Monday at 9:00 AM

### 3. Master Pipeline Integration ✅
**File**: `src/processor_master.py`

Unified processor that runs ALL sources in one command:
- Email sources (LinkedIn, Supra, F6S, Artemis)
- Robotics/deeptech web scraper

**Usage:**
```bash
# Run everything (emails + robotics)
job-agent-venv/bin/python src/processor_master.py

# Email sources only
job-agent-venv/bin/python src/processor_master.py --robotics-only=false

# Robotics only
job-agent-venv/bin/python src/processor_master.py --email-only=false

# Custom score threshold
job-agent-venv/bin/python src/processor_master.py --robotics-min-score 80
```

### 4. Instant Notifications for A/B Grade Jobs ✅
**Modified**: `src/processor_v2.py` and `src/jobs/weekly_robotics_scraper.py`

Both processors now:
- Only send notifications for jobs scoring 70+ (A/B grade)
- Add score to notification title: `[B 77] Director of Engineering @ Boston Dynamics`
- Skip notifications for C/D/F grade jobs
- Log skipped notifications

**Notification Format:**
```
Subject: [B 82] New Job: Director of Product Management
Company: Skydio
Score: B (82/100)
Link: https://www.skydio.com/careers
```

---

## Test Results

**Latest Run (2025-10-22):**
```
Jobs scraped: 171 (leadership roles)
Passed PM/Engineering filter: 21
High-scoring (B+ grade): 6
New jobs stored: 5
Duplicates skipped: 1
```

**Top Jobs Stored:**
1. **Director of Product Management @ Skydio** - B (82/100)
2. **Director of Product Management @ Boston Dynamics** - B (77/100)
3. **Engineering Director @ Bright Machines** - B (77/100)
4. **Director of Engineering @ Waymo** - B (70/100)
5. **Director of Engineering @ Apis Cor** - B (70/100)

**Score Breakdown:**
- Seniority: 30/30 (Director level)
- Domain: 25/25 (Robotics/hardware companies)
- Role Type: 10-20/20 (Product vs Engineering leadership)

---

## Workflow

### Manual Run (On-Demand)
```bash
# 1. Run robotics scraper
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 70

# 2. View results
job-agent-venv/bin/python src/generate_jobs_html.py
open jobs.html
```

### Automated Run (Scheduled)
```bash
# 1. Setup cron (one-time)
./scripts/setup_weekly_scraper_cron.sh

# 2. Check logs
tail -f logs/weekly_scraper.log

# 3. View results weekly
open jobs.html
```

### Full Pipeline (All Sources)
```bash
# Run emails + robotics in one command
job-agent-venv/bin/python src/processor_master.py

# View combined results
open jobs.html
```

---

## Scoring Algorithm for Robotics Jobs

**Why robotics jobs score higher:**

| Factor | Software PM | Robotics Director |
|--------|-------------|-------------------|
| Seniority | 15 pts (Staff PM) | 30 pts (Director) |
| Domain | 5 pts (SaaS) | 25 pts (Robotics) |
| Role Type | 5 pts (PM) | 20 pts (Eng Dir) |
| **Total** | **35/100 (F)** | **75/100 (B)** |

**Perfect match example**: Senior Director of Software Engineering @ Boston Dynamics
- Seniority: 30/30 (Director+)
- Domain: 25/25 (Robotics)
- Role Type: 20/20 (Engineering leadership)
- **Score: 87/100 (A grade)** ⭐

---

## Configuration

### Adjust Minimum Score
Edit the command or cron job:
```bash
# Higher threshold (A-grade only, 85+)
--min-score 85

# Lower threshold (C+ grade, 55+)
--min-score 55

# Default (B+ grade, 70+)
--min-score 70
```

### Include IC Roles
```bash
# Add flag to include individual contributor roles
--all-roles
```

### Change Schedule
Edit crontab:
```bash
crontab -e

# Examples:
0 9 * * 1     # Monday at 9am (default)
0 9 * * *     # Every day at 9am
0 9 * * 1,4   # Monday and Thursday at 9am
```

---

## Maintenance

### View Logs
```bash
# Real-time monitoring
tail -f logs/weekly_scraper.log

# Last 50 lines
tail -50 logs/weekly_scraper.log

# Search for high-scoring jobs
grep "Score: A" logs/weekly_scraper.log
grep "Score: B" logs/weekly_scraper.log
```

### Database Stats
```bash
# View all stored jobs
job-agent-venv/bin/python -c "from src.database import JobDatabase; db = JobDatabase(); print(db.get_stats())"

# Count robotics jobs
sqlite3 data/jobs.db "SELECT COUNT(*) FROM jobs WHERE source='robotics_deeptech_sheet';"

# View top-scoring robotics jobs
sqlite3 data/jobs.db "SELECT title, company, fit_grade, fit_score FROM jobs WHERE source='robotics_deeptech_sheet' ORDER BY fit_score DESC LIMIT 10;"
```

### Update Scraper
If the Google Sheet structure changes, update:
- `src/scrapers/robotics_deeptech_scraper.py` - Column mappings
- Sheet ID/GID if URL changes

---

## Next Steps

1. **Set up cron job** (one-time):
   ```bash
   ./scripts/setup_weekly_scraper_cron.sh
   ```

2. **Test the scraper**:
   ```bash
   job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 70
   ```

3. **View results**:
   ```bash
   open jobs.html
   ```

4. **Monitor logs weekly**:
   ```bash
   tail -f logs/weekly_scraper.log
   ```

5. **Adjust scoring** based on results (see Issue #4 for configurable scoring)

---

## Related Issues

- **Issue #1**: Filter notifications to only send for high-scoring jobs (✅ Implemented)
- **Issue #2**: Add minimum score threshold to job filter
- **Issue #3**: Create daily digest email with top-scored jobs
- **Issue #4**: Make scoring weights configurable

---

**🎯 Bottom Line**: The robotics source is your **highest-value job feed**. Set up the cron job and you'll get weekly alerts for Director+ roles at Boston Dynamics, Waymo, Skydio, and other top robotics companies - automatically scored and filtered for Wesley's profile.
