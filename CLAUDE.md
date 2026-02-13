# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job discovery automation for multiple user profiles (Wes, Adam, Eli). Features intelligent scoring, automated scraping, and personalized email digests.

## Architecture

- **Email processors**: LinkedIn, Supra, F6S, Artemis, Built In, Ministry of Testing
- **Company monitoring**: Firecrawl-based scraping of robotics/deeptech companies
- **Scoring**: 100-point system with multi-profile scoring and per-profile filtering (Issue #258 fix)
- **LLM extraction**: Dual regex+LLM via Claude 3.5 Sonnet ($15/month budget)
- **Database**: SQLite with multi-profile scoring and deduplication
- **Notifications**: A/B grade jobs (70+) only
- **Automation**: Weekly cron jobs

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

Multi-factor scoring system (0-100 base points, max 110 with bonuses) evaluating jobs against profile preferences:
- **Seniority** (0-30): **Relative scoring** - jobs matching candidate's target_seniority get 30pts, one level away gets 25pts, two levels gets 15pts, etc. (Issue #244)
- **Domain** (0-25): Profile-specific domain keywords (e.g., Robotics, hardware, automation, IoT, MedTech)
- **Role Type** (0-20): Profile-specific role types, with +2 bonuses per matched keyword
- **Location** (0-15): Remote (+15), Hybrid Ontario (+15), Ontario cities (+12)
- **Technical Keywords** (0-10): Profile-specific technical keywords
- **Company Classification** (±20): Hardware boost (+10) or software penalty (-20)

**Grading**: A (85+), B (70+), C (55+), D (40+), F (<40)

#### Relative Seniority Scoring (Issue #244)

The scoring system uses **relative seniority matching** based on each candidate's `target_seniority` preferences:

**Seniority Hierarchy** (9 levels):
- **Level 0**: Junior, Entry-level, Intern, Associate
- **Level 1**: Mid-level, Engineer, Analyst, Specialist (IC without "senior")
- **Level 2**: Senior, Staff, Principal
- **Level 3**: Lead, Team Lead, Tech Lead
- **Level 4**: Architect, Distinguished, Fellow
- **Level 5**: Manager, Engineering Manager
- **Level 6**: Director, Senior Manager, Group Manager
- **Level 7**: VP, Vice President, Head of, Executive Director
- **Level 8**: Chief, CTO, CPO, CEO

**Scoring Logic**:
- **Perfect match** to target level: 30 points
- **One level away**: 25 points (stretch opportunity or slightly junior)
- **Two levels away**: 15 points
- **Three levels away**: 10 points
- **Four+ levels away**: 5 points

**Examples**:
- **Mario** (targets "senior, staff, lead") → "Senior QA Engineer" = 30pts, "Lead QA" = 30pts, "QA Manager" = 25pts, "Director QA" = 15pts
- **Wes** (targets "director, vp, head of") → "Director of Engineering" = 30pts, "VP Engineering" = 30pts, "Senior Manager" = 25pts
- **Adam** (targets "senior, staff, principal") → "Staff Engineer" = 30pts, "Principal Engineer" = 30pts, "Lead Engineer" = 25pts

This ensures all candidates receive equal scoring for jobs matching **their** target level, eliminating the previous bias toward executive roles.

#### Company Classification Filtering (Issue #122)

The scoring engine includes intelligent filtering to reduce software engineering roles while preserving hardware/robotics opportunities:

**Multi-Signal Classification:**
- Analyzes company name, curated database, domain keywords, and job content
- Returns type (software/hardware/both/unknown) with confidence score (0-1.0)
- Performance: <100ms classification, <200ms full scoring

**Three Aggression Levels:**
1. **Conservative**: Only filters explicit "software engineering" keywords in job title
   - Use when you want maximum coverage, minimal false negatives
   - Example: "VP Engineering" at Stripe → NOT filtered

2. **Moderate** (default): Filters engineering roles at software companies (confidence ≥0.6)
   - Balanced approach for most users
   - Example: "Director of Engineering" at Stripe → filtered

3. **Aggressive**: Filters any engineering role without hardware keywords
   - Use when you only want hardware/robotics roles
   - Example: "VP Engineering" at any company → filtered (unless "hardware" in title)

**Filtering Rules:**
- Product leadership NEVER filtered (any company type)
- Dual-role titles (Product Engineering) treated as product leadership
- Dual-domain companies (Tesla) require explicit software keywords to filter
- Hardware companies receive +10 boost, never filtered

**Configuration** (in profile JSON):
```json
"filtering": {
  "aggression_level": "moderate",
  "software_engineering_avoid": [
    "software engineer", "software engineering",
    "vp of software", "director of software",
    "frontend", "backend", "full stack"
  ],
  "hardware_company_boost": 10,
  "software_company_penalty": -20
}
```

**Classification Metadata:**
Each scored job includes classification metadata:
- `company_type`: software, hardware, both, or unknown
- `confidence`: 0-1.0 score based on signal strength
- `signals`: which signals contributed (name, curated, domain, content)
- `source`: curated_db, multi_signal, or name_pattern
- `filtered`: boolean indicating if job was filtered
- `filter_reason`: explanation of filtering decision

### 2. Email Processing Pipeline (`src/processor_v2.py`)
1. IMAP monitoring of dedicated Gmail account
2. Email parsing to extract job details (title, company, link, location)
3. Keyword-based filtering (include/exclude lists)
4. **Multi-profile scoring** - Each job scored for ALL enabled profiles (stored in `job_scores` table)
5. Job deduplication and storage
6. Notification triggers for A/B grade jobs only (70+)

**Supported Sources**: LinkedIn, Supra Product Leadership Jobs, F6S, Artemis, Built In

**Architecture (Issue #184)**: Scraping is now decoupled from scoring. Jobs are scraped once and automatically scored for all profiles.

### 3. Email Digest System (`src/send_profile_digest.py`)
- Generates HTML email with top-scoring jobs
- Attaches interactive jobs.html file (56KB)
- Location-based filtering buttons (Remote/Hybrid/Ontario)
- Sent to wesvanooyen@gmail.com with scoring breakdowns

### 4. LinkedIn Connections Matching (Issue #134)
Shows "👥 You have X connections" in digests. Upload CSV via `scripts/upload_connections.py --profile <name> ~/Downloads/Connections.csv`. Automatically included in digests/HTML reports. Files gitignored for privacy.

### 5. Unified Weekly Scraper (`src/jobs/weekly_unified_scraper.py`) **RECOMMENDED**
Combines ALL job sources into one automated workflow:
- **Email processing** (LinkedIn, Supra, F6S, Artemis, Built In, etc.)
- **Company monitoring** (robotics/deeptech companies via Firecrawl)

**Single inbox mode**:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile <wes|adam|eli|mario>
```

**Multi-inbox mode** (`--all-inboxes`):
Processes ALL profiles with configured email credentials in one command:
```bash
# Process all inboxes + companies + ministry
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --all-inboxes

# Only emails from all inboxes
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --all-inboxes --email-only

# Only companies (no emails)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --all-inboxes --companies-only
```

**How it works (Issue #184 - Decoupled Architecture)**:
- `--profile` flag determines **which email inbox to connect to** for scraping
- `--all-inboxes` flag processes **ALL configured email inboxes sequentially** (Wes, Adam, etc.)
- Jobs are **automatically scored for ALL profiles** (not just the specified profile)
- Each job stored once in `jobs` table, with scores in `job_scores` table
- Companies/Ministry scraped ONCE (shared resources)

**Key features**:
- Single command runs all sources
- Multi-profile scoring (all profiles scored automatically)
- Multi-inbox support for simplified automation
- Configurable thresholds per source
- Comprehensive stats and logging
- Cron-friendly for weekly automation

**Scoring thresholds**:
- Emails: All passing filter
- Companies: D+ grade (50+) ← Lower threshold for more options

### 6. Company Monitoring (`src/jobs/company_scraper.py`)
- Scrapes robotics/deeptech companies' career pages for leadership roles
- Uses Firecrawl MCP for JavaScript-heavy pages
- Stores D+ grade jobs (50+) to capture more opportunities
- Tracks last_checked timestamps
- Sends notifications for A/B grade jobs (70+)

### 7. LLM Extraction Pipeline (PRODUCTION)
Dual regex+LLM extraction via Claude 3.5 Sonnet. Finds jobs regex misses (e.g., non-standard formats). $15/month budget, 30s timeout. Config: `config/llm-extraction-settings.json`. Toggle with `"enabled": true/false`.

### 8. Independent Re-scoring Utility (`src/utils/rescore_jobs.py`) **Issue #184 Phase 4**
Re-score existing jobs without re-scraping. Useful for:
- Profile configuration changes (target seniority, keywords, etc.)
- Scoring algorithm updates
- Backfilling scores for new profiles
- Testing scoring changes before deploying

```bash
# Re-score last 7 days for all profiles
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode recent --days 7

# Re-score specific date range
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode date-range --start-date 2024-01-01 --end-date 2024-01-31

# Backfill scores for new profile (e.g., Mario)
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode backfill --profile mario --max-jobs 500

# Re-score specific company
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode company --company Tesla

# Dry run (preview changes)
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode recent --days 7 --dry-run
```

**Key features**:
- Re-scores without re-scraping (preserves API credits)
- Shows significant score changes (Δ ≥ 10 points)
- Supports selective re-scoring by date, company, or profile
- Dry-run mode for testing

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

**Recommended:** Use TUI for interactive workflow
```bash
./run-tui.sh
```

**📖 For detailed TUI workflow guide (sources-first architecture), see: [`docs/development/TUI_WORKFLOW.md`](docs/development/TUI_WORKFLOW.md)**

**Quick TUI Overview:**
- **Step 1**: Select sources (companies, email, ministry) - profile-agnostic
- **Step 2**: Select action (scrape, digest, or both)
- **Step 3**: Run scraper (if needed)
- **Step 4**: Select digest recipients (multi-select: 1,2 or "all")
- **Step 5**: Digest options (production, dry-run, force-resend)
- **Step 6**: Confirm & execute

**Key benefits**: One scrape → multiple digest recipients. Jobs automatically scored for ALL profiles.

**Weekly Scraper** (all sources, scores for ALL profiles):
```bash
# Single inbox mode
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile <wes|adam|eli|mario>
# --profile determines email inbox to scrape; jobs scored for ALL profiles automatically

# Multi-inbox mode (process ALL configured inboxes)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --all-inboxes
# Processes all inboxes (Wes, Adam, etc.) + companies/ministry in one command
```

**Re-score Existing Jobs** (no scraping):
```bash
# Re-score recent jobs
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode recent --days 7

# Backfill new profile
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode backfill --profile mario
```

**Send Digest**:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile <name>
# Add --dry-run for testing, --all for all profiles
```

**Cron Setup**:
```bash
./scripts/setup_unified_weekly_scraper.sh  # Monday 9am automation
./scripts/setup_backup_cron.sh             # Daily 3am database backups
```

## Database Backups

**Automated Tiered Backup System** (runs daily at 3:00 AM):

**Retention Policy:**
- **Daily backups**: Keep 7 days (detailed recent history)
- **Weekly backups**: Keep 4 weeks (created Sundays)
- **Monthly backups**: Keep 3 months (created 1st of month)

**Commands:**
```bash
# Manual backup
./scripts/backup_database.sh

# Setup automated daily backups (cron)
./scripts/setup_backup_cron.sh

# Check backup status
ls -lah data/backups/

# View backup logs
tail -50 logs/database_backup.log

# Restore from backup
cp data/backups/jobs-backup-YYYYMMDD-TYPE.db data/jobs.db
```

**Storage:** Approximately 14MB for ~1MB database (7 daily + 4 weekly + 3 monthly)

**Location:** `data/backups/` (gitignored, not committed)

**⚠️ CRITICAL:** After Issue #236, pytest hooks only run in CI. But backups are still essential for:
- Accidental deletions
- Corruption recovery
- Rollback after bad data imports
- Historical snapshots


## Technical Details

### Database Schema (`data/jobs.db`)
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,           -- linkedin, supra_newsletter, builtin, f6s, artemis, company_monitoring
    type TEXT,             -- direct_job, funding_lead
    company TEXT,
    title TEXT,
    location TEXT,
    link TEXT,
    keywords_matched TEXT, -- JSON array
    received_at TEXT,
    fit_score INTEGER,     -- 0-110 points (100 base + adjustments)
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

**Key Features (Issue #184 - Decoupled Architecture)**:
- **Scraping**: Profile flag determines which email inbox to connect to
- **Scoring**: Jobs automatically scored for ALL enabled profiles (stored in `job_scores` table)
- **Digests**: Sent separately to each profile with personalized matches
- **Database**: Single `jobs` table, multi-profile scores in `job_scores` table
- **Re-scoring**: Independent utility allows updating scores without re-scraping
- **TUI**: Automatically loads all enabled profiles (no code changes needed)

**📖 To add a new profile, see the step-by-step guide: [`docs/development/ADDING_NEW_PROFILES.md`](docs/development/ADDING_NEW_PROFILES.md)**

**📖 For multi-profile system architecture, see: [`docs/development/MULTI_PROFILE_GUIDE.md`](docs/development/MULTI_PROFILE_GUIDE.md)**

Quick summary:
1. Create `profiles/yourname.json` with scoring criteria
2. (Optional) Set up `yourname.jobalerts@gmail.com` with app password and add to `.env`
3. Test with `--profile yourname` flag
4. Profile automatically appears in TUI


### Configuration
- `config/` - Email settings, filter keywords, notifications, LLM settings, company classifications
- `.env` - API keys (Gmail, Twilio, OpenRouter)
- `profiles/*.json` - Per-profile scoring criteria and digest settings
