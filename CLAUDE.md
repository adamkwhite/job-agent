# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a job discovery and application automation system built around n8n workflows. The project focuses on automating email-based job alert processing with keyword filtering and instant notifications to meet critical 12-hour application windows.

## Architecture

### Current Implementation (V1)
- **n8n-based workflows** for email processing and automation
- **IMAP email monitoring** for job alert ingestion
- **SQLite database** for job storage and tracking
- **Multi-channel notifications** (SMS via Twilio, email via SMTP)
- **Self-hosted deployment** on Hostinger VPS

### Project Structure
- `n8n-workflows/` - Exportable n8n workflow JSON files
- `config/` - Configuration files, keyword lists, templates
- `scripts/` - Setup, deployment, and maintenance scripts
- `docs/setup/` - Installation and configuration documentation
- `tests/` - Test data and validation scripts
- `data/` - SQLite databases and job data storage
- `logs/` - Application and workflow logs
- `backup/` - Backup files and workflow exports

## Key Components

### Email Processing Pipeline
1. IMAP monitoring of dedicated Gmail account
2. Email parsing to extract job details (title, company, link)
3. Keyword-based filtering (include/exclude lists)
4. Job deduplication and storage
5. Notification triggers for relevant matches

### Filtering System
- **Include keywords**: Configurable positive matching terms
- **Exclude keywords**: Configurable negative filtering terms
- **Company targeting**: Specific company inclusion/exclusion
- **Role focus**: Target specific job functions and levels

### Notification System
- **Speed requirement**: 30-minute notification window
- **Multi-channel**: SMS and email alerts
- **Rich content**: Job details, application links, company info

## Development Commands

This is primarily an n8n workflow project with supporting configuration:

- **n8n workflows**: Export/import via n8n web interface
- **Configuration**: Edit JSON/YAML files in `config/`
- **Deployment**: Shell scripts in `scripts/` directory
- **Testing**: Manual validation scripts in `tests/`

## Success Metrics (V1)

- Notification speed: Within 30 minutes of job posting
- Filtering accuracy: 90%+ relevant job identification
- Coverage: Zero missed opportunities from target companies
- Efficiency: 50% reduction in manual research time

## Future Roadmap

### V2: Enhanced Intelligence
- Automated company research via APIs
- Scoring system for opportunity ranking
- Enhanced email digests with company intelligence

### V3: Full Automation
- Semi-automated application submission
- AI-powered resume customization
- Interview preparation automation

## Technical Constraints

- **12-hour application window**: Critical timing requirement
- **Cost optimization**: Target $9-17/month for V1
- **Self-hosted**: Hostinger VPS deployment
- **Reliability**: Must handle 10-15 daily email alerts consistently

## Configuration Management

- Email credentials and IMAP settings
- Keyword lists for filtering
- Notification preferences and contacts
- Company research preferences (V2+)
- Scoring weights and criteria (V2+)

## Key Patterns

- Workflow-based automation over traditional coding
- Configuration-driven filtering and targeting
- Incremental enhancement from V1 → V2 → V3
- Manual oversight with automation assistance
- Cost-conscious architecture decisions