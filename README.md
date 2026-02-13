# Job Discovery & Application Automation

An intelligent job discovery and scoring system for multiple user profiles with automated email processing, web scraping, and personalized job matching.

## Project Overview

This system automates job discovery for multiple professionals (Wes, Adam, Eli, Mario) using a 100-point intelligent scoring system (max 110 with bonuses), automated web scraping of 1,000+ jobs weekly, and multi-source email processing. The system filters noise by notifying only on A/B grade matches (70+ points) and delivers weekly email digests with top opportunities personalized to each profile.

**Key Features**: Multi-profile support with profile-specific scoring, interactive TUI for workflow management, automated company monitoring, and LinkedIn connection matching.

**Key Achievement**: Latest digest delivered 5 excellent matches (70+) and 11 good matches (55+) from 50+ processed jobs.

## Technology Stack

- **Language**: Python 3.12+
- **Database**: SQLite with SQLAlchemy
- **Web Scraping**: BeautifulSoup4, lxml, Firecrawl, Playwright
- **Email Processing**: IMAP client with custom parsers
- **Notifications**: Twilio (SMS) + SMTP (email)
- **Testing**: pytest, pytest-cov, pytest-mock
- **Code Quality**: Ruff, mypy, Bandit, pre-commit hooks
- **CI/CD**: GitHub Actions with SonarCloud integration

## Architecture (V2 - Current)

### 1. Job Scoring Engine (`src/agents/job_scorer.py`)
Multi-factor 100-point base scoring system (max 110 with bonuses) with **multi-profile support**:
- **Seniority** (0-30): Relative scoring based on each profile's target levels (Issue #244)
- **Domain** (0-25): Profile-specific domain keywords (Robotics, hardware, fintech, etc.)
- **Role Type** (0-20): Profile-specific role preferences with +2 bonuses per matched keyword
- **Location** (0-15): Remote (+15), Hybrid Ontario (+15), Ontario cities (+12)
- **Technical Keywords** (0-10): Profile-specific technical skills
- **Company Classification** (±20): Hardware boost (+10) or software penalty (-20)

**Grading**: A (85+), B (70+), C (55+), D (40+), F (<40)

**Multi-Profile Scoring (Issue #184)**: Jobs are automatically scored for ALL enabled profiles. Each job gets personalized scores based on individual profile preferences, stored in the `job_scores` table.

**Company Classification Filtering**: Intelligent filtering reduces software engineering roles while preserving hardware/robotics opportunities. Three aggression levels (conservative/moderate/aggressive) control filtering strictness. See `CLAUDE.md` for details.

### 2. Email Processing Pipeline (`src/processor_v2.py`)
1. IMAP monitoring of profile-specific Gmail accounts
2. Email parsing via specialized parsers (LinkedIn, Supra, F6S, Artemis, Built In)
3. Keyword-based filtering (include/exclude lists)
4. **Multi-profile scoring** - Jobs scored for ALL enabled profiles automatically
5. Job deduplication and SQLite storage
6. Notification triggers for A/B grade jobs only (70+)

### 3. Web Scrapers
- **Company Monitoring** (`src/jobs/company_scraper.py`): 68 robotics/deeptech companies via Firecrawl MCP
- **Ministry of Testing** (`src/jobs/ministry_scraper.py`): QA/testing job board
- **Unified Workflow** (`src/jobs/weekly_unified_scraper.py`): Single command for all sources with multi-profile scoring

### 4. Email Digest System (`src/send_profile_digest.py`)
- **Profile-specific digests** with personalized job matches
- Generates HTML email with top-scoring jobs for each profile
- Attaches interactive jobs.html file with filtering buttons
- Location-based filtering (Remote/Hybrid/Ontario)
- **Profile-specific tracking** - Same job can be sent to multiple profiles independently
- LinkedIn connection matching (shows "👥 You have X connections" in digests)

### 5. Interactive TUI (`src/tui.py`)
**Recommended workflow management interface** with sources-first architecture:
- **Step 1**: Select sources (companies, email, ministry) - profile-agnostic
- **Step 2**: Select action (scrape, digest, or both)
- **Step 3**: Run scraper (if needed)
- **Step 4**: Select digest recipients (multi-select or "all")
- **Step 5**: Digest options (production, dry-run, force-resend)
- **Step 6**: Confirm & execute

**Key Benefits**: One scrape → multiple digest recipients, clear separation of scraping scope and digest recipients.

**Launch TUI**: `./run-tui.sh` or `PYTHONPATH=$PWD job-agent-venv/bin/python src/tui.py`

**Full Documentation**: [`docs/development/TUI_WORKFLOW.md`](docs/development/TUI_WORKFLOW.md)

### 6. LinkedIn Connections Matching (`src/utils/connections_manager.py`)
- Load LinkedIn connections CSV export
- Match connections to job companies using fuzzy matching
- Display connection counts and names in email digests
- Show detailed connection info in HTML reports
- Profile-specific connections storage (`data/profiles/{profile}/connections.csv`)

## Project Structure

```
job-agent/
├── src/                    # Python application source
│   ├── agents/             # Job scoring engine
│   ├── jobs/               # Weekly scrapers and automation
│   ├── scrapers/           # Email parsers and web scrapers
│   ├── parsers/            # Email parser implementations
│   ├── enrichment/         # Company research pipeline
│   ├── models/             # Data models
│   ├── utils/              # Utility functions
│   └── api/                # API endpoints
├── config/                 # Configuration files and templates
│   ├── email-settings.json
│   ├── filter-keywords.json
│   ├── notification-settings.json
│   └── parsers.json
├── scripts/                # Setup and deployment scripts
├── docs/                   # Documentation and PRDs
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── fixtures/           # Test data
├── data/                   # SQLite database (jobs.db)
├── logs/                   # Application logs
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
└── .pre-commit-config.yaml # Pre-commit hooks
```

## Quick Start

### 1. Environment Setup
```bash
# Create virtual environment (Python 3.12+ required)
python3.12 -m venv job-agent-venv
source job-agent-venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

### 2. Configuration
```bash
# Create .env file with credentials
cp .env.example .env
# Edit .env with Gmail app password, Twilio credentials, etc.

# Configure email settings
vim config/email-settings.json

# Customize keyword filters
vim config/filter-keywords.json
```

### 3. Setup Automated Database Backups (CRITICAL)

**⚠️ IMPORTANT:** After losing 7 weeks of data (Dec 11 - Jan 31) when pytest hooks deleted the production database, automated backups are now MANDATORY.

```bash
# Install daily backup cron job (runs at 3:00 AM)
./scripts/setup_backup_cron.sh

# Manual backup anytime
./scripts/backup_database.sh

# Check backup status
ls -lah data/backups/
tail -20 logs/database_backup.log
```

**Tiered Retention Policy:**
- 📅 Daily backups: Keep 7 days (detailed recent history)
- 📅 Weekly backups: Keep 4 weeks (Sundays only)
- 📅 Monthly backups: Keep 3 months (1st of month)
- 💾 Total storage: ~14MB (for 1MB database)

**Restore from backup:**
```bash
cp data/backups/jobs-backup-YYYYMMDD-TYPE.db data/jobs.db
```

**Location:** `data/backups/` (gitignored, not committed)

### 4. Run Components

**Interactive TUI (Recommended)**:
```bash
# Launch interactive workflow manager
./run-tui.sh

# Or run directly
PYTHONPATH=$PWD job-agent-venv/bin/python src/tui.py
```

**Benefits**: Sources-first workflow, multi-recipient digests, dry-run testing, utility access (API credits, system health).

**Full TUI Guide**: [`docs/development/TUI_WORKFLOW.md`](docs/development/TUI_WORKFLOW.md)

---

**Unified Weekly Scraper (CLI)**:
```bash
# Single profile inbox mode
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes

# Multi-inbox mode (all configured profiles)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --all-inboxes

# Email only (specific profile)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam --email-only

# Company monitoring only (profile-agnostic)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --companies-only
```

**Note**: `--profile` selects which email inbox to connect to. Jobs are automatically scored for ALL profiles regardless of which inbox is used.

**Individual Components**:
```bash
# Email processor (specific profile)
PYTHONPATH=$PWD job-agent-venv/bin/python src/processor_v2.py --profile wes --fetch-emails --limit 50

# Company scraper (profile-agnostic)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/company_scraper.py --filter "From Wes"

# Ministry of Testing scraper
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/ministry_scraper.py
```

**LinkedIn Connections**:
```bash
# Upload LinkedIn connections CSV for a profile
python scripts/upload_connections.py --profile wes ~/Downloads/Connections.csv

# How to export from LinkedIn:
# 1. Go to https://www.linkedin.com/mypreferences/d/download-my-data
# 2. Select 'Connections'
# 3. Download the Connections.csv file
```

**Generate Reports & Send Digests**:
```bash
# Create HTML report with connections for a profile
PYTHONPATH=$PWD job-agent-venv/bin/python src/generate_jobs_html.py --profile wes

# Send email digest to specific profile
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile wes

# Send digests to all profiles
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --all

# Dry-run (preview without sending)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile adam --dry-run
```

### 5. Setup Weekly Automation
```bash
# Configure cron job (Monday 9am)
./scripts/setup_unified_weekly_scraper.sh

# View logs
tail -f logs/unified_weekly_scraper.log
```

## Development

### Running Tests

**All tests use isolated databases** to prevent production data pollution. See [`docs/development/TESTING.md`](docs/development/TESTING.md) for comprehensive testing guide.

```bash
# Run all tests with coverage
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_job_scorer.py -v

# Run with coverage for specific module
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/ --cov=src/agents --cov-report=term-missing
```

**Database Isolation**: Tests automatically use temporary databases via `DATABASE_PATH` environment variable. Production database (`data/jobs.db`) is never touched during test execution.

### Code Quality

**Coverage Policy** (Enforced by SonarCloud):
- All new/changed code must have ≥80% test coverage
- Legacy code: 17% (doesn't block PRs)
- SonarCloud quality gate checks new code only
- See [`docs/development/TESTING.md`](docs/development/TESTING.md) for writing tests

**Pre-commit Hooks**:
- Ruff linting and formatting
- mypy type checking
- Bandit security scanning
- File validation (trailing whitespace, JSON/YAML validation)

To skip hooks temporarily (use sparingly):
```bash
SKIP=python-safety-dependencies-check git commit -m "message"
```

### Git Workflow

**Branch Strategy** (MANDATORY):
1. Create feature branch: `git checkout -b feature/description`
2. Make changes and test locally
3. Commit with meaningful messages
4. Push branch: `git push -u origin feature/description`
5. Create PR: `gh pr create`
6. Monitor PR checks: `gh pr checks`
7. Wait for approval before merging

**NEVER commit directly to main branch** - even for small fixes.

## Database Schema

**Multi-Profile Database** (`data/jobs.db`):

```sql
-- Jobs table (single source of truth)
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,           -- linkedin, supra_newsletter, company_monitoring, etc.
    type TEXT,             -- direct_job, funding_lead
    company TEXT,
    title TEXT,
    location TEXT,
    link TEXT,
    keywords_matched TEXT, -- JSON array
    received_at TEXT,
    research_notes TEXT,
    UNIQUE(title, company, link)  -- SHA256 deduplication
);

-- Multi-profile scores (Issue #184)
CREATE TABLE job_scores (
    job_id INTEGER,
    profile_id TEXT,
    fit_score INTEGER,     -- 0-110 points (100 base + adjustments)
    fit_grade TEXT,        -- A, B, C, D, F
    score_breakdown TEXT,  -- JSON object with category scores
    scored_at TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id),
    PRIMARY KEY(job_id, profile_id)
);

-- Profile-specific digest tracking (Issue #262)
CREATE TABLE digest_tracking (
    job_id INTEGER,
    profile_id TEXT,
    sent_at TEXT,
    FOREIGN KEY(job_id) REFERENCES jobs(id),
    PRIMARY KEY(job_id, profile_id)
);
```

**Key Features**:
- Jobs stored once, scored for all profiles
- Same job can have different scores per profile
- Same job can be sent to multiple profiles independently

## Multi-Profile Support

The system supports multiple user profiles, each with personalized scoring criteria:

**Supported Profiles** (`profiles/*.json`):
- **Wesley** - VP/Director roles in Robotics/Hardware
- **Adam** - Senior/Staff roles in Software/Product
- **Eli** - Director/VP/CTO roles in Fintech/Healthtech/PropTech
- **Mario** - Senior/Staff/Lead roles in QA Engineering

**Profile Configuration**:
- Profile-specific domain keywords and technical skills
- Relative seniority scoring (Issue #244)
- Individual email accounts for inbox scraping
- Independent digest tracking (same job → multiple profiles)

**Adding Profiles**: See [`docs/development/ADDING_NEW_PROFILES.md`](docs/development/ADDING_NEW_PROFILES.md)

## Success Metrics

- ✅ Intelligent 100-point base scoring system (max 110) with A/B/C/D/F grading
- ✅ Location-aware filtering (Remote/Hybrid Ontario +15 points)
- ✅ Noise reduction (A/B grade notifications only, 70+)
- ✅ Weekly automation via cron (Monday 9am)
- ✅ Email digests with interactive HTML reports
- ✅ Latest results: 5 excellent matches (70+), 11 good matches (55+)

## Project Roadmap

### ✅ V1: Minimal Viable Product (Completed)
- Email monitoring via IMAP
- Basic keyword filtering
- Instant notifications

### ✅ V2: Enhanced Intelligence (Current)
- Automated company research
- 100-point base scoring system (max 110 with bonuses)
- Multi-source web scraping (1,092+ jobs weekly)
- Email parsers for 5+ job sources
- Location-aware filtering
- Weekly email digests

### 🔮 V3: Full Automation (Planned)
- Semi-automated application submission
- AI-powered resume customization
- Interview preparation automation
- Configurable scoring weights
- Daily digest emails

## Documentation

See `docs/` for detailed documentation:
- `docs/features/` - PRDs for planned features
- `docs/development/` - Development guidelines
- `docs/setup/` - Setup and deployment guides
- `CLAUDE.md` - Project context for Claude AI

## License

MIT

## Contributing

This is a personal project, but contributions are welcome. Please:
1. Create feature branch
2. Write tests (≥80% coverage on new code)
3. Run pre-commit hooks
4. Submit PR with clear description

**If updating job scoring criteria:**
- Follow the checklist in `docs/development/SCORING_UPDATE_CHECKLIST.md`
- Use GitHub issue template: `.github/ISSUE_TEMPLATE/scoring-update.md`
- Update email templates in `src/send_profile_digest.py` and profile-specific templates
