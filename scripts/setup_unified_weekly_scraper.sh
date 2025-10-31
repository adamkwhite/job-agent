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
# Unified weekly scraper runner
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
echo "Unified Scraper Run: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run unified scraper (all sources by default)
# Email processing: last 100 emails
# Robotics: B+ grade (70+)
# Companies: D+ grade (50+), Wes's companies only
python3 src/jobs/weekly_unified_scraper.py \
  --email-limit 100 \
  --robotics-min-score 70 \
  --companies-min-score 50 \
  --company-filter "From Wes" \
  >> "$LOG_FILE" 2>&1

# Generate HTML report
echo "" >> "$LOG_FILE"
echo "Generating HTML report..." >> "$LOG_FILE"
python3 src/generate_jobs_html.py >> "$LOG_FILE" 2>&1

# Send digest (if configured)
# Uncomment when ready to automate email sending:
# echo "" >> "$LOG_FILE"
# echo "Sending digest email..." >> "$LOG_FILE"
# python3 src/send_digest_to_wes.py >> "$LOG_FILE" 2>&1

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
echo "Setup Complete!"
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
echo "Sources configured:"
echo "  • Email processing (100 emails max)"
echo "  • Robotics sheet (B+ grade, 70+ points)"
echo "  • Company monitoring (D+ grade, 50+ points, Wes's companies)"
echo ""
echo "Notifications: A/B grade jobs only (80+ points)"
echo "================================================"
