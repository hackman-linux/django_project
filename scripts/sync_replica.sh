#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# NapsterLegal — Replica Sync Script (Option B)
# Dumps primary PostgreSQL and restores to Supabase replica.
#
# SETUP:
#   chmod +x scripts/sync_replica.sh
#   crontab -e
#   Add:  0 2 * * * ~/envs/django_project/scripts/sync_replica.sh >> /var/log/napster_sync.log 2>&1
#
# REQUIREMENTS:
#   export REPLICA_DB_URL="postgresql://postgres:PASSWORD@db.xxx.supabase.co/postgres"
# ─────────────────────────────────────────────────────────────────────────────

set -e
DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR="~/envs/backups"
DUMP_FILE="$BACKUP_DIR/napsterlegal_$DATE.sql"

mkdir -p "$BACKUP_DIR"

echo "[$DATE] Starting replica sync..."

# 1. Dump primary database
pg_dump -U napster_user -d napsterlegal_db -f "$DUMP_FILE"
echo "  Dump complete: $DUMP_FILE"

# 2. Restore to replica (Supabase)
if [ -n "$REPLICA_DB_URL" ]; then
    psql "$REPLICA_DB_URL" < "$DUMP_FILE"
    echo "  Replica sync complete"
else
    echo "  WARNING: REPLICA_DB_URL not set — skipping remote sync"
fi

# 3. Keep only last 7 local backups
find "$BACKUP_DIR" -name "napsterlegal_*.sql" -mtime +7 -delete
echo "  Old backups cleaned"

echo "[$DATE] Sync done."
