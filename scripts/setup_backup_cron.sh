#!/bin/bash
# Setup cron job for daily database backups
# Runs at 3:00 AM daily

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$PROJECT_DIR/scripts/backup_database.sh"

# Cron job entry (runs at 3 AM daily)
CRON_JOB="0 3 * * * cd $PROJECT_DIR && $BACKUP_SCRIPT >> logs/database_backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_database.sh"; then
    echo "⚠️  Backup cron job already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep backup_database.sh
    echo ""
    read -p "Replace existing cron job? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cancelled"
        exit 0
    fi
    # Remove existing job
    crontab -l | grep -v backup_database.sh | crontab -
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Database backup cron job installed!"
echo ""
echo "Schedule: Daily at 3:00 AM"
echo "Command:  $BACKUP_SCRIPT"
echo "Logs:     logs/database_backup.log"
echo ""
echo "Retention policy:"
echo "  • Daily backups: Keep 7 days"
echo "  • Weekly backups: Keep 4 weeks (Sundays)"
echo "  • Monthly backups: Keep 3 months (1st of month)"
echo ""
echo "To verify: crontab -l | grep backup"
echo "To remove: crontab -l | grep -v backup_database.sh | crontab -"
