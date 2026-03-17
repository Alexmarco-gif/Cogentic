#!/usr/bin/env bash
# =============================================================================
# Cogent — Database Migration Script
# =============================================================================
# Runs Alembic migrations with safety checks and rollback support.
#
# Usage:
#   ./scripts/migrate.sh                     # Upgrade to head
#   ./scripts/migrate.sh upgrade head        # Same as above
#   ./scripts/migrate.sh downgrade -1        # Roll back one migration
#   ./scripts/migrate.sh current             # Show current revision
#   ./scripts/migrate.sh history             # Show migration history
# =============================================================================

set -euo pipefail

COMMAND="${1:-upgrade}"
TARGET="${2:-head}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[migrate]${NC} $*"; }
warn() { echo -e "${YELLOW}[migrate]${NC} $*"; }
err()  { echo -e "${RED}[migrate]${NC} $*" >&2; }

# ── Preflight checks ─────────────────────────────────────────────────────────
if [[ -z "${DATABASE_URL:-}" ]]; then
    err "DATABASE_URL is not set. Aborting."
    exit 1
fi


# ── Show current state ───────────────────────────────────────────────────────
log "Current migration revision:"
alembic current 2>&1 | sed 's/^/  /'

if [[ "$COMMAND" == "current" ]]; then
    exit 0
fi

if [[ "$COMMAND" == "history" ]]; then
    log "Migration history:"
    alembic history --verbose 2>&1 | sed 's/^/  /'
    exit 0
fi

# ── Validate the target ─────────────────────────────────────────────────────
if [[ "$COMMAND" == "upgrade" ]]; then
    PENDING=$(alembic heads 2>&1 | head -n1)
    log "Target: $TARGET (heads: $PENDING)"
fi

# ── Execute ──────────────────────────────────────────────────────────────────
log "Running: alembic $COMMAND $TARGET"
echo ""

if alembic "$COMMAND" "$TARGET" 2>&1; then
    echo ""
    log "Migration completed successfully."
    log "New revision:"
    alembic current 2>&1 | sed 's/^/  /'
else
    EXIT_CODE=$?
    echo ""
    err "Migration FAILED (exit code $EXIT_CODE)."
    err ""
    err "To roll back the last migration:"
    err "  alembic downgrade -1"
    err ""
    err "Current state:"
    alembic current 2>&1 | sed 's/^/  /' >&2
    exit $EXIT_CODE
fi
