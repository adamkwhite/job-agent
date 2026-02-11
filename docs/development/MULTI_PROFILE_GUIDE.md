# Multi-Profile System Guide

The job agent supports multiple user profiles, each with separate:
- Email accounts for job alerts
- Scoring criteria and preferences
- Email digest settings
- Notification thresholds

## Current Profiles

- **Wes** (`profiles/wes.json`) - VP/Director roles in Robotics/Hardware
- **Adam** (`profiles/adam.json`) - Senior/Staff roles in Software/Product

## How It Works (Issue #184 - Decoupled Architecture)

1. **Scraping**: The `--profile` flag determines which email inbox to connect to for scraping
2. **Scoring**: Each job is automatically scored for ALL enabled profiles (stored in `job_scores` table)
3. **Digests**: Sent separately to each profile with their personalized matches
4. **Database**: The `jobs` table tracks which email inbox the job came from (`profile` column)
5. **Re-scoring**: Independent utility allows updating scores without re-scraping

**Key insight**: You only need to scrape once (from any profile's inbox) and all profiles get scored automatically. No need to run the scraper multiple times.

### Database Schema

**`jobs` table**:
- `profile` column - Which email inbox the job was scraped from (e.g., 'wes', 'adam')
- Stores the raw job data (title, company, location, link, description)

**`job_scores` table**:
- `job_id` - Foreign key to jobs table
- `profile_id` - Which profile the score is for (e.g., 'wes', 'adam')
- `fit_score`, `fit_grade`, `score_breakdown` - Profile-specific scoring
- `digest_sent_at`, `notified_at` - Track what's been sent to each profile

**Why two tables?**
- One job can have different scores for different profiles
- Wes might get an A grade on a robotics VP role, while Adam gets an F
- Adam might get an A grade on a software staff role, while Wes gets a D
- Each person only receives jobs that match their criteria

## Adding a New Profile

Follow these steps to add a new person to the system:

### Step 1: Create Profile JSON

Create `profiles/yourname.json` with the following structure:

```json
{
  "id": "yourname",
  "name": "Your Full Name",
  "email": "youremail@example.com",
  "enabled": true,
  "email_credentials": {
    "username": "yourname.jobalerts@gmail.com",
    "app_password_env": "YOURNAME_GMAIL_APP_PASSWORD"
  },
  "scoring": {
    "target_seniority": ["senior", "staff", "lead", "principal"],
    "domain_keywords": [
      "your", "domain", "keywords", "here"
    ],
    "role_types": {
      "engineering": ["software engineer", "developer"],
      "product": ["product manager", "product owner"]
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
    "enabled": true,
    "min_grade": "B",
    "min_score": 80
  }
}
```

### Step 2: Set Up Dedicated Gmail Account

1. Create a new Gmail account: `yourname.jobalerts@gmail.com`
2. Enable 2-Factor Authentication (2FA) on the account
3. Generate an App Password:
   - Go to Google Account → Security → 2-Step Verification → App passwords
   - Create a new app password for "Mail"
   - Save the 16-character password
4. Subscribe to job alert newsletters:
   - LinkedIn Job Alerts
   - Built In
   - Work In Tech
   - Other relevant job boards

### Step 3: Add Credentials to `.env`

Add your Gmail app password to the `.env` file:

```bash
YOURNAME_GMAIL_APP_PASSWORD=your_16_char_app_password
```

**Important**: The environment variable name must match `app_password_env` in your profile JSON.

### Step 4: Test the Profile

#### Test Email Connection
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python -c "
from src.imap_client import IMAPEmailClient
client = IMAPEmailClient(profile='yourname')
print(f'Connected to: {client.username}')
"
```

Expected output:
```
Using email: yourname.jobalerts@gmail.com (profile: yourname)
Connected to: yourname.jobalerts@gmail.com
```

#### Test Scraping (Small Sample)
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile yourname --email-only --email-limit 5
```

This will:
- Connect to your email inbox
- Process up to 5 emails
- Score jobs for all profiles (including your new one)
- Store results in database

#### Test Digest (Dry Run)
```bash
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile yourname --dry-run
```

This will:
- Query jobs scored for your profile
- Generate HTML digest
- Show what would be sent (without actually sending)

### Step 5: Update TUI (Optional)

If you want to add the profile to the interactive TUI (`src/tui.py`), you'll need to:

1. **Update `select_profile()` function**:
```python
table.add_row("1", "Wesley van Ooyen", "wesvanooyen@gmail.com", "Robotics/Hardware (VP/Director)")
table.add_row("2", "Adam White", "adamkwhite@gmail.com", "Software/Product (Senior/Staff)")
table.add_row("3", "Your Name", "youremail@example.com", "Your Focus")  # Add this
table.add_row("q", "Quit", "", "")
```

2. **Update `select_sources()` function** with your criteria:
```python
elif profile == "yourname":
    criteria_content = """[bold yellow]📊 Scoring (0-115 pts)[/bold yellow]

[cyan]Seniority (30):[/cyan] Your Target Seniority

[cyan]Domain (25):[/cyan] Your Domain Keywords

[cyan]Role (20):[/cyan] Your Role Preferences

[cyan]Location (15):[/cyan] Remote/Your Location

[bold yellow]🎓 Grades[/bold yellow]
[green]A (85+)[/green] Notify + Digest
[green]B (70+)[/green] Notify + Digest
[yellow]C (55+)[/yellow] Digest only
[dim]D/F[/dim] Stored/Filtered

[bold yellow]📧 Sent to:[/bold yellow]
youremail@example.com
[dim]CC:[/dim] adamkwhite@gmail.com"""
    panel_title = "[bold cyan]Your Name's Scoring Criteria[/bold cyan]"
```

## Scoring Criteria Explained

The scoring system awards points across 6 categories (total 115 points):

### Seniority (30 points)
**What it does**: Matches job titles against target seniority levels
**Examples**:
- VP/Director level: `["vp", "director", "head of", "executive", "chief"]`
- Senior/Staff level: `["senior", "staff", "lead", "principal", "architect"]`
- Mid level: `["engineer", "manager", "specialist"]`

### Domain Keywords (25 points)
**What it does**: Matches job descriptions against industry/technology keywords
**Examples**:
- Robotics/Hardware: `["robotics", "automation", "iot", "hardware", "medtech"]`
- Software/Cloud: `["software", "cloud", "devops", "saas", "api"]`
- Data/ML: `["data", "machine learning", "ai", "analytics"]`

### Role Types (20 points)
**What it does**: Categorizes jobs by function and applies preference weighting
**Examples**:
```json
{
  "engineering": ["software engineer", "developer", "architect"],
  "product": ["product manager", "product owner"],
  "data": ["data engineer", "data scientist"]
}
```

### Location (15 points)
**What it does**: Scores based on remote/hybrid/location preferences
**Scoring**:
- Remote keywords: +15 points
- Hybrid keywords: +15 points
- Preferred cities: +12 points
- Preferred regions: +10 points
- No match: +5 points (baseline)

**Examples**:
```json
{
  "remote_keywords": ["remote", "work from home", "wfh", "distributed"],
  "hybrid_keywords": ["hybrid"],
  "preferred_cities": ["toronto", "waterloo", "ottawa"],
  "preferred_regions": ["ontario", "canada", "greater toronto area"]
}
```

### Company Stage (15 points)
**What it does**: Matches against company funding/growth stage
**Examples**:
- Growth stage: `["series a", "series b", "series c", "growth", "scale-up"]`
- Established: `["fortune 500", "enterprise", "public company"]`
- Early stage: `["seed", "pre-seed", "startup"]`

### Technical Keywords (10 points)
**What it does**: Bonus points for specific technical skills
**Examples**:
- Hardware: `["mechatronics", "embedded", "firmware", "pcb", "dfm"]`
- Software: `["python", "javascript", "react", "kubernetes", "aws"]`
- Data: `["sql", "spark", "tensorflow", "mlops"]`

### Grading Scale

| Grade | Score Range | Action |
|-------|-------------|--------|
| A | 98-115 | Immediate notification + digest |
| B | 80-97 | Immediate notification + digest |
| C | 63-79 | Digest only |
| D | 46-62 | Stored, not sent |
| F | 0-45 | Filtered out |

## Using the System with Multiple Profiles

### Running the Scraper

```bash
# For Wes (all sources: emails + robotics + company monitoring)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes

# For Adam (all sources)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam

# Email only (profile-specific inbox)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile adam --email-only --email-limit 100
```

### Sending Digests

```bash
# Send to specific profile (only unsent jobs)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile wes
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile adam

# Send to all enabled profiles
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --all

# Test digest without sending (dry run)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile adam --dry-run

# Force resend all jobs (for testing)
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile wes --force-resend
```

### Using the Interactive TUI

```bash
# Launch the interactive terminal UI
./run-tui.sh
```

The TUI provides:
- Profile selection (Wes or Adam)
- Source selection (Email, Robotics sheet, Company monitoring)
- Action selection (Scrape only, Send digest, or Both)
- Profile-specific scoring criteria display
- Profile-specific email inbox display
- Confirmation before execution

## Troubleshooting

### Error: "Profile file not found"
- Check that `profiles/yourname.json` exists
- Ensure the filename matches the profile ID (e.g., `profiles/adam.json` for `profile='adam'`)

### Error: "Gmail credentials not configured"
- Check that the environment variable name in `.env` matches `app_password_env` in your profile JSON
- Example: If `app_password_env` is `"ADAM_GMAIL_APP_PASSWORD"`, then `.env` must have `ADAM_GMAIL_APP_PASSWORD=...`

### Error: "Found 0 unread emails"
- Emails may have been processed already (they're marked as read after processing)
- Check Gmail web interface to verify there are truly unread job alerts
- Try subscribing to more job alert newsletters

### Jobs not appearing in digest
- Check if jobs were scored for your profile: Run the scraper with `--profile yourname`
- Verify your scoring criteria aren't too restrictive (check `min_grade` in digest settings)
- Run `PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py --profile yourname --dry-run` to see what would be sent

### Digest not being sent
- Verify email credentials in `.env`
- Check `digest.min_grade` and `digest.include_grades` in your profile JSON
- Ensure `enabled: true` in your profile JSON
- Check logs for error messages

## Advanced: Multi-Person Scoring Details

When a job is added to the database, the system automatically:

1. **Stores the job once** in `jobs` table with `profile` set to the email inbox it came from
2. **Scores the job for ALL enabled profiles** using `MultiPersonScorer`
3. **Stores each score separately** in `job_scores` table

Example for a robotics VP job:
```
jobs table:
  id=123, title="VP Engineering - Robotics", profile="wes"

job_scores table:
  job_id=123, profile_id="wes",  fit_score=105, fit_grade="A"
  job_id=123, profile_id="adam", fit_score=45,  fit_grade="F"
```

This allows:
- Wes receives this job in his A-grade digest
- Adam never sees it (below his threshold)
- Both profiles maintain separate tracking of what's been sent

## Future Enhancements

Potential improvements to the multi-profile system:

- [ ] Web UI for managing profiles (currently JSON files)
- [ ] Per-profile notification preferences (SMS, Slack, etc.)
- [ ] Profile-specific job sources (e.g., Adam subscribes to different newsletters than Wes)
- [ ] Team/shared profiles (multiple people sharing one profile)
- [ ] Profile inheritance (base profile + personal overrides)
- [ ] A/B testing different scoring criteria
