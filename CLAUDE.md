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

**Supported Sources**: LinkedIn, Supra Product Leadership Jobs, F6S, Artemis, Built In

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

### 5. Unified Weekly Scraper (`src/jobs/weekly_unified_scraper.py`) **RECOMMENDED**
Combines ALL job sources into one automated workflow:
- **Email processing** (LinkedIn, Supra, F6S, Artemis, Built In, etc.)
- **Robotics/Deeptech sheet** (1,092 jobs from Google Sheets)
- **Company monitoring** (Wes's 26+ companies via Firecrawl)

```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py
```

**Key features**:
- Single command runs all sources
- Unified scoring and deduplication
- Configurable thresholds per source
- Comprehensive stats and logging
- Cron-friendly for weekly automation

**Scoring thresholds**:
- Emails: All passing filter
- Robotics: B+ grade (70+)
- Companies: D+ grade (50+) ← Lower threshold for more options

### 6. Company Monitoring (`src/jobs/company_scraper.py`)
- Scrapes 26+ companies' career pages for leadership roles
- Uses Firecrawl MCP for JavaScript-heavy pages
- Stores D+ grade jobs (50+) to capture more opportunities
- Tracks last_checked timestamps
- Sends notifications for A/B grade jobs (80+)

## Testing & Coverage Requirements

**Coverage Policy (Enforced by SonarCloud):**
- **All new code MUST have ≥80% test coverage** (enforced by SonarCloud quality gate)
- Legacy code coverage is currently 17%, but this does NOT block PRs
- SonarCloud only checks coverage on NEW/CHANGED code in PRs

**Writing Tests:**
- Place tests in `tests/unit/` directory
- Follow existing test patterns (see `tests/unit/test_company_service.py` for reference)
- Use `pytest` fixtures for test setup
- Mock external dependencies (APIs, databases, file I/O)
- Test both success and failure cases

**Running Tests Locally:**
```bash
# Run all tests with coverage
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_company_matcher.py -v

# Run with coverage for specific module
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/ --cov=src/utils/company_matcher --cov-report=term-missing
```

**Pre-Commit Hooks:**
The project uses pre-commit hooks to enforce code quality before commits:
- Ruff linting and formatting
- mypy type checking
- Bandit security scanning
- File validation (trailing whitespace, end-of-file, JSON/YAML validation)

To skip hooks temporarily (use sparingly):
```bash
SKIP=python-safety-dependencies-check git commit -m "message"
```

## Development Commands

### Run Unified Weekly Scraper (RECOMMENDED)
```bash
# All sources: emails + robotics + company monitoring
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py

# Email only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --email-only --email-limit 100

# Robotics only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --robotics-only --robotics-min-score 70

# Company monitoring only (Wes's 26 companies)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --companies-only --company-filter "From Wes"
```

### Run Individual Components (Legacy)
```bash
# Email processors only
job-agent-venv/bin/python src/processor_v2.py --fetch-emails --limit 50

# Robotics scraper only
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 70

# Company scraper only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/company_scraper.py --filter "From Wes"
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
# Send to Wesley (only unsent jobs)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_digest_to_wes.py

# Force resend all jobs (for testing)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_digest_to_wes.py --force-resend

# Send copy to Adam
job-agent-venv/bin/python src/send_digest_copy.py
```

**Digest Tracking**: The system automatically tracks which jobs have been sent in previous digests using the `digest_sent_at` field. Running the script multiple times will only send new jobs, preventing duplicate emails.

### Cron Setup (Weekly Automation)
```bash
# Setup unified weekly scraper (Monday 9am) - RECOMMENDED
./scripts/setup_unified_weekly_scraper.sh

# View cron jobs
crontab -l

# View logs
tail -f logs/unified_weekly_scraper.log

# Test manually
./scripts/run_unified_scraper.sh
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

### Email Parser Implementation Details

#### Built In Parser (`src/parsers/builtin_parser.py`)
Parses Built In job alert emails with unique challenges:

**AWS Tracking URLs**: Built In wraps job URLs in AWS tracking links with URL-encoded paths:
```python
# Example: https://cb4sdw3d.r.us-west-2.awstrack.me/L0/https:%2F%2Fbuiltin.com%2Fjob%2F...
# Pattern must match both plain and encoded paths
soup.find_all("a", href=re.compile(r"builtin\.com(%2F|/)job(%2F|/)"))
```

**Style-Based HTML Parsing**: Built In uses inline styles instead of semantic classes:
```python
# Company: font-size:16px, margin-bottom:8px
# Title: font-size:20px, font-weight:700
# Location/Salary: Identified by LocationIcon/SalaryIcon images
```

**URL Cleaning**: Decode URL-encoded characters and strip query params:
```python
url.replace("%2F", "/").replace("%3F", "?").split("?")[0]
```

**Detection Logic**:
- `"builtin" in from_addr` or `"support@builtin.com" in from_addr`
- `"job" and "match" and "product" in subject`

**Type Hint Fix**: Added `from __future__ import annotations` to `src/imap_client.py` to enable forward references for `email.message.Message` type hints in Python 3.9+.

### Configuration Files
- `config/email-settings.json` - IMAP credentials and email settings
- `config/filter-keywords.json` - Include/exclude keyword lists
- `config/notification-settings.json` - Twilio SMS + email settings
- `config/parsers.json` - Email parser configurations (includes builtin parser)
- `.env` - Environment variables (Gmail app password, Twilio credentials)

### Key Patterns
- Python-based automation over n8n workflows
- Profile-driven scoring over keyword filtering
- Location-aware job matching
- A/B grade notifications only (reduce noise)
- Weekly automation with cron
- Interactive HTML reports over plain text
- Manual oversight with intelligent assistance
