#!/bin/bash
# Unified weekly scraper runner - Multi-Inbox Mode
# This script is called by cron

# Get project root (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment
source job-agent-venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/unified_weekly_scraper.log"

# Timestamp
echo "========================================" >> "$LOG_FILE"
echo "Unified Scraper Run (Multi-Inbox): $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run unified scraper with --all-inboxes flag
# Processes ALL configured email inboxes (Wes, Adam, etc.)
# Email processing: last 100 emails per inbox
# Companies: D+ grade (50+), all monitored companies
# Ministry: 47+ points (for Mario's QA focus)
python3 src/jobs/weekly_unified_scraper.py \
  --all-inboxes \
  --email-limit 100 \
  --companies-min-score 50 \
  >> "$LOG_FILE" 2>&1

# Generate HTML report (optional - if you use this)
# echo "" >> "$LOG_FILE"
# echo "Generating HTML report..." >> "$LOG_FILE"
# python3 src/generate_jobs_html.py >> "$LOG_FILE" 2>&1

# Send digests (optional - if you want automated digest sending)
# Uncomment when ready to automate email sending:
# echo "" >> "$LOG_FILE"
# echo "Sending profile digests..." >> "$LOG_FILE"
# python3 src/send_profile_digest.py --all >> "$LOG_FILE" 2>&1

echo "" >> "$LOG_FILE"
echo "Completed: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
