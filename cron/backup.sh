#!/bin/bash
# News Digest Bot - SQLite Database Backup Script
# Runs daily via cron to create timestamped backups of the digest database
# Keeps last 7 days of backups, removes older ones automatically

set -e

# Configuration
PROJECT_DIR="/opt/digest-bot"
DATABASE_FILE="$PROJECT_DIR/digest.db"
BACKUP_DIR="$PROJECT_DIR/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/digest_${TIMESTAMP}.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database file exists
if [ ! -f "$DATABASE_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Database file not found at $DATABASE_FILE" >&2
    exit 1
fi

# Create backup using sqlite3 .backup command (safe, doesn't lock database)
if sqlite3 "$DATABASE_FILE" ".backup '$BACKUP_FILE'" 2>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: Backup created at $BACKUP_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Failed to create backup" >&2
    exit 1
fi

# Verify backup file was created and has content
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup file is empty or missing" >&2
    exit 1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup size: $BACKUP_SIZE"

# Clean up old backups (keep last 7 days)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "digest_*.db" -type f -mtime +$RETENTION_DAYS -delete

# Count remaining backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "digest_*.db" -type f | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Retained $BACKUP_COUNT backups"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup job completed successfully"
