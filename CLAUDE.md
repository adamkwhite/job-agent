# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a job discovery and application automation system for Wesley van Ooyen (robotics/hardware executive). The project has evolved from n8n workflows to Python-based email processing with intelligent job scoring, automated web scraping, and personalized email digests.

## Architecture

### Current Implementation (V2 - Enhanced Intelligence)
- **Python-based email processors** for LinkedIn, Supra, F6S, Artemis newsletters
- **Automated web scraping** of robotics/deeptech job boards (1,092 jobs weekly)
- **Intelligent job scoring** (115-point system) against candidate profile
- **LLM extraction pipeline** (experimental) - Dual regex+LLM extraction via Claude 3.5 Sonnet
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
  - `src/extractors/` - LLM extraction and comparison tools
  - `src/api/` - LLM budget tracking service
  - `src/enrichment/` - Company research pipeline
- `config/` - Configuration files, keyword lists, templates, LLM settings
- `scripts/` - Setup, deployment, and cron scripts
- `docs/` - Documentation, PRDs, research guides
- `tests/` - Test fixtures and validation scripts
- `data/` - SQLite database (jobs.db) and job storage
- `logs/` - Application and scraper logs
- `requirements.txt` - Python dependencies

## Key Components

### 1. Job Scoring Engine (`src/agents/job_scorer.py`)

⚠️ **When updating scoring criteria, follow the checklist:** `docs/development/SCORING_UPDATE_CHECKLIST.md`

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
**Phase 1: Google Sheets**
- Scrapes 1,092 jobs from robotics/deeptech Google Sheets
- Filters for Director+ leadership roles
- Scores and stores B+ grade jobs (70+)
- Runs weekly via cron (Monday 9am)

**Phase 2: Firecrawl Generic Career Pages** (Issue #65, PR #71)
- Semi-automated workflow for 10 priority companies with generic career pages
- Priority companies: Boston Dynamics, Figure, Sanctuary AI, Agility Robotics, 1X Technologies, Skydio, Skild AI, Dexterity, Covariant, Nuro
- Outputs Firecrawl MCP commands for manual execution
- Markdown processor extracts leadership jobs from scraped pages
- Budget tracking: 50 credits/week (~$20/month)
- Failure monitoring with 50% threshold
- Expected to discover 25-50+ additional leadership jobs/week
- Config: `config/robotics_priority_companies.json`

### 4. Email Digest System (`src/send_profile_digest.py`)
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

### 7. LLM Extraction Pipeline (`src/extractors/llm_extractor.py`) **EXPERIMENTAL**
**Status:** IN PROGRESS - Core pipeline complete, validation ongoing

Dual extraction system running regex AND LLM-based job extraction in parallel:
- **Model:** Claude 3.5 Sonnet via OpenRouter API
- **Budget:** $5/month limit ($0.01 per company, ~500 companies/month)
- **Timeout:** 30 seconds per company (NFR1 requirement)
- **Extraction Method Tagging:** Each job tagged with 'regex' or 'llm' in database
- **Deduplication:** Database hash prevents duplicate storage across methods
- **Graceful Degradation:** LLM failures don't break pipeline, regex continues

**Key Features:**
- Finds jobs regex misses (e.g., Figure AI's `[Title](url)` format)
- Budget tracking via `logs/llm-budget-YYYY-MM.json`
- TUI "Advanced Options" step for user-friendly enablement
- Visual indicators: 📝 Regex vs 🤖 LLM in output

**Configuration:**
- `config/llm-extraction-settings.json` - Model, prompts, budget, timeout
- `OPENROUTER_API_KEY` environment variable required

**Usage:**
```bash
# Via TUI (recommended)
./run-tui.sh
# Select "Companies" source, then enable in Advanced Options

# Via CLI flag
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes --llm-extraction
```

**Production Validation (2025-12-07):**
- ✅ 60 companies processed, $0.60 cost (88% budget remaining)
- ✅ Found 3 leadership jobs from Figure AI that regex missed
- ✅ Correctly deduplicated overlapping results
- ✅ Graceful handling of LLM failures (0 jobs found)

**Related:**
- PRD: `docs/features/llm-job-extraction-IN_PROGRESS/prd.md`
- Issues: [#87](https://github.com/adamkwhite/job-agent/issues/87) (DB), [#88](https://github.com/adamkwhite/job-agent/issues/88) (Core), [#89](https://github.com/adamkwhite/job-agent/issues/89) (Budget), [#90](https://github.com/adamkwhite/job-agent/issues/90) (Pipeline)
- PRs: [#111](https://github.com/adamkwhite/job-agent/pull/111), [#112](https://github.com/adamkwhite/job-agent/pull/112), [#113](https://github.com/adamkwhite/job-agent/pull/113)

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
# For Wes (all sources: emails + robotics + company monitoring)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes

# For Adam (all sources)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam

# Email only (profile-specific inbox)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam --email-only --email-limit 100

# Robotics only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes --robotics-only --robotics-min-score 70

# Company monitoring only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes --companies-only --company-filter "From Wes"

# Without profile (uses legacy .env GMAIL_USERNAME)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py
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
# Send to Wes (only unsent jobs for his profile)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile wes

# Send to Adam (only unsent jobs for his profile)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile adam

# Send to all enabled profiles
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --all

# Test digest without sending (dry run)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile adam --dry-run

# Force resend all jobs (for testing)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile wes --force-resend
```

**Digest Tracking**: The system automatically tracks which jobs have been sent to each profile using the `job_scores.digest_sent_at` field. Running the script multiple times will only send new jobs to each person, preventing duplicate emails. Each profile maintains separate digest tracking.

### Interactive TUI (Easiest Method)
```bash
# Launch the interactive terminal UI
./run-tui.sh
# or
job-agent-venv/bin/python src/tui.py
```

**Features**:
- Select profile (Wes or Adam)
- Choose sources to scrape (Email, Robotics sheet, Company monitoring)
- Pick action (Scrape only, Send digest, or Both)
- View scoring criteria for each profile
- Profile-specific email inbox display
- Confirmation before execution

The TUI automatically passes the correct `--profile` flag to the scraper and shows profile-specific information throughout the workflow.

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

### Multi-Profile System

The job agent supports multiple user profiles with separate email accounts, scoring criteria, and digest settings.

**Current Profiles**:
- **Wes** (`profiles/wes.json`) - VP/Director roles in Robotics/Hardware
- **Adam** (`profiles/adam.json`) - Senior/Staff roles in Software/Product
- **Eli** (`profiles/eli.json`) - Director/VP/CTO roles in Fintech/Healthtech/PropTech

**Key Features**:
- Jobs scraped from profile-specific email inboxes (or digest-only for profiles without inbox)
- Each job scored for ALL enabled profiles (stored in `job_scores` table)
- Digests sent separately to each profile with personalized matches
- Database tracks which inbox jobs came from (`jobs.profile` column)
- TUI automatically loads all enabled profiles (no code changes needed)

**📖 To add a new profile, see the step-by-step guide: [`docs/development/ADDING_NEW_PROFILES.md`](docs/development/ADDING_NEW_PROFILES.md)**

**📖 For multi-profile system architecture, see: [`docs/development/MULTI_PROFILE_GUIDE.md`](docs/development/MULTI_PROFILE_GUIDE.md)**

Quick summary:
1. Create `profiles/yourname.json` with scoring criteria
2. (Optional) Set up `yourname.jobalerts@gmail.com` with app password and add to `.env`
3. Test with `--profile yourname` flag
4. Profile automatically appears in TUI

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
