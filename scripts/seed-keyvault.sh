#!/usr/bin/env bash
# =============================================================================
# Cogent — Key Vault Secret Seeding Script
# =============================================================================
# Populates Azure Key Vault with the secrets required by Container Apps.
# Run once per environment, then update individual secrets as needed.
#
# Prerequisites:
#   - Azure CLI logged in with sufficient permissions
#   - Key Vault already deployed via Bicep
#
# Usage:
#   VAULT_NAME=cogent-stg-kv ./scripts/seed-keyvault.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[keyvault]${NC} $*"; }
warn() { echo -e "${YELLOW}[keyvault]${NC} $*"; }
err()  { echo -e "${RED}[keyvault]${NC} $*" >&2; }

VAULT_NAME="${VAULT_NAME:?VAULT_NAME must be set}"

# ── Required secrets ─────────────────────────────────────────────────────────
# Each entry: <key-vault-secret-name> <env-var-name-or-prompt>
SECRETS=(
    "redis-url|REDIS_URL"
    "secret-key|SECRET_KEY"
    "auth0-domain|AUTH0_DOMAIN"
    "auth0-audience|AUTH0_AUDIENCE"
    "auth0-m2m-client-id|AUTH0_M2M_CLIENT_ID"
    "auth0-m2m-client-secret|AUTH0_M2M_CLIENT_SECRET"
    "auth0-webhook-secret|AUTH0_WEBHOOK_SECRET"
    "openai-api-key|OPENAI_API_KEY"
    "sentry-dsn|SENTRY_DSN"
    "auth0-frontend-secret|AUTH0_SECRET"
    "auth0-issuer-base-url|AUTH0_ISSUER_BASE_URL"
    "auth0-client-id|AUTH0_CLIENT_ID"
    "auth0-client-secret|AUTH0_CLIENT_SECRET"
)

# ── Seed loop ────────────────────────────────────────────────────────────────
for entry in "${SECRETS[@]}"; do
    KV_NAME="${entry%%|*}"
    ENV_VAR="${entry##*|}"

    VALUE="${!ENV_VAR:-}"
    if [[ -z "$VALUE" ]]; then
        warn "Skipping '$KV_NAME' — $ENV_VAR is not set in the environment."
        continue
    fi

    log "Setting secret: $KV_NAME"
    az keyvault secret set \
        --vault-name "$VAULT_NAME" \
        --name "$KV_NAME" \
        --value "$VALUE" \
        --output none
done

log "Done. Secrets seeded into Key Vault: $VAULT_NAME"
log "Note: 'database-url' is created by infrastructure/main.bicep from the Azure PostgreSQL server outputs."
log ""
log "To verify:"
log "  az keyvault secret list --vault-name $VAULT_NAME --output table"
