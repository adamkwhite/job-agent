#!/bin/bash
# Setup weekly unified scraper cron job
# Runs Monday 9am: emails + robotics + companies

set -e

echo "Setting up Unified Weekly Scraper automation..."
echo "================================================"

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p logs

# Create wrapper script
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/run_unified_scraper.sh"

cat > "$WRAPPER_SCRIPT" << 'EOF'
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
EOF

chmod +x "$WRAPPER_SCRIPT"

echo "✓ Created wrapper script: $WRAPPER_SCRIPT"

# Create cron entry (Monday 9am)
CRON_CMD="0 9 * * 1 $WRAPPER_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$WRAPPER_SCRIPT"; then
    echo "✓ Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✓ Added cron job: Monday 9am"
fi

echo ""
echo "================================================"
echo "Setup Complete! (Multi-Inbox Mode)"
echo "================================================"
echo ""
echo "Schedule: Every Monday at 9:00 AM"
echo "Script:   $WRAPPER_SCRIPT"
echo "Logs:     $PROJECT_ROOT/logs/unified_weekly_scraper.log"
echo ""
echo "To view cron jobs:    crontab -l"
echo "To remove cron job:   crontab -e (then delete the line)"
echo "To test manually:     $WRAPPER_SCRIPT"
echo "To view logs:         tail -f logs/unified_weekly_scraper.log"
echo ""
echo "Sources configured (--all-inboxes mode):"
echo "  • ALL configured email inboxes (Wes, Adam, etc.)"
echo "  • Email processing: 100 emails max per inbox"
echo "  • Company monitoring: D+ grade (50+ points)"
echo "  • Ministry of Testing: 47+ points"
echo ""
echo "Features:"
echo "  • Sequential inbox processing with error handling"
echo "  • Shared company/ministry scraping (runs once)"
echo "  • Aggregated stats across all profiles"
echo "  • Jobs scored for ALL profiles automatically"
echo ""
echo "Notifications: A/B grade jobs only (70+ points)"
echo "================================================"
