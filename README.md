# Job Discovery & Application Automation

An intelligent job discovery and scoring system for robotics/hardware executives with automated email processing, web scraping, and personalized job matching.

## Project Overview

This system automates job discovery for Wesley van Ooyen (robotics/hardware executive) using a 115-point intelligent scoring system, automated web scraping of 1,092+ robotics jobs weekly, and multi-source email processing. The system filters noise by notifying only on A/B grade matches (80+ points) and delivers weekly email digests with top opportunities.

**Key Achievement**: Latest digest delivered 5 excellent matches (80+) and 11 good matches (70+) from 50+ processed jobs.

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
Multi-factor 115-point scoring system evaluating jobs against Wesley's profile:
- **Seniority** (0-30): VP/Director/Head of roles score highest
- **Domain** (0-25): Robotics, hardware, automation, IoT, MedTech
- **Role Type** (0-20): Engineering leadership > Product leadership
- **Location** (0-15): Remote (+15), Hybrid Ontario (+15), Ontario cities (+12)
- **Company Stage** (0-15): Series A-C, growth stage preferred
- **Company Fit** (±20): Hardware boost (+10) or software penalty (-20)
- **Technical Keywords** (0-10): Mechatronics, embedded, manufacturing

**Grading**: A (98+), B (80+), C (63+), D (46+), F (<46)

**Company Classification Filtering**: Intelligent filtering reduces software engineering roles while preserving hardware/robotics opportunities. Three aggression levels (conservative/moderate/aggressive) control filtering strictness. See `CLAUDE.md` for details.

### 2. Email Processing Pipeline (`src/processor_v2.py`)
1. IMAP monitoring of dedicated Gmail account
2. Email parsing via specialized parsers (LinkedIn, Supra, F6S, Artemis, Built In)
3. Keyword-based filtering (include/exclude lists)
4. Job scoring against candidate profile
5. Job deduplication and SQLite storage
6. Notification triggers for A/B grade jobs only (80+)

### 3. Web Scrapers
- **Robotics Scraper** (`src/jobs/weekly_robotics_scraper.py`): 1,092 jobs from robotics/deeptech Google Sheets
- **Company Monitoring** (`src/jobs/company_scraper.py`): 26+ companies via Firecrawl MCP
- **Unified Workflow** (`src/jobs/weekly_unified_scraper.py`): Single command for all sources

### 4. Email Digest System (`src/send_digest_to_wes.py`)
- Generates HTML email with top-scoring jobs
- Attaches interactive jobs.html file with filtering buttons
- Location-based filtering (Remote/Hybrid/Ontario)
- Tracks sent jobs to prevent duplicate emails

### 5. LinkedIn Connections Matching (`src/utils/connections_manager.py`)
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

### 3. Run Components

**Unified Weekly Scraper (Recommended)**:
```bash
# All sources: emails + robotics + company monitoring
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py

# Email only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --email-only

# Company monitoring only
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --companies-only
```

**Individual Components**:
```bash
# Email processor
job-agent-venv/bin/python src/processor_v2.py --fetch-emails --limit 50

# Robotics scraper
job-agent-venv/bin/python src/jobs/weekly_robotics_scraper.py --min-score 70

# Company scraper
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/company_scraper.py --filter "From Wes"
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

**Generate Reports**:
```bash
# Create interactive HTML report
job-agent-venv/bin/python src/generate_jobs_html.py

# Create HTML report with connections for a profile
job-agent-venv/bin/python src/generate_jobs_html.py --profile wes

# Send email digest
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_digest_to_wes.py
```

### 4. Setup Weekly Automation
```bash
# Configure cron job (Monday 9am)
./scripts/setup_unified_weekly_scraper.sh

# View logs
tail -f logs/unified_weekly_scraper.log
```

## Development

### Running Tests
```bash
# Run all tests with coverage
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/test_job_scorer.py -v

# Run with coverage for specific module
PYTHONPATH=$PWD job-agent-venv/bin/pytest tests/unit/ --cov=src/agents --cov-report=term-missing
```

### Code Quality

**Coverage Policy** (Enforced by SonarCloud):
- All new/changed code must have ≥80% test coverage
- Legacy code: 17% (doesn't block PRs)
- SonarCloud quality gate checks new code only

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

**jobs table** (`data/jobs.db`):
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,           -- linkedin, supra_newsletter, robotics_deeptech_sheet, etc.
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
    digest_sent_at TEXT,   -- Track sent jobs
    research_notes TEXT,
    UNIQUE(title, company, link)  -- SHA256 deduplication
);
```

## Candidate Profile (Wesley van Ooyen)

- **Background**: Robotics/hardware executive, 11 patents, IoT/MedTech experience
- **Target Roles**: VP/Director/Head of Engineering or Product
- **Domains**: Robotics, automation, hardware, IoT, MedTech, mechatronics
- **Location**: Remote (US/anywhere), Hybrid Ontario (Toronto/Waterloo/Burlington)
- **Role Preference**: Engineering leadership > Product leadership

## Success Metrics

- ✅ Intelligent 115-point scoring system with A/B/C/D/F grading
- ✅ Location-aware filtering (Remote/Hybrid Ontario +15 points)
- ✅ Noise reduction (A/B grade notifications only, 80+)
- ✅ Weekly automation via cron (Monday 9am)
- ✅ Email digests with interactive HTML reports
- ✅ Latest results: 5 excellent matches (80+), 11 good matches (70+)

## Project Roadmap

### ✅ V1: Minimal Viable Product (Completed)
- Email monitoring via IMAP
- Basic keyword filtering
- Instant notifications

### ✅ V2: Enhanced Intelligence (Current)
- Automated company research
- 115-point scoring system
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
- Update email template in `src/send_digest_to_wes.py` (lines 222-238)
