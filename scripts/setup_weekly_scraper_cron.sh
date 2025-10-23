#!/bin/bash
# Setup weekly robotics scraper as cron job
# Run every Monday at 9am

PROJECT_DIR="/home/adam/Code/job-agent"
VENV_PYTHON="$PROJECT_DIR/job-agent-venv/bin/python"
SCRAPER_SCRIPT="$PROJECT_DIR/src/jobs/weekly_robotics_scraper.py"
LOG_DIR="$PROJECT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Cron job command (runs every Monday at 9am)
CRON_CMD="0 9 * * 1 cd $PROJECT_DIR && $VENV_PYTHON $SCRAPER_SCRIPT --min-score 70 >> $LOG_DIR/weekly_scraper.log 2>&1"

echo "Adding weekly robotics scraper to crontab..."
echo "Schedule: Every Monday at 9:00 AM"
echo "Command: $CRON_CMD"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "weekly_robotics_scraper.py"; then
    echo "⚠️  Cron job already exists. Remove it first with:"
    echo "   crontab -e"
    echo "   (then delete the line containing 'weekly_robotics_scraper.py')"
    exit 1
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✓ Cron job added successfully!"
echo ""
echo "To view your crontab:"
echo "  crontab -l"
echo ""
echo "To edit your crontab:"
echo "  crontab -e"
echo ""
echo "To remove this job:"
echo "  crontab -e"
echo "  (then delete the line containing 'weekly_robotics_scraper.py')"
echo ""
echo "Logs will be written to: $LOG_DIR/weekly_scraper.log"
echo ""
echo "To test the scraper manually:"
echo "  $VENV_PYTHON $SCRAPER_SCRIPT --min-score 70"
