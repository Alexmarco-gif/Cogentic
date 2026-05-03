#!/usr/bin/env bash
set -euo pipefail

# Seeds AWS Secrets Manager secrets from the current shell environment.

AWS_REGION="${AWS_REGION:-eu-west-2}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
PROJECT_NAME="${PROJECT_NAME:-cogent}"
PREFIX="${PROJECT_NAME}-${ENVIRONMENT}"

declare -a SECRET_NAMES=(
  "SECRET_KEY"
  "AUTH0_DOMAIN"
  "AUTH0_AUDIENCE"
  "AUTH0_SECRET"
  "AUTH0_ISSUER_BASE_URL"
  "AUTH0_CLIENT_ID"
  "AUTH0_CLIENT_SECRET"
  "AUTH0_M2M_CLIENT_ID"
  "AUTH0_M2M_CLIENT_SECRET"
  "AUTH0_WEBHOOK_SECRET"
  "OPENAI_API_KEY"
  "NEWSAPI_API_KEY"
  "NGX_MARKET_DATA_API_KEY"
  "NGX_MARKET_DATA_BASE_URL"
  "X_BEARER_TOKEN"
  "SERPAPI_API_KEY"
  "RESEND_API_KEY"
  "RESEND_FROM_EMAIL"
  "PAYSTACK_PUBLIC_KEY"
  "PAYSTACK_SECRET_KEY"
  "SENTRY_DSN"
  "LOGTAIL_TOKEN"
  "POSTHOG_API_KEY"
  "POSTHOG_HOST"
  "NEO4J_URI"
  "NEO4J_USER"
  "NEO4J_PASSWORD"
)

for env_name in "${SECRET_NAMES[@]}"; do
  value="${!env_name-}"
  secret_id="${PREFIX}/${env_name}"

  if [[ -z "${value}" ]]; then
    echo "[aws-secrets] Skipping ${secret_id}; ${env_name} is not set"
    continue
  fi

  if ! aws secretsmanager describe-secret \
    --region "${AWS_REGION}" \
    --secret-id "${secret_id}" >/dev/null 2>&1; then
    aws secretsmanager create-secret \
      --region "${AWS_REGION}" \
      --name "${secret_id}" \
      --secret-string "${value}" >/dev/null
  else
    aws secretsmanager put-secret-value \
      --region "${AWS_REGION}" \
      --secret-id "${secret_id}" \
      --secret-string "${value}" >/dev/null
  fi

  echo "[aws-secrets] Updated ${secret_id}"
done
