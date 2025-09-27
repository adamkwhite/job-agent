# Job Discovery & Application Automation

An automated workflow for discovering, researching, and applying to job opportunities with a focus on mission-driven companies.

## Project Overview

This system automates the job discovery process for professionals, with a critical 12-hour application window to avoid being lost in applicant queues.

## Version Roadmap

### V1: Minimal Viable Product (Current)
- **Email monitoring** via IMAP for job alerts
- **Basic keyword filtering** (include/exclude lists)
- **Instant notifications** for relevant opportunities
- **Manual research and application** prep

### V2: Enhanced Intelligence (Future)
- Automated company research
- Opportunity scoring system
- Enhanced notifications with intelligence

### V3: Full Automation (Future)
- Semi-automated application submission
- AI-powered resume customization
- Interview preparation automation

## Technical Stack (V1)

- **Platform**: Self-hosted n8n on Hostinger VPS
- **Email**: Gmail IMAP integration
- **Database**: SQLite for job storage
- **Notifications**: SMS (Twilio) + Email (SMTP)
- **Parsing**: Basic regex/string matching

## Project Structure

```
├── n8n-workflows/          # n8n workflow JSON exports
├── config/                 # Configuration files and templates
├── scripts/                # Setup and maintenance scripts
├── docs/                   # Documentation and setup guides
├── tests/                  # Test data and validation scripts
├── logs/                   # Application logs
├── data/                   # Job data and databases
└── backup/                 # Backup files and exports
```

## Quick Start

1. **VPS Setup**: Deploy n8n on Hostinger VPS
2. **Email Configuration**: Set up dedicated Gmail account with IMAP
3. **Workflow Import**: Import workflows from `n8n-workflows/`
4. **Filter Configuration**: Customize keywords in `config/`
5. **Notification Setup**: Configure SMS/email alerts

## Key Features

- ⚡ **Fast Notifications**: 30-minute alert window
- 🎯 **Accurate Filtering**: 90%+ relevant job identification
- 📧 **Email Integration**: Monitors 10-15 daily job alerts
- 📱 **Multi-channel Alerts**: SMS + Email notifications
- 🎯 **Focused Targeting**: Customizable company and role criteria

## Success Criteria (V1)

- Notifications arrive within 30 minutes of job posting
- 90%+ accuracy in relevant job identification
- Zero false negatives for target companies
- Manual research time reduced by 50%

## Monthly Costs (V1)

- Hostinger VPS: $4-7/month
- SMS notifications: $5-10/month
- **Total**: $9-17/month

## Getting Started

See `docs/setup/` for detailed installation and configuration guides.