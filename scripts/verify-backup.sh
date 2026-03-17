#!/usr/bin/env bash
# =============================================================================
# Cogent — Database Backup Verification Script (Azure PostgreSQL)
# =============================================================================
# Verifies that Azure PostgreSQL Flexible Server backups are restorable by:
#   1. Creating a point-in-time restore (PITR) server from the latest backup
#   2. Running a connectivity + schema check against the restored server
#   3. Deleting the temporary restore server
#
# Requires:
#   - Azure CLI ≥ 2.60 logged in (az login)
#   - psycopg2 installed in the active Python environment
#   - AZURE_RESOURCE_GROUP, AZURE_POSTGRES_SERVER env vars set
#   - DB_ADMIN_USER, DB_ADMIN_PASSWORD, DB_NAME env vars set
#
# Usage:
#   AZURE_RESOURCE_GROUP=cogent-production \
#   AZURE_POSTGRES_SERVER=cogent-prod-postgres \
#   DB_ADMIN_USER=cogentadmin \
#   DB_ADMIN_PASSWORD=<password> \
#   DB_NAME=cogent \
#     ./scripts/verify-backup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[backup-verify]${NC} $*"; }
warn() { echo -e "${YELLOW}[backup-verify]${NC} $*"; }
err()  { echo -e "${RED}[backup-verify]${NC} $*" >&2; }

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:?AZURE_RESOURCE_GROUP must be set}"
AZURE_POSTGRES_SERVER="${AZURE_POSTGRES_SERVER:?AZURE_POSTGRES_SERVER must be set}"
DB_ADMIN_USER="${DB_ADMIN_USER:?DB_ADMIN_USER must be set}"
DB_ADMIN_PASSWORD="${DB_ADMIN_PASSWORD:?DB_ADMIN_PASSWORD must be set}"
DB_NAME="${DB_NAME:-cogent}"

RESTORE_SERVER_NAME="${AZURE_POSTGRES_SERVER}-verify-$(date +%Y%m%d-%H%M%S)"
CLEANUP_RESTORE_SERVER=true

cleanup() {
    if [[ "$CLEANUP_RESTORE_SERVER" == "true" ]]; then
        log "Deleting restore server: $RESTORE_SERVER_NAME"
        az postgres flexible-server delete \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --name "$RESTORE_SERVER_NAME" \
            --yes 2>/dev/null || warn "Could not delete restore server (may not exist yet)."
    fi
}
trap cleanup EXIT

# ── Step 1: Determine restore point (latest available) ──────────────────────
log "Determining earliest restore point for $AZURE_POSTGRES_SERVER…"
RESTORE_TIME=$(az postgres flexible-server show \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$AZURE_POSTGRES_SERVER" \
    --query "backup.earliestRestoreDate" \
    --output tsv 2>/dev/null || echo "")

# Use 5 minutes ago as restore point (well within available range)
RESTORE_POINT=$(python3 -c "
from datetime import datetime, timezone, timedelta
print((datetime.now(timezone.utc) - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'))
")
log "Restore point: $RESTORE_POINT"

# ── Step 2: Create point-in-time restore server ─────────────────────────────
log "Creating PITR restore server: $RESTORE_SERVER_NAME (this may take ~5 minutes)…"
az postgres flexible-server restore \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$RESTORE_SERVER_NAME" \
    --source-server "$AZURE_POSTGRES_SERVER" \
    --restore-time "$RESTORE_POINT"

log "Restore server ready: $RESTORE_SERVER_NAME"

# ── Step 3: Get restore server FQDN ─────────────────────────────────────────
RESTORE_FQDN=$(az postgres flexible-server show \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$RESTORE_SERVER_NAME" \
    --query "fullyQualifiedDomainName" \
    --output tsv)

if [[ -z "$RESTORE_FQDN" ]]; then
    err "Could not retrieve FQDN for restore server."
    exit 1
fi
log "Restore server FQDN: $RESTORE_FQDN"

# Allow Azure services to connect to the restore server
az postgres flexible-server firewall-rule create \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --name "$RESTORE_SERVER_NAME" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 2>/dev/null || true

VERIFY_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${RESTORE_FQDN}:5432/${DB_NAME}?sslmode=require"

# ── Step 4: Verify schema ────────────────────────────────────────────────────
log "Verifying schema on restore server…"

TABLE_COUNT=$(python3 -c "
import psycopg2, sys
try:
    conn = psycopg2.connect('${VERIFY_URL}')
    cur = conn.cursor()
    cur.execute(\"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'\")
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)

if [[ "$TABLE_COUNT" =~ ^[0-9]+$ ]] && [[ "$TABLE_COUNT" -gt 0 ]]; then
    log "Schema verified: $TABLE_COUNT tables found on restore server."
else
    err "Schema verification FAILED. Output: $TABLE_COUNT"
    exit 1
fi

# ── Step 5: Verify Alembic revision ─────────────────────────────────────────
log "Checking Alembic migration state on restore server…"
DATABASE_URL="$VERIFY_URL" alembic current 2>&1 | sed 's/^/  /'

log "Backup verification PASSED."
