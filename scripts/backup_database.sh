#!/bin/bash
# Automated database backup - daily retention (7 days)

set -e

# Configuration
DB_PATH="${DATABASE_PATH:-data/jobs.db}"
BACKUP_DIR="data/backups"
DATE=$(date +%Y%m%d)
LOG_FILE="logs/database_backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    log "⚠️  Database not found at $DB_PATH - skipping backup"
    exit 0
fi

BACKUP_FILE="${BACKUP_DIR}/jobs-backup-${DATE}.db"

# Create backup
log "📦 Creating backup: $BACKUP_FILE"
cp "$DB_PATH" "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✅ Backup created successfully ($BACKUP_SIZE)"
else
    log "❌ Backup failed!"
    exit 1
fi

# Keep 7 daily backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "jobs-backup-*.db" -type f | wc -l)
if [ "$BACKUP_COUNT" -gt 7 ]; then
    REMOVED=$((BACKUP_COUNT - 7))
    find "$BACKUP_DIR" -name "jobs-backup-*.db" -type f -printf '%T@ %p\n' | \
        sort -rn | tail -n +8 | cut -d' ' -f2- | xargs rm -f
    log "🧹 Removed $REMOVED old backup(s)"
fi

# Summary
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "jobs-backup-*.db" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "📊 $TOTAL_BACKUPS backups using $TOTAL_SIZE"
