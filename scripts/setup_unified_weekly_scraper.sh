#!/bin/bash
# Setup daily unified scraper cron job
# Runs daily at 6am: emails + companies + ministry + frequency-aware digests

set -e

echo "Setting up Daily Unified Scraper automation..."
echo "================================================"

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p logs

# Wrapper script path
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/run_unified_scraper.sh"
chmod +x "$WRAPPER_SCRIPT"

echo "✓ Wrapper script: $WRAPPER_SCRIPT"

# Create cron entry (daily at 6am)
CRON_CMD="0 6 * * * $WRAPPER_SCRIPT"

# Remove old weekly cron entry if it exists, then add daily
EXISTING=$(crontab -l 2>/dev/null || true)
if echo "$EXISTING" | grep -q "$WRAPPER_SCRIPT"; then
    # Remove existing entry and add new one
    echo "$EXISTING" | grep -v "$WRAPPER_SCRIPT" | { cat; echo "$CRON_CMD"; } | crontab -
    echo "✓ Updated cron job: weekly → daily at 6am"
else
    # Add new entry
    (echo "$EXISTING"; echo "$CRON_CMD") | crontab -
    echo "✓ Added cron job: daily at 6am"
fi

echo ""
echo "================================================"
echo "Setup Complete! (Daily Mode)"
echo "================================================"
echo ""
echo "Schedule: Every day at 6:00 AM"
echo "Script:   $WRAPPER_SCRIPT"
echo "Logs:     $PROJECT_ROOT/logs/unified_scraper.log"
echo ""
echo "To view cron jobs:    crontab -l"
echo "To remove cron job:   crontab -e (then delete the line)"
echo "To test manually:     $WRAPPER_SCRIPT"
echo "To view logs:         tail -f logs/unified_scraper.log"
echo ""
echo "Sources:"
echo "  • ALL configured email inboxes (Wes, Adam, etc.)"
echo "  • Email processing: 100 emails max per inbox"
echo "  • Company monitoring: D+ grade (50+ points)"
echo "  • Ministry of Testing: 47+ points"
echo ""
echo "Digest schedule:"
echo "  • Daily profiles: digest sent every run"
echo "  • Weekly profiles: digest sent on Mondays only"
echo ""
echo "Notifications: A/B grade jobs only (70+ points)"
echo "================================================"
