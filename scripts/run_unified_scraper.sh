#!/bin/bash
# Unified daily scraper runner - Multi-Inbox Mode
# This script is called by cron (daily at 6am)
# Sends daily digests every run, weekly digests on Mondays only

# Get project root (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment
source job-agent-venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/unified_scraper.log"

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

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "SCRAPER FAILED with exit code $EXIT_CODE at $(date)" >> "$LOG_FILE"
fi

# Send daily digests (profiles with send_frequency="daily")
echo "" >> "$LOG_FILE"
echo "Sending daily digests..." >> "$LOG_FILE"
python3 src/send_profile_digest.py --all --frequency daily >> "$LOG_FILE" 2>&1

# On Mondays, also send weekly digests
DAY_OF_WEEK=$(date +%u)  # 1=Monday
if [ "$DAY_OF_WEEK" -eq 1 ]; then
    echo "" >> "$LOG_FILE"
    echo "Monday - sending weekly digests..." >> "$LOG_FILE"
    python3 src/send_profile_digest.py --all --frequency weekly >> "$LOG_FILE" 2>&1
fi

echo "" >> "$LOG_FILE"
echo "Completed: $(date) (exit code: $EXIT_CODE)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
