# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a job discovery and application automation system for Wesley van Ooyen (robotics/hardware executive). The project has evolved from n8n workflows to Python-based email processing with intelligent job scoring, automated web scraping, and personalized email digests.

## Architecture

### Current Implementation (V2 - Enhanced Intelligence)
- **Python-based email processors** for LinkedIn, Supra, F6S, Artemis newsletters
- **Automated web scraping** of robotics/deeptech job boards (1,092 jobs weekly)
- **Intelligent job scoring** (115-point system) against candidate profile
- **Location-aware filtering** (Remote, Hybrid Ontario, Ontario cities)
- **SQLite database** with deduplication and scoring history
- **Multi-channel notifications** for A/B grade jobs only (80+)
- **Weekly email digests** with interactive HTML job tables
- **Cron-based automation** (Monday 9am scraper runs)

### Project Structure
- `src/` - Python application source code
  - `src/agents/` - Job scoring engine
  - `src/jobs/` - Weekly scraper and automation
  - `src/scrapers/` - Email parsers and web scrapers
  - `src/enrichment/` - Company research pipeline
- `config/` - Configuration files, keyword lists, templates
- `scripts/` - Setup, deployment, and cron scripts
- `docs/` - Documentation, PRDs, research guides
- `tests/` - Test fixtures and validation scripts
- `data/` - SQLite database (jobs.db) and job storage
- `logs/` - Application and scraper logs
- `requirements.txt` - Python dependencies

## Key Components

### 1. Job Scoring Engine (`src/agents/job_scorer.py`)
Multi-factor scoring system (0-115 points) evaluating jobs against Wesley's profile:
- **Seniority** (0-30): VP/Director/Head of roles score highest
- **Domain** (0-25): Robotics, hardware, automation, IoT, MedTech
- **Role Type** (0-20): Engineering leadership > Product leadership
- **Location** (0-15): Remote (+15), Hybrid Ontario (+15), Ontario cities (+12)
- **Company Stage** (0-15): Series A-C, growth stage preferred
- **Technical Keywords** (0-10): Mechatronics, embedded, manufacturing

**Grading**: A (98+), B (80+), C (63+), D (46+), F (<46)

### 2. Email Processing Pipeline (`src/processor_v2.py`)
1. IMAP monitoring of dedicated Gmail account
2. Email parsing to extract job details (title, company, link, location)
3. Keyword-based filtering (include/exclude lists)
4. Job scoring against candidate profile
5. Job deduplication and storage
6. Notification triggers for A/B grade jobs only (80+)

**Supported Sources**: LinkedIn, Supra Product Leadership Jobs, F6S, Artemis

### 3. Robotics Web Scraper (`src/jobs/weekly_robotics_scraper.py`)
- Scrapes 1,092 jobs from robotics/deeptech Google Sheets
- Filters for Director+ leadership roles
- Scores and stores B+ grade jobs (70+)
- Runs weekly via cron (Monday 9am)
- **Key Companies**: Boston Dynamics, Waymo, Skydio, Figure AI, Bright Machines

### 4. Email Digest System (`src/send_digest_to_wes.py`)
- Generates HTML email with top-scoring jobs
- Attaches interactive jobs.html file (56KB)
- Location-based filtering buttons (Remote/Hybrid/Ontario)
- Sent to wesvanooyen@gmail.com with scoring breakdowns

### 5. Master Pipeline (`src/processor_master.py`)
Unified command running all sources:
```bash
job-agent-venv/bin/python src/processor_master.py
```
Runs email processors + robotics scraper + generates HTML + sends digest

## Development Commands

### Run Email Processors
```bash
# All email sources + scoring
job-agent-venv/bin/python src/processor_v2.py

# Fetch latest emails and process
job-agent-venv/bin/python src/processor_v2.py --fetch-emails --limit 50
```

### Run Robotics Scraper
```bash
# Weekly scraper (B+ grade, leadership only)
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py

# Custom threshold
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 80

# Include IC roles
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --all-roles
```

### Run Master Pipeline (All Sources)
```bash
# Everything: emails + robotics + HTML + digest
job-agent-venv/bin/python src/processor_master.py
```

### Generate HTML Report
```bash
# Create interactive jobs.html
job-agent-venv/bin/python src/generate_jobs_html.py

# Open in browser
open jobs.html  # or xdg-open on Linux
```

### Send Email Digest
```bash
# Send to Wesley
job-agent-venv/bin/python src/send_digest_to_wes.py

# Send copy to Adam
job-agent-venv/bin/python src/send_digest_copy.py
```

### Cron Setup
```bash
# Setup weekly scraper (Monday 9am)
./scripts/setup_weekly_scraper_cron.sh

# View cron jobs
crontab -l

# View logs
tail -f logs/weekly_scraper.log
```

## Success Metrics (V2 - Achieved)

- **Intelligent Scoring**: 115-point system with A/B/C/D/F grading
- **High-Quality Sources**: Robotics source yields 10 B+ grade jobs vs 0 from LinkedIn/Supra
- **Location Filtering**: Remote/Hybrid Ontario jobs prioritized (+15 points)
- **Noise Reduction**: Notifications only for A/B grade jobs (80+)
- **Weekly Automation**: Cron job scrapes 1,092 robotics jobs every Monday
- **Email Digests**: Beautiful HTML email with interactive job table (56KB attachment)
- **Coverage**: 5 excellent matches, 11 good matches in latest digest

## Current Performance

**Latest Digest (Oct 22, 2025)**:
- 50 total jobs processed
- 5 excellent matches (80+ score)
- 11 good matches (70+ score)
- Top match: 87/115 (A grade) - Director of Engineering @ Robotics Company
- Email delivered to wesvanooyen@gmail.com with full HTML attachment

## Future Roadmap

### V3: Full Automation (Planned)
- Semi-automated application submission
- AI-powered resume customization
- Interview preparation automation
- Configurable scoring weights (Issue #4)
- Daily digest emails (Issue #3)

## Technical Details

### Database Schema (`data/jobs.db`)
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,           -- linkedin, supra_newsletter, robotics_deeptech_sheet
    type TEXT,             -- direct_job, funding_lead
    company TEXT,
    title TEXT,
    location TEXT,
    link TEXT,
    keywords_matched TEXT, -- JSON array
    received_at TEXT,
    fit_score INTEGER,     -- 0-115 points
    fit_grade TEXT,        -- A, B, C, D, F
    score_breakdown TEXT,  -- JSON object with category scores
    research_notes TEXT,
    UNIQUE(title, company, link)  -- SHA256 deduplication
);
```

### Candidate Profile (Wesley van Ooyen)
- **Background**: Robotics/hardware executive, 11 patents, IoT/MedTech experience
- **Target Roles**: VP/Director/Head of Engineering or Product
- **Domains**: Robotics, automation, hardware, IoT, MedTech, mechatronics
- **Location**: Remote (US/anywhere), Hybrid Ontario (Toronto/Waterloo/Burlington)
- **Role Preference**: Engineering leadership > Product leadership

### Configuration Files
- `config/email-settings.json` - IMAP credentials and email settings
- `config/filter-keywords.json` - Include/exclude keyword lists
- `config/notification-settings.json` - Twilio SMS + email settings
- `config/parsers.json` - Email parser configurations
- `.env` - Environment variables (Gmail app password, Twilio credentials)

### Key Patterns
- Python-based automation over n8n workflows
- Profile-driven scoring over keyword filtering
- Location-aware job matching
- A/B grade notifications only (reduce noise)
- Weekly automation with cron
- Interactive HTML reports over plain text
- Manual oversight with intelligent assistance