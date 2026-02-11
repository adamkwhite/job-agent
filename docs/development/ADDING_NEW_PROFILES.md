# Adding New Profiles to Job Agent

This guide explains how to add a new job seeker profile to the Job Agent system.

## Overview

The Job Agent supports multiple user profiles, each with their own:
- Job search criteria (seniority, domains, locations)
- Email digest preferences
- Optional email inbox monitoring
- Personalized scoring weights

Profiles are stored in `profiles/*.json` and automatically loaded by the system. **No code changes are required** when adding new profiles.

**Architecture Note (Issue #184)**: Scraping is decoupled from scoring. When you run the scraper with any profile's `--profile` flag, jobs are automatically scored for ALL enabled profiles. You don't need to scrape separately for each profile.

## Quick Start

1. Create `profiles/yourname.json` with job preferences
2. (Optional) Set up dedicated email inbox with app password
3. (Optional) Add credentials to `.env`
4. Test the profile with `--profile yourname` flag
5. The profile will automatically appear in the TUI

## Step-by-Step Guide

### 1. Create Profile JSON File

Create a new file `profiles/yourname.json` (use lowercase ID):

```json
{
  "id": "yourname",
  "name": "Your Full Name",
  "email": "your.email@gmail.com",
  "enabled": true,
  "scoring": {
    "target_seniority": ["senior", "staff", "lead", "principal"],
    "domain_keywords": [
      "software", "backend", "cloud", "devops", "python"
    ],
    "role_types": {
      "engineering": ["software engineer", "backend engineer"],
      "data": ["data engineer", "ml engineer"]
    },
    "company_stage": ["startup", "series a", "series b"],
    "avoid_keywords": ["junior", "intern"],
    "location_preferences": {
      "remote_keywords": ["remote", "work from home"],
      "hybrid_keywords": ["hybrid"],
      "preferred_cities": ["toronto", "ottawa"],
      "preferred_regions": ["ontario", "canada"]
    }
  },
  "digest": {
    "min_grade": "C",
    "min_score": 63,
    "include_grades": ["A", "B", "C"],
    "send_frequency": "weekly"
  },
  "notifications": {
    "enabled": false,
    "min_grade": "B",
    "min_score": 80
  }
}
```

### 2. Profile Configuration Fields

#### Basic Info
- `id`: Lowercase profile identifier (used in commands)
- `name`: Full name for display
- `email`: Where to send job digests
- `enabled`: Set to `true` to activate profile

#### Scoring Criteria

**target_seniority** (0-30 points):
- Higher matches = higher scores
- Examples: `["director", "vp", "head of"]`, `["senior", "staff", "principal"]`

**domain_keywords** (0-25 points):
- Industry/technology keywords
- Examples: `["fintech", "healthtech"]`, `["robotics", "hardware"]`

**role_types** (0-20 points):
- Categories of roles you're interested in
- Keys are role type names, values are keyword lists
- Examples: `{"engineering": ["software engineer"]}`, `{"product": ["product manager"]}`

**company_stage** (0-15 points):
- Preferred company maturity
- Examples: `["startup", "series a", "series b"]`, `["scale-up", "growth"]`

**avoid_keywords**:
- Jobs containing these are penalized
- Examples: `["junior", "intern", "coordinator"]`

**location_preferences** (0-15 points):
- `remote_keywords`: Remote work indicators (15 points)
- `hybrid_keywords`: Hybrid work indicators (15 points)
- `preferred_cities`: City matches (12 points)
- `preferred_regions`: Region matches (8 points)

#### Digest Settings

- `min_grade`: Minimum grade to include ("A", "B", "C", "D", "F")
- `min_score`: Minimum numeric score (e.g., 63)
- `include_grades`: Array of grades to include
- `send_frequency`: How often to send ("weekly" recommended)

#### Notification Settings

- `enabled`: Set to `true` for real-time notifications, `false` for digest-only
- `min_grade`: Minimum grade for notifications (typically "B")
- `min_score`: Minimum score for notifications (typically 80)

### 3. Optional: Email Inbox Monitoring

If you want the system to monitor a dedicated email inbox for job alerts:

#### 3.1 Create Gmail Account

1. Create `yourname.jobalerts@gmail.com`
2. Enable 2-factor authentication
3. Generate app password: Google Account → Security → 2-Step Verification → App passwords
4. Save the 16-character app password

#### 3.2 Add Email Credentials to Profile

Add this section to your profile JSON:

```json
{
  "id": "yourname",
  "name": "Your Full Name",
  "email": "your.email@gmail.com",
  "enabled": true,
  "email_credentials": {
    "username": "yourname.jobalerts@gmail.com",
    "app_password_env": "YOURNAME_GMAIL_APP_PASSWORD"
  },
  "scoring": { ... }
}
```

#### 3.3 Add Credentials to `.env`

```bash
# Email credentials for yourname's job alerts inbox
YOURNAME_GMAIL_APP_PASSWORD=your-16-char-app-password
```

**Note**: If you skip this section, the profile will still work for robotics scraping and company monitoring, just not email inbox scanning.

### 4. Test the Profile

#### Validate Profile Loads

```bash
PYTHONPATH=$PWD job-agent-venv/bin/python -c "
from src.utils.profile_manager import get_profile_manager
pm = get_profile_manager()
profile = pm.get_profile('yourname')
print(f'✓ Profile: {profile.name}')
print(f'  Email: {profile.email}')
print(f'  Seniority: {profile.get_target_seniority()[:3]}')
print(f'  Domains: {profile.get_domain_keywords()[:3]}')
"
```

#### Score Jobs for Profile

```bash
# Score all existing jobs for your profile
PYTHONPATH=$PWD job-agent-venv/bin/python src/score_all_profiles.py
```

#### Send Test Digest

```bash
# Dry run (don't actually send)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile yourname --dry-run

# Actually send digest
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile yourname
```

#### Test Email Inbox (if configured)

```bash
# Run unified scraper for your profile
# Note: Jobs are scored for ALL profiles, not just 'yourname'
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile yourname --email-only
```

#### Backfill Scores for Existing Jobs

If you're adding a profile to a system with existing jobs, backfill scores:

```bash
# Score all existing jobs for your new profile
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode backfill --profile yourname

# Or limit to recent jobs (faster)
PYTHONPATH=$PWD job-agent-venv/bin/python src/utils/rescore_jobs.py --mode backfill --profile yourname --max-jobs 500
```

### 5. Use in TUI

Your profile will automatically appear in the TUI menu:

```bash
./run-tui.sh
```

You'll see it as a numbered option:
```
┌────────┬──────────────────┬────────────────────────┬─────────────────────────┐
│ Option │ Profile          │ Email                  │ Focus                   │
├────────┼──────────────────┼────────────────────────┼─────────────────────────┤
│ 1      │ Adam White       │ adamkwhite@gmail.com   │ Software/Product (...)  │
│ 2      │ Wesley van Ooyen │ wesvanooyen@gmail.com  │ Robotics/Hardware (...) │
│ 3      │ Your Name        │ your.email@gmail.com   │ Your domains (...)      │
│ q      │ Quit             │                        │                         │
└────────┴──────────────────┴────────────────────────┴─────────────────────────┘
```

## Profile Examples

### Example 1: Senior Software Engineer (Email Inbox Enabled)

```json
{
  "id": "sarah",
  "name": "Sarah Johnson",
  "email": "sarah.johnson@gmail.com",
  "enabled": true,
  "email_credentials": {
    "username": "sarah.jobalerts@gmail.com",
    "app_password_env": "SARAH_GMAIL_APP_PASSWORD"
  },
  "scoring": {
    "target_seniority": ["senior", "staff", "lead", "principal"],
    "domain_keywords": ["backend", "cloud", "microservices", "golang", "python"],
    "role_types": {
      "engineering": ["backend engineer", "software engineer", "platform engineer"]
    },
    "company_stage": ["series b", "series c", "growth"],
    "avoid_keywords": ["junior", "entry level"],
    "location_preferences": {
      "remote_keywords": ["remote", "distributed"],
      "hybrid_keywords": ["hybrid"],
      "preferred_cities": ["san francisco", "seattle"],
      "preferred_regions": ["california", "pacific northwest"]
    }
  },
  "digest": {
    "min_grade": "B",
    "min_score": 80,
    "include_grades": ["A", "B"],
    "send_frequency": "weekly"
  },
  "notifications": {
    "enabled": true,
    "min_grade": "A",
    "min_score": 98
  }
}
```

### Example 2: Director/VP Engineering (Digest Only)

```json
{
  "id": "michael",
  "name": "Michael Chen",
  "email": "michael.chen@gmail.com",
  "enabled": true,
  "scoring": {
    "target_seniority": ["director", "vp", "head of", "cto"],
    "domain_keywords": ["fintech", "payments", "banking", "crypto"],
    "role_types": {
      "engineering_leadership": ["director engineering", "vp engineering", "cto"]
    },
    "company_stage": ["series c", "series d", "growth", "public"],
    "avoid_keywords": ["manager", "senior manager"],
    "location_preferences": {
      "remote_keywords": ["remote"],
      "preferred_cities": ["new york", "austin", "miami"],
      "preferred_regions": ["east coast", "texas", "florida"]
    }
  },
  "digest": {
    "min_grade": "C",
    "min_score": 63,
    "include_grades": ["A", "B", "C"],
    "send_frequency": "weekly"
  },
  "notifications": {
    "enabled": false
  }
}
```

## Troubleshooting

### Profile Not Appearing in TUI

1. Check JSON syntax: `python3 -m json.tool profiles/yourname.json`
2. Verify `enabled: true` in profile
3. Restart TUI

### Jobs Not Being Scored

```bash
# Re-run scoring for all profiles
PYTHONPATH=$PWD job-agent-venv/bin/python src/score_all_profiles.py
```

### Email Inbox Not Working

1. Verify app password in `.env`
2. Test credentials:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python -c "
from src.imap_client import IMAPClient
from src.utils.profile_manager import get_profile_manager
pm = get_profile_manager()
profile = pm.get_profile('yourname')
client = IMAPClient(profile.email_username, profile.email_app_password)
print('✓ IMAP connection successful')
"
```

### Digest Not Sending

1. Check there are jobs to send:
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile yourname --dry-run
```

2. Check Gmail credentials for sending (uses profile's email_credentials or falls back to legacy GMAIL_USERNAME/GMAIL_APP_PASSWORD)

## Scoring System Reference

Jobs are scored out of 115 points total:

| Category | Max Points | Description |
|----------|------------|-------------|
| Seniority | 30 | Match against target_seniority |
| Domain | 25 | Match against domain_keywords |
| Role Type | 20 | Match against role_types |
| Location | 15 | Remote (15), Hybrid (15), Cities (12), Regions (8) |
| Company Stage | 15 | Match against company_stage |
| Technical | 10 | Technical keyword matches |

**Grades:**
- A: 85+ points
- B: 70-84 points
- C: 55-69 points
- D: 40-54 points
- F: <40 points

## Best Practices

1. **Start Broad**: Use inclusive domain_keywords initially, narrow down based on results
2. **Test First**: Use `--dry-run` to preview digests before enabling
3. **Monitor Inbox**: If using email monitoring, check that job alerts arrive at the configured inbox
4. **Adjust Grades**: Start with min_grade "C", increase to "B" if too many low-quality matches
5. **Location Priority**: Remote jobs get the highest location score (15 points)
6. **Disable When Not Searching**: Set `enabled: false` to pause profile without deleting it

## Related Documentation

- [Multi-Profile Guide](MULTI_PROFILE_GUIDE.md) - How the multi-profile system works
- [Scoring System](../SCORING_CRITERIA.md) - Detailed scoring algorithm
- [TUI Usage](../USER_GUIDE.md) - Using the interactive terminal interface
