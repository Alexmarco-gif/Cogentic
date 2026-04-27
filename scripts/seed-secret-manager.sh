#!/usr/bin/env bash
set -euo pipefail

# Seeds GCP Secret Manager secrets from the current shell environment.

PROJECT_ID="${PROJECT_ID:?PROJECT_ID must be set}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
PREFIX="cogent-${ENVIRONMENT}"

declare -a SECRET_MAP=(
  "redis-url|REDIS_URL"
  "secret-key|SECRET_KEY"
  "auth0-domain|AUTH0_DOMAIN"
  "auth0-audience|AUTH0_AUDIENCE"
  "auth0-m2m-client-id|AUTH0_M2M_CLIENT_ID"
  "auth0-m2m-client-secret|AUTH0_M2M_CLIENT_SECRET"
  "auth0-webhook-secret|AUTH0_WEBHOOK_SECRET"
  "auth0-frontend-secret|AUTH0_SECRET"
  "auth0-client-id|AUTH0_CLIENT_ID"
  "auth0-client-secret|AUTH0_CLIENT_SECRET"
  "openai-api-key|OPENAI_API_KEY"
  "newsapi-api-key|NEWSAPI_API_KEY"
  "ngx-market-data-api-key|NGX_MARKET_DATA_API_KEY"
  "ngx-market-data-base-url|NGX_MARKET_DATA_BASE_URL"
  "x-bearer-token|X_BEARER_TOKEN"
  "serpapi-api-key|SERPAPI_API_KEY"
  "resend-api-key|RESEND_API_KEY"
  "paystack-public-key|PAYSTACK_PUBLIC_KEY"
  "paystack-secret-key|PAYSTACK_SECRET_KEY"
  "sentry-dsn|SENTRY_DSN"
  "logtail-token|LOGTAIL_TOKEN"
  "posthog-api-key|POSTHOG_API_KEY"
  "neo4j-uri|NEO4J_URI"
  "neo4j-user|NEO4J_USER"
  "neo4j-password|NEO4J_PASSWORD"
)

for pair in "${SECRET_MAP[@]}"; do
  secret_name="${pair%%|*}"
  env_name="${pair##*|}"
  value="${!env_name-}"
  full_name="${PREFIX}-${secret_name}"

  if [[ -z "${value}" ]]; then
    echo "[secret-manager] Skipping ${full_name}; ${env_name} is not set"
    continue
  fi

  if ! gcloud secrets describe "${full_name}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud secrets create "${full_name}" --project "${PROJECT_ID}" --replication-policy automatic
  fi

  printf "%s" "${value}" | gcloud secrets versions add "${full_name}" \
    --project "${PROJECT_ID}" \
    --data-file=-
  echo "[secret-manager] Updated ${full_name}"
done

