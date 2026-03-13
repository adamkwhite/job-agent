#!/bin/bash
# Catch-up script for missed cron runs (e.g., after WSL restart)
# Called via @reboot cron entry. Waits for network, then checks if
# today's scraper has already run. If not, runs it.

PROJECT_ROOT="/home/adam/Code/job-agent"
LOG_FILE="$PROJECT_ROOT/logs/unified_scraper.log"
LOCK_FILE="/tmp/job-agent-catchup.lock"

# Prevent concurrent runs (with the regular 6am cron job)
if [ -f "$LOCK_FILE" ]; then
    exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT
touch "$LOCK_FILE"

# Wait for network (email/API calls need it)
for i in $(seq 1 30); do
    if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

# Check if today's run already happened by looking for today's date in the log
TODAY=$(date +%Y-%m-%d)
# Match lines like "Unified Scraper Run (Multi-Inbox): Thu Mar 13 06:00:01 EDT 2026"
# and "Completed: Thu Mar 13 ..."
if grep -q "Unified Scraper Run.*$(date +'%b %_d')" "$LOG_FILE" 2>/dev/null; then
    # Verify it's actually today (not same month/day from last year)
    # Check for a "Completed" line with today's abbreviated date after the last "Unified Scraper Run"
    LAST_RUN_LINE=$(grep -n "Unified Scraper Run" "$LOG_FILE" 2>/dev/null | tail -1 | cut -d: -f1)
    if [ -n "$LAST_RUN_LINE" ]; then
        COMPLETED_AFTER=$(tail -n +"$LAST_RUN_LINE" "$LOG_FILE" | grep -c "Completed:.*$(date +'%b %_d')")
        if [ "$COMPLETED_AFTER" -gt 0 ]; then
            echo "$(date): Scraper already ran today, skipping catch-up" >> "$LOG_FILE"
            exit 0
        fi
    fi
fi

# Today's run was missed — catch up
echo "" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "CATCH-UP RUN (missed cron): $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

exec "$PROJECT_ROOT/scripts/run_unified_scraper.sh"
