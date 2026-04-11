# Cogent - Infrastructure Setup Guide

**Last Updated:** March 2026
**Purpose:** Step-by-step guide to deploy Cogent from zero to production using the infrastructure and deployment code currently in this repository.

---

## Table of Contents

1. [Environments Overview](#1-environments-overview)
2. [Prerequisites](#2-prerequisites)
3. [GitHub Repository Setup](#3-github-repository-setup)
4. [Azure Infrastructure Setup](#4-azure-infrastructure-setup)
5. [Database Setup](#5-database-setup)
6. [Auth0 Configuration](#6-auth0-configuration)
7. [External Services](#7-external-services)
8. [Key Vault Secret Seeding](#8-key-vault-secret-seeding)
9. [GitHub Secrets and Variables](#9-github-secrets-and-variables)
10. [DNS Configuration](#10-dns-configuration)
11. [First Deployment (Staging)](#11-first-deployment-staging)
12. [Production Deployment](#12-production-deployment)
13. [Post-Deployment Verification](#13-post-deployment-verification)
14. [Go-Live and User Launch](#14-go-live-and-user-launch)
15. [Current Status and Resume Guide](#15-current-status-and-resume-guide)
16. [Detailed Execution Playbook](#16-detailed-execution-playbook)

---

## 1. Environments Overview

Cogent uses two environments: **staging** and **production**.

Each environment has its own:
- Azure resource group
- Azure Container Apps environment
- Azure PostgreSQL Flexible Server
- Azure Redis cache
- Azure Key Vault
- Auth0 application settings
- custom domains

### Staging

| Property | Value |
|----------|-------|
| Purpose | QA, smoke testing, pre-production validation |
| Trigger | Push to `main` deploys staging |
| Frontend URL | `https://staging.cogent.ai` |
| Backend URL | `https://api-staging.cogent.ai` |
| Resource group | `cogent-staging` |
| Resource prefix | `cogent-stg` |
| Backend replicas | 1-2 |
| Worker replicas | 1 |
| Frontend replicas | 1-2 |
| Redis SKU | Basic |
| ACR SKU | Standard |
| PostgreSQL server | `cogent-stg-postgres` |
| Postgres backup retention | 7 days |
| Log retention | 30 days |
| Zone redundancy | Disabled |

### Production

| Property | Value |
|----------|-------|
| Purpose | Live user-facing environment |
| Trigger | GitHub Release publication deploys production |
| Frontend URL | `https://app.cogent.ai` |
| Backend URL | `https://api.cogent.ai` |
| Resource group | `cogent-production` |
| Resource prefix | `cogent-prod` |
| Backend replicas | 2-10 |
| Worker replicas | 2 |
| Frontend replicas | 2-10 |
| Redis SKU | Standard |
| ACR SKU | Standard |
| PostgreSQL server | `cogent-prod-postgres` |
| Postgres backup retention | 35 days |
| Log retention | 90 days |
| Zone redundancy | Enabled |

### Key Differences

| Aspect | Staging | Production |
|--------|---------|------------|
| Deploy trigger | Push to `main` | Release published |
| Redis | Basic | Standard |
| Min backend replicas | 1 | 2 |
| Postgres SKU | Burstable / `Standard_B2ms` | GeneralPurpose / `Standard_D4s_v3` |
| Postgres storage | 32 GB | 128 GB |
| Geo-redundant backup | Disabled | Enabled |
| Log retention | 30 days | 90 days |
| ACA environment | `cogent-stg-env` | `cogent-prod-env` |

---

## 2. Prerequisites

Install these locally before you start:

```bash
# Azure CLI
az --version

# Install or upgrade the Container Apps extension
az extension add --name containerapp --upgrade

# Update Bicep support
az bicep upgrade

# GitHub CLI
gh --version

# Docker
docker --version

# Node.js 20+
node --version

# Python 3.11+
python --version
```

Login:

```bash
az login
az account set --subscription "<your-subscription-id>"

gh auth login
```

---

## 3. GitHub Repository Setup

This section is still valid for the current repo. The deployment workflow expects:

- `main` protected
- PR-based changes into `main`
- GitHub environments named `staging` and `production`
- OIDC-based Azure login from Actions

### 3.1 Recommended Branches

| Branch | Purpose |
|--------|---------|
| `main` | Staging deploy source |
| `feature/*` | Feature work |
| `bugfix/*` | Bug fixes |
| `hotfix/*` | Urgent production fixes |
| `release/*` | Release prep |
| `chore/*` | Tooling / infra / dependency work |

### 3.2 Branch Protection for `main`

Recommended required checks:

| Check |
|-------|
| `Lint & Format` |
| `Type Check (mypy)` |
| `Tests` |
| `Frontend Lint & TypeScript` |
| `Frontend Tests` |

Notes:
- `E2E Tests` currently run on push to `main`, not on PRs.
- `Security Audit` runs on pull requests only.

### 3.3 GitHub Environments

Create:

| Environment | Use |
|-------------|-----|
| `staging` | automatic deploys from `main` |
| `production` | release-gated deploys |

### 3.4 CODEOWNERS

Recommended owners:

```text
*                           @your-github-username
/backend/                   @your-github-username
/frontend/                  @your-github-username
/infrastructure/            @your-github-username
/.github/                   @your-github-username
/scripts/                   @your-github-username
```

---

## 4. Azure Infrastructure Setup

### Step 4.1 - Create Resource Groups

```bash
az group create --name cogent-staging --location uksouth
az group create --name cogent-production --location uksouth
```

### Step 4.2 - Create Azure AD App Registration for GitHub OIDC

```bash
az ad app create --display-name "cogent-github-deploy"

APP_ID="<appId-from-output>"
az ad sp create --id $APP_ID

SP_OBJECT_ID=$(az ad sp show --id $APP_ID --query id -o tsv)
```

Add federated credentials:

```bash
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-staging",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<your-github-org>/cogent:environment:staging",
  "audiences": ["api://AzureADTokenExchange"]
}'

az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-production",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<your-github-org>/cogent:environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

### Step 4.3 - Assign RBAC Roles

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/cogent-staging"

az role assignment create \
  --assignee $SP_OBJECT_ID \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/cogent-production"
```

### Step 4.4 - Deploy Bicep Infrastructure

`infrastructure/main.bicep` provisions:
- Log Analytics
- Azure Container Registry
- Key Vault
- Azure PostgreSQL Flexible Server
- Redis
- Container Apps environment
- backend, worker, frontend container apps
- migration job

Deploy staging first:

```bash
DB_PASS="<strong-random-password>"

az deployment group create \
  --name staging-infra \
  --resource-group cogent-staging \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/staging.bicepparam \
  --parameters dbAdminPassword="$DB_PASS"

az deployment group show \
  --name staging-infra \
  --resource-group cogent-staging \
  --query properties.outputs -o json
```

Then production:

```bash
DB_PASS="<strong-random-password>"

az deployment group create \
  --name production-infra \
  --resource-group cogent-production \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/production.bicepparam \
  --parameters dbAdminPassword="$DB_PASS"

az deployment group show \
  --name production-infra \
  --resource-group cogent-production \
  --query properties.outputs -o json
```

### Step 4.5 - Expected Resource Names

| Resource | Staging | Production |
|----------|---------|------------|
| Log Analytics | `cogent-stg-logs` | `cogent-prod-logs` |
| ACR | `cogentacrstg` | `cogentacrprod` |
| Key Vault | `cogent-stg-kv` | `cogent-prod-kv` |
| PostgreSQL | `cogent-stg-postgres` | `cogent-prod-postgres` |
| Redis | `cogent-stg-redis` | `cogent-prod-redis` |
| ACA env | `cogent-stg-env` | `cogent-prod-env` |
| Backend app | `cogent-stg-backend` | `cogent-prod-backend` |
| Worker app | `cogent-stg-worker` | `cogent-prod-worker` |
| Frontend app | `cogent-stg-frontend` | `cogent-prod-frontend` |
| Migration job | `cogent-stg-migrate` | `cogent-prod-migrate` |

### Step 4.6 - Grant ACR Push Permissions

```bash
STG_ACR_ID=$(az acr show --name cogentacrstg --query id -o tsv)
PROD_ACR_ID=$(az acr show --name cogentacrprod --query id -o tsv)

az role assignment create --assignee $SP_OBJECT_ID --role "AcrPush" --scope $STG_ACR_ID
az role assignment create --assignee $SP_OBJECT_ID --role "AcrPush" --scope $PROD_ACR_ID
```

---

## 5. Database Setup

Cogent now uses **Azure Database for PostgreSQL Flexible Server**, not Neon.

### Step 5.1 - What Bicep Creates

`infrastructure/modules/postgres.bicep` creates:

| Setting | Staging | Production |
|---------|---------|------------|
| PostgreSQL version | 16 | 16 |
| Database name | `cogent` | `cogent` |
| TLS minimum | 1.2 | 1.2 |
| `pgvector` extension | Enabled | Enabled |
| Firewall rule | `AllowAzureServices` | `AllowAzureServices` |
| High availability | Disabled | Disabled in current template |

### Step 5.2 - Verify Server and Database

```bash
az postgres flexible-server show \
  --name cogent-stg-postgres \
  --resource-group cogent-staging \
  --output table

az postgres flexible-server db show \
  --server-name cogent-stg-postgres \
  --resource-group cogent-staging \
  --database-name cogent \
  --output table
```

Repeat for production with `cogent-prod-postgres` and `cogent-production`.

### Step 5.3 - Database Connection Secret

`infrastructure/main.bicep` creates the Key Vault secret `database-url` automatically from the PostgreSQL server outputs.

You do **not** need to seed `DATABASE_URL` manually unless you are intentionally overriding the generated value.

Verify:

```bash
az keyvault secret show \
  --vault-name cogent-stg-kv \
  --name database-url \
  --query value -o tsv
```

### Step 5.4 - Migration Job

The deploy workflow runs the existing manual Container Apps Job:

```bash
az containerapp job start \
  --name cogent-stg-migrate \
  --resource-group cogent-staging
```

The production equivalent is `cogent-prod-migrate`.

---

## 6. Auth0 Configuration

### Step 6.1 - Create Auth0 Tenant / Applications

Create:
- a **Regular Web Application** for the frontend
- a **Machine-to-Machine** application for smoke tests, CI health checks, and admin automation
- an API representing Cogent

### Step 6.2 - Regular Web Application

| Setting | Staging | Production |
|---------|---------|------------|
| Name | Cogent Frontend (Staging) | Cogent Frontend |
| Application Type | `Regular Web Application` | `Regular Web Application` |
| Initiate Login URI | `https://staging.cogent.ai/api/auth/login` | `https://app.cogent.ai/api/auth/login` |
| Callback URL | `https://staging.cogent.ai/api/auth/callback` | `https://app.cogent.ai/api/auth/callback` |
| Logout URL | `https://staging.cogent.ai` | `https://app.cogent.ai` |
| Web Origin | `https://staging.cogent.ai` | `https://app.cogent.ai` |
| Token Endpoint Authentication Method | `Post` | `Post` |

Important:
- Do **not** configure the frontend as a Single Page Application. The current app uses `@auth0/nextjs-auth0/server`, stores an encrypted session cookie, and requires a client secret.
- The frontend runtime expects `AUTH0_SECRET`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, and `AUTH0_ISSUER_BASE_URL`.

### Step 6.3 - Connections

Enable these Auth0 connections because the frontend links directly to them:

| Connection | Required | Where it is used |
|------------|----------|------------------|
| `Username-Password-Authentication` | Yes | email login, signup, password reset |
| `google-oauth2` | Yes | social login buttons on login/signup pages |
| `linkedin` | Yes | social login buttons on login/signup pages |
| `github` | Yes | social login buttons on login/signup pages |

### Step 6.4 - API and Authorization Model

| Setting | Value |
|---------|-------|
| Name | Cogent API |
| Identifier | `https://api.cogent.ai` |
| Signing algorithm | `RS256` |
| Audience checked by backend | `AUTH0_AUDIENCE` |
| Runtime authorization model | namespaced claims + org role |
| OAuth scopes such as `read:*` / `write:*` / `delete:*` | not currently enforced by FastAPI route guards |
| Internal API-key scopes currently used by app code | `read:documents`, `write:documents` |

Auth0 scopes are **not** the primary authorization mechanism in the current codebase. The live backend checks org membership, role, and namespaced claims instead.

Runtime roles / permissions expected by the app:

| Type | Values used in code |
|------|---------------------|
| Org roles | `viewer`, `member`, `analyst`, `admin`, `owner` |
| Permission gates | `view_signals`, `manage_signals`, `manage_regulatory_knowledge`, plus role gates such as `admin`, `owner`, `analyst` |

### Step 6.5 - Machine-to-Machine Application

| Setting | Value |
|---------|-------|
| Application Type | `Machine to Machine` |
| Authorized API | `Cogent API` |
| Grant Type | `client_credentials` |
| Used for | smoke tests, deployment verification, service-to-service administration |

The backend requires the M2M access token to carry these custom claims:

| Claim | Required | Purpose |
|-------|----------|---------|
| `https://cogent.ai/claims/org_id` | Yes | tenant context |
| `https://cogent.ai/claims/user_id` | Yes | service-account user UUID |
| `https://cogent.ai/claims/role` | Yes | authorization role, usually `admin` or `owner` |
| `https://cogent.ai/claims/email` | Recommended | clearer audit trail |

### Step 6.6 - Auth0 Actions

Use a **Post Login** action to add the user claims the frontend and backend expect:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://cogent.ai/claims/';
  const appMeta = event.user.app_metadata || {};
  const userMeta = event.user.user_metadata || {};
  const orgId = appMeta.org_id || userMeta.org_id;
  const plan = appMeta.plan || userMeta.plan || 'explorer';
  const roles = event.authorization?.roles || appMeta.roles || [];

  api.idToken.setCustomClaim(`${namespace}email`, event.user.email);
  api.accessToken.setCustomClaim(`${namespace}email`, event.user.email);
  api.idToken.setCustomClaim(`${namespace}roles`, roles);
  api.accessToken.setCustomClaim(`${namespace}roles`, roles);
  api.idToken.setCustomClaim(`${namespace}plan`, plan);
  api.accessToken.setCustomClaim(`${namespace}plan`, plan);

  if (orgId) {
    api.idToken.setCustomClaim(`${namespace}org_id`, orgId);
    api.accessToken.setCustomClaim(`${namespace}org_id`, orgId);
  }
};
```

Use a **Client Credentials Exchange** action for the M2M app:

```javascript
exports.onExecuteCredentialsExchange = async (event, api) => {
  const namespace = 'https://cogent.ai/claims/';
  const meta = event.client.metadata || {};

  api.accessToken.setCustomClaim(`${namespace}org_id`, meta.org_id);
  api.accessToken.setCustomClaim(`${namespace}user_id`, meta.user_id);
  api.accessToken.setCustomClaim(`${namespace}role`, meta.role || 'admin');

  if (meta.email) {
    api.accessToken.setCustomClaim(`${namespace}email`, meta.email);
  }
};
```

Recommended Auth0 application metadata for the M2M app:

| Metadata key | Value |
|--------------|-------|
| `org_id` | target organization UUID |
| `user_id` | local service-account user UUID |
| `role` | `admin` or `owner` |
| `email` | optional audit email such as `deploy-bot@cogent.ai` |

### Step 6.7 - Auth0 Log Stream

Configure a **Custom Webhook** log stream:

| Setting | Staging | Production |
|---------|---------|------------|
| URL | `https://staging.cogent.ai/api/webhooks/auth0` | `https://app.cogent.ai/api/webhooks/auth0` |
| Authorization Token | secure random token | secure random token |
| Content Type | `application/json` | `application/json` |
| Content Format | JSON Lines | JSON Lines |

Events to include:
- `s`
- `ss`
- `f`
- `spr`
- `sad`

Important:
- The Auth0 log stream hits the **frontend** route, not the backend directly.
- The token above becomes `AUTH0_WEBHOOK_SECRET`.
- The frontend validates the bearer token from Auth0, then forwards normalized events to the backend `/webhooks/auth0/events`.

### Step 6.8 - Auth0 Secrets Summary

| Secret | Where | Notes |
|--------|-------|-------|
| `AUTH0_DOMAIN` | Key Vault | shared by backend |
| `AUTH0_AUDIENCE` | Key Vault | shared by backend and frontend |
| `AUTH0_M2M_CLIENT_ID` | Key Vault | backend |
| `AUTH0_M2M_CLIENT_SECRET` | Key Vault | backend |
| `AUTH0_WEBHOOK_SECRET` | Key Vault | frontend inbound token, backend forward verification |
| `AUTH0_SECRET` | Key Vault | frontend session encryption |
| `AUTH0_ISSUER_BASE_URL` | Key Vault | frontend |
| `AUTH0_CLIENT_ID` | Key Vault | frontend |
| `AUTH0_CLIENT_SECRET` | Key Vault | frontend |

---

## 7. External Services

### 7.1 Required for Production Launch

These services are treated as part of the production deployment path and are now wired into runtime configuration through `infrastructure/main.bicep` plus Key Vault secrets.

| Service | Required | Why | Runtime |
|---------|----------|-----|---------|
| OpenAI | Yes | chat, synthesis, embeddings | backend, worker |
| Sentry | Yes | production error visibility | backend |
| PostHog | Yes | product analytics and operational event tracking | backend |
| Better Stack / Logtail | Yes | centralized log shipping | backend |
| Resend | Yes | transactional emails and privacy/export notifications | backend, worker |
| SerpApi | Yes | external search enrichment | backend, worker |
| NewsAPI | Yes | provider-backed article ingestion contracts | backend, worker |
| NGX Market Data API | Yes | official Nigerian Exchange market data contracts | backend, worker |
| X API | Yes | provider-backed social signal contracts for X | backend, worker |
| Azure Blob Storage | Yes | model / artifact storage used by background jobs | backend, worker |

### 7.2 Paystack Billing

Cogent's paid plan checkout now runs through a real Paystack integration:

- frontend inline popup checkout
- backend-created recurring plans
- backend transaction verification before tier activation
- signed webhook handling for subscription lifecycle events

Required backend settings:

```bash
PAYSTACK_PUBLIC_KEY=<paystack-public-key>
PAYSTACK_SECRET_KEY=<paystack-secret-key>
PAYSTACK_BASE_URL=https://api.paystack.co
CORS_ORIGINS=http://localhost:3000,https://<your-frontend-domain>
```

Required frontend settings:

```bash
AUTH0_BASE_URL=https://<your-frontend-domain>
APP_BASE_URL=https://<your-frontend-domain>
BACKEND_URL=https://<your-backend-domain>
NEXT_PUBLIC_PAYSTACK_CALLBACK_URL=https://<your-frontend-domain>/dashboard/settings?tab=plan&paystack=return
```

If the public URL points to the frontend app, configure Paystack with:

- callback URL: `https://<your-frontend-domain>/dashboard/settings?tab=plan&paystack=return`
- webhook URL: `https://<your-frontend-domain>/api/webhooks/paystack/events`

Notes:

- The frontend webhook route relays the signed payload to the backend webhook handler.
- The same code path is used in test and live mode; only the keys and deployed URLs change.
- The backend billing configuration currently creates `USD` monthly plans programmatically for the paid tiers.

Local dev helpers:

- Start the backend with [`scripts/start-backend-dev.ps1`](c:/Users/Alex Marco/Documents/Cogent/scripts/start-backend-dev.ps1). This clears any stale shell-level `REDIS_URL` override before launching Uvicorn, so the repo `.env` value wins.
- Start the frontend with [`scripts/start-frontend-dev.ps1`](c:/Users/Alex Marco/Documents/Cogent/scripts/start-frontend-dev.ps1). This uses [`frontend/.env.local`](c:/Users/Alex Marco/Documents/Cogent/frontend/.env.local) and serves Next.js on port `3000` by default.
- The expected local pairing is:
  `backend/.env` equivalent via [`.env`](c:/Users/Alex Marco/Documents/Cogent/.env) for FastAPI and [`frontend/.env.local`](c:/Users/Alex Marco/Documents/Cogent/frontend/.env.local) for Next.js.

### 7.3 OpenAI

Create an API key and set:
- `OPENAI_API_KEY`

Current model usage in code:
- `gpt-4o`
- `gpt-4o-mini`
- `text-embedding-3-small`

### 7.4 Sentry

Create a DSN and set:
- `SENTRY_DSN`

### 7.5 PostHog

| Setting | Value |
|---------|-------|
| Project API key | `POSTHOG_API_KEY` |
| Host / ingestion URL | `POSTHOG_HOST` |
| Runtime | backend |

### 7.6 Better Stack / Logtail

| Setting | Value |
|---------|-------|
| Source token | `LOGTAIL_TOKEN` |
| Runtime | backend |

### 7.7 Resend

| Setting | Value |
|---------|-------|
| API key | `RESEND_API_KEY` |
| Verified sender | `RESEND_FROM_EMAIL` |
| Runtime | backend, worker |

### 7.8 SerpApi

| Setting | Value |
|---------|-------|
| API key | `SERPAPI_API_KEY` |
| Runtime | backend, worker |

### 7.9 NewsAPI

| Setting | Value |
|---------|-------|
| API key | `NEWSAPI_API_KEY` |
| Runtime | backend, worker |
| Contract source type | `api` |
| Contract provider preset | `newsapi` |

Notes:
- The Contract Studio now supports a `NewsAPI` preset under `Source type = api`.
- The backend injects the runtime API key automatically; you do not store it per contract.

### 7.10 NGX Pulse API

| Setting | Value |
|---------|-------|
| API key | `NGX_MARKET_DATA_API_KEY` |
| Base URL / default endpoint | `NGX_MARKET_DATA_BASE_URL` |
| Runtime | backend, worker |
| Contract source type | `api` |
| Contract provider preset | `ngx_market_data` |

Notes:
- Use your licensed NGX Pulse base endpoint, typically `https://ngxpulse.ng/api/ngxdata/market` or another documented Pulse route from your dashboard.
- If a contract supplies a full `source_url`, that contract URL wins.
- If a contract leaves the endpoint blank, the backend falls back to `NGX_MARKET_DATA_BASE_URL`.

### 7.11 X API

| Setting | Value |
|---------|-------|
| Bearer token | `X_BEARER_TOKEN` |
| Runtime | backend, worker |
| Contract source type | `social` |
| Contract provider preset | `x` |

Notes:
- The Contract Studio now supports an `X` preset under `Source type = social`.
- The backend injects the runtime bearer token automatically; you do not store it per contract.

### 7.12 LinkedIn Public Scraper

No separate API credential is required for this path.

| Setting | Value |
|---------|-------|
| Runtime | backend |
| Contract source type | `scraper` |
| Contract provider preset | `linkedin_public` |

Notes:
- This is a public-page scraper, not a LinkedIn partner API integration.
- Provide the public LinkedIn company or profile URL in the contract.
- The scraper runs with preset selectors and request headers but still uses the normal contract scheduler and worker flow.

### 7.13 Azure Blob Storage

Provision a Storage Account and Blob container for model / artifact persistence.

| Setting | Value |
|---------|-------|
| Connection string | `AZURE_BLOB_CONNECTION_STRING` |
| Container name | `AZURE_BLOB_MODEL_CONTAINER` |
| Suggested container | `ml-models` |
| Runtime | backend, worker |

### 7.14 Reserved Runtime Settings

`NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` still exist in backend config, but there is no active production runtime path in the current codebase that requires Neo4j for go-live. Keep these out of the launch checklist unless you intentionally enable that graph path later.

---

## 8. Key Vault Secret Seeding

Use `scripts/seed-keyvault.sh` or `scripts/seed-keyvault.ps1` after infrastructure is provisioned.

### Step 8.1 - Staging Secret Exports

```bash
export REDIS_URL="rediss://:$(az redis list-keys --name cogent-stg-redis --resource-group cogent-staging --query primaryKey -o tsv)@cogent-stg-redis.redis.cache.windows.net:6380/0"
export SECRET_KEY="$(openssl rand -hex 32)"
export AUTH0_DOMAIN="cogent-staging.auth0.com"
export AUTH0_AUDIENCE="https://api.cogent.ai"
export AUTH0_M2M_CLIENT_ID="<from-auth0>"
export AUTH0_M2M_CLIENT_SECRET="<from-auth0>"
export AUTH0_WEBHOOK_SECRET="<same-token-used-in-auth0-log-stream>"
export OPENAI_API_KEY="sk-..."
export SENTRY_DSN="https://<key>@sentry.io/<project>"
export LOGTAIL_TOKEN="<better-stack-source-token>"
export POSTHOG_API_KEY="<posthog-project-api-key>"
export POSTHOG_HOST="https://<your-posthog-host>"
export RESEND_API_KEY="re_..."
export RESEND_FROM_EMAIL="Cogent <notifications@yourdomain.com>"
export SERPAPI_API_KEY="<from-serpapi>"
export NEWSAPI_API_KEY="<from-newsapi>"
export NGX_MARKET_DATA_API_KEY="<from-ngx-pulse>"
export NGX_MARKET_DATA_BASE_URL="https://ngxpulse.ng/api/ngxdata/market"
export X_BEARER_TOKEN="<from-x-api>"
export AZURE_BLOB_CONNECTION_STRING="<from-storage-account>"
export AZURE_BLOB_MODEL_CONTAINER="ml-models"
export AUTH0_SECRET="$(openssl rand -hex 32)"
export AUTH0_ISSUER_BASE_URL="https://cogent-staging.auth0.com"
export AUTH0_CLIENT_ID="<from-auth0>"
export AUTH0_CLIENT_SECRET="<from-auth0>"
```

Do **not** export `DATABASE_URL` here unless you deliberately want to override the Bicep-generated Key Vault secret.

### Step 8.1b - Staging Secret Exports (PowerShell)

```powershell
$env:REDIS_URL = "rediss://:$(az redis list-keys --name cogent-stg-redis --resource-group cogent-staging --query primaryKey -o tsv)@cogent-stg-redis.redis.cache.windows.net:6380/0"
$env:SECRET_KEY = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
$env:AUTH0_DOMAIN = "cogent-staging.auth0.com"
$env:AUTH0_AUDIENCE = "https://api.cogent.ai"
$env:AUTH0_M2M_CLIENT_ID = "<from-auth0>"
$env:AUTH0_M2M_CLIENT_SECRET = "<from-auth0>"
$env:AUTH0_WEBHOOK_SECRET = "<same-token-used-in-auth0-log-stream>"
$env:OPENAI_API_KEY = "sk-..."
$env:SENTRY_DSN = "https://<key>@sentry.io/<project>"
$env:LOGTAIL_TOKEN = "<better-stack-source-token>"
$env:POSTHOG_API_KEY = "<posthog-project-api-key>"
$env:POSTHOG_HOST = "https://<your-posthog-host>"
$env:RESEND_API_KEY = "re_..."
$env:RESEND_FROM_EMAIL = "Cogent <notifications@yourdomain.com>"
$env:SERPAPI_API_KEY = "<from-serpapi>"
$env:NEWSAPI_API_KEY = "<from-newsapi>"
$env:NGX_MARKET_DATA_API_KEY = "<from-ngx-pulse>"
$env:NGX_MARKET_DATA_BASE_URL = "https://ngxpulse.ng/api/ngxdata/market"
$env:X_BEARER_TOKEN = "<from-x-api>"
$env:AZURE_BLOB_CONNECTION_STRING = "<from-storage-account>"
$env:AZURE_BLOB_MODEL_CONTAINER = "ml-models"
$env:AUTH0_SECRET = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
$env:AUTH0_ISSUER_BASE_URL = "https://cogent-staging.auth0.com"
$env:AUTH0_CLIENT_ID = "<from-auth0>"
$env:AUTH0_CLIENT_SECRET = "<from-auth0>"
```

Do **not** set `DATABASE_URL` here unless you deliberately want to override the Bicep-generated Key Vault secret.

### Step 8.2 - Seed Key Vault

```bash
VAULT_NAME=cogent-stg-kv ./scripts/seed-keyvault.sh
az keyvault secret list --vault-name cogent-stg-kv --output table
```

PowerShell equivalent:

```powershell
.\scripts\seed-keyvault.ps1 -VaultName cogent-stg-kv
az keyvault secret list --vault-name cogent-stg-kv --output table
```

The seeding script now fails fast if any required deployment secret is missing.

### Step 8.3 - Repeat for Production

Use production values, then:

```bash
VAULT_NAME=cogent-prod-kv ./scripts/seed-keyvault.sh
```

PowerShell equivalent:

```powershell
.\scripts\seed-keyvault.ps1 -VaultName cogent-prod-kv
```

---

## 9. GitHub Secrets and Variables

### 9.1 Repository Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Azure OIDC app registration client ID |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |

### 9.2 Environment Secrets

**Staging**

| Secret | Value |
|--------|-------|
| `ACR_NAME` | `cogentacrstg` |
| `SMOKE_TEST_TOKEN` | valid Auth0 M2M token with `org_id`, `user_id`, and `role` claims |
| `E2E_USERNAME` | staging test account |
| `E2E_PASSWORD` | staging test account password |

**Production**

| Secret | Value |
|--------|-------|
| `ACR_NAME` | `cogentacrprod` |
| `SMOKE_TEST_TOKEN` | valid Auth0 M2M token with `org_id`, `user_id`, and `role` claims |

### 9.3 Environment Variables

**Staging**

| Variable | Value |
|----------|-------|
| `ACR_LOGIN_SERVER` | `cogentacrstg.azurecr.io` |
| `AZURE_RESOURCE_GROUP` | `cogent-staging` |
| `BACKEND_FQDN` | `cogent-stg-backend.<region>.azurecontainerapps.io` |
| `FRONTEND_FQDN` | `cogent-stg-frontend.<region>.azurecontainerapps.io` |
| `NEXT_PUBLIC_API_URL` | `https://api-staging.cogent.ai` |
| `STAGING_FRONTEND_URL` | `https://staging.cogent.ai` |

**Production**

| Variable | Value |
|----------|-------|
| `ACR_LOGIN_SERVER` | `cogentacrprod.azurecr.io` |
| `AZURE_RESOURCE_GROUP` | `cogent-production` |
| `BACKEND_FQDN` | `cogent-prod-backend.<region>.azurecontainerapps.io` |
| `FRONTEND_FQDN` | `cogent-prod-frontend.<region>.azurecontainerapps.io` |
| `NEXT_PUBLIC_API_URL` | `https://api.cogent.ai` |

---

## 10. DNS Configuration

### Step 10.1 - Get ACA FQDNs

```bash
az containerapp show --name cogent-stg-backend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name cogent-stg-frontend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv

az containerapp show --name cogent-prod-backend --resource-group cogent-production --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name cogent-prod-frontend --resource-group cogent-production --query properties.configuration.ingress.fqdn -o tsv
```

### Step 10.2 - DNS Records

| Record | Type | Name | Value |
|--------|------|------|-------|
| Staging API | CNAME | `api-staging` | `cogent-stg-backend.<region>.azurecontainerapps.io` |
| Staging Frontend | CNAME | `staging` | `cogent-stg-frontend.<region>.azurecontainerapps.io` |
| Production API | CNAME | `api` | `cogent-prod-backend.<region>.azurecontainerapps.io` |
| Production Frontend | CNAME | `app` | `cogent-prod-frontend.<region>.azurecontainerapps.io` |

### Step 10.3 - Bind Custom Domains

```bash
az containerapp hostname add \
  --name cogent-stg-backend \
  --resource-group cogent-staging \
  --hostname api-staging.cogent.ai
```

Repeat for frontend and production resources.

---

## 11. First Deployment (Staging)

### Step 11.1 - Fresh-Clone and Source-Control Gate

Before the first staging deploy, validate the exact source state that CI and GitHub Actions will see:

- [ ] `frontend/lib` is tracked and present in a clean checkout
- [ ] tracked deletions are intentional, including `frontend/public/error.JPG` if it remains deleted
- [ ] CI is green from a fresh clone, not only from a long-lived local workspace

### Step 11.2 - Trigger Deploy

```bash
git checkout main
git push origin main
```

The deploy workflow will:
1. run CI
2. build backend, worker, and frontend images
3. push to ACR
4. start `cogent-stg-migrate`
5. update `cogent-stg-backend`, `cogent-stg-worker`, and `cogent-stg-frontend`
6. run smoke tests

### Step 11.3 - Watch Deployment

```bash
gh run watch
```

### Step 11.4 - Verify Staging

```bash
curl https://api-staging.cogent.ai/health

SMOKE_TOKEN="Bearer <token>" bash scripts/smoke-test.sh https://api-staging.cogent.ai

curl -s -o /dev/null -w "%{http_code}" https://staging.cogent.ai
```

### Step 11.5 - Staging Checklist

- [ ] `/health` returns `200`
- [ ] frontend loads
- [ ] Auth0 login works
- [ ] Auth0 callback, session refresh, and logout work despite the current Next/Auth0 Edge runtime warning
- [ ] Auth0 log stream hits `https://staging.cogent.ai/api/webhooks/auth0`
- [ ] migrations complete successfully
- [ ] the `signal_contracts.org_id` migration is applied on staging
- [ ] tenant isolation is verified: one org cannot see another org's contracts or org-scoped signals
- [ ] smoke tests pass
- [ ] Sentry receives events
- [ ] PostHog receives events
- [ ] Better Stack / Logtail receives logs
- [ ] Resend can deliver a staging test email
- [ ] SerpApi-backed search succeeds
- [ ] NewsAPI contract fetch succeeds
- [ ] NGX Market Data contract fetch succeeds
- [ ] X contract fetch succeeds
- [ ] LinkedIn public scraper contract fetch succeeds
- [ ] Azure Blob connection succeeds for background job storage paths

---

## 12. Production Deployment

### Step 12.1 - Production Promotion Gate

Do not cut the production release until all staging signoff checks are green:

- [ ] staging deploy completed cleanly
- [ ] org-scope migration has run and tenant isolation is confirmed
- [ ] Auth0 session and middleware behavior is verified in staging
- [ ] CI is still green from a fresh clone
- [ ] the Git tree contains the committed frontend source needed by production

### Step 12.2 - Create Release

```bash
git tag v1.0.0
git push origin v1.0.0

gh release create v1.0.0 \
  --title "v1.0.0 - Initial Production Release" \
  --notes "First production deployment of Cogent."
```

### Step 12.3 - Production Flow

The production workflow will:
1. run CI
2. build and push tagged images
3. start `cogent-prod-migrate`
4. update production container apps
5. run smoke tests
6. run canary verification

### Step 12.4 - Post-Deploy Monitoring

```bash
nohup bash scripts/post-deploy-monitor.sh \
  --backend-url https://api.cogent.ai \
  --frontend-url https://app.cogent.ai \
  --slack-webhook "$SLACK_WEBHOOK_URL" &
```

---

## 13. Post-Deployment Verification

### 13.1 - Paystack Billing

After deploying billing changes, verify the payment flow end-to-end:

1. Run the latest migration:
   `alembic upgrade head`
2. Open the frontend settings plan page.
3. Start an upgrade to `Growth` or another paid tier.
4. Confirm the Paystack inline popup opens.
5. Complete checkout with a Paystack test card when using test keys.
6. Confirm the browser returns to:
   `https://<your-frontend-domain>/dashboard/settings?tab=plan&paystack=return`
7. Confirm Paystack delivers a webhook to:
   `https://<your-frontend-domain>/api/webhooks/paystack/events`
8. Confirm the backend verifies the reference and activates the purchased tier.
9. Confirm monthly credits are reset to the purchased plan allocation.

Troubleshooting checks:

- frontend console for blocked popup, script, or CSP issues
- Paystack dashboard webhook delivery logs
- backend logs for verify or webhook signature failures
- local subscription data for missing provider plan or subscription codes

### 13.2 - Rollback

```bash
az containerapp revision list \
  --name cogent-prod-backend \
  --resource-group cogent-production \
  --output table

az containerapp revision activate \
  --name cogent-prod-backend \
  --resource-group cogent-production \
  --revision <previous-revision-name>

az containerapp ingress traffic set \
  --name cogent-prod-backend \
  --resource-group cogent-production \
  --revision-weight <previous-revision-name>=100
```

### 13.3 - Ongoing Operations

| Task | Frequency | How |
|------|-----------|-----|
| Check error rates | Daily | Sentry |
| Review uptime | Daily | uptime monitor |
| Check PostgreSQL metrics | Weekly | Azure Portal -> PostgreSQL Flexible Server |
| Review Redis memory | Weekly | Azure Portal -> Redis |
| Run load tests | Before major releases | `scripts/load_test.py` |
| Rotate secrets | Quarterly | reseed Key Vault |
| Review logs | Weekly | Log Analytics / Better Stack |

### 13.4 - Useful Commands

```bash
az containerapp logs show \
  --name cogent-prod-backend \
  --resource-group cogent-production \
  --follow

az keyvault secret list --vault-name cogent-prod-kv --output table

az postgres flexible-server show \
  --name cogent-prod-postgres \
  --resource-group cogent-production \
  --output table
```

---

## 14. Go-Live and User Launch

### 14.1 - Production Go-Live Gate

Users should only be sent to production after all of these are green:

- [ ] `https://app.cogent.ai` loads successfully
- [ ] `https://api.cogent.ai/health` returns `200`
- [ ] production migrations completed successfully
- [ ] Auth0 production callbacks, logout URLs, and log stream are active
- [ ] Paystack live public and secret keys are loaded into the deployed environment
- [ ] Paystack production callback URL points to the frontend settings return page
- [ ] Paystack production webhook URL points to `/api/webhooks/paystack/events`
- [ ] one successful end-to-end live payment has been verified
- [ ] smoke tests pass with the production M2M token
- [ ] Sentry, PostHog, and Better Stack / Logtail are receiving production traffic
- [ ] Resend can deliver production emails
- [ ] provider-backed contract fetches succeed for NewsAPI, NGX Market Data, X, and LinkedIn public scraping

### 14.2 - Open the Product to Users

At that point the launch path is:

1. Keep the production release live on GitHub.
2. Confirm custom domains and TLS are active for `app.cogent.ai` and `api.cogent.ai`.
3. Leave the required Auth0 connections enabled: email/password, Google, LinkedIn, and GitHub.
4. Send users to `https://app.cogent.ai` to sign in or create accounts.
5. Monitor logs, errors, and health metrics closely for the first 24-72 hours.

### 14.3 - First-Day Operating Watchlist

- [ ] watch Container Apps logs for backend, worker, and frontend
- [ ] watch PostgreSQL CPU/connections and Redis memory
- [ ] watch Sentry for new exceptions
- [ ] watch PostHog ingestion and Better Stack log flow
- [ ] confirm Auth0 webhook events continue to arrive
- [ ] verify at least one end-to-end user signup/login journey in production

---

## 15. Current Status and Resume Guide

This section is the **continue-from-here deployment runbook** for the exact point already reached in staging.

### 15.1 - Current Confirmed Staging Progress

The following has already been completed in Azure:

| Component | Status | Notes |
|----------|--------|-------|
| Resource group | Done | `cogent-staging` |
| ACR | Done | `cogentacrstg.azurecr.io` |
| Key Vault | Done | `cogent-stg-kv` |
| PostgreSQL | Done | `cogent-stg-postgres` |
| Redis | Done | `cogent-stg-redis` |
| Log Analytics | Done | `cogent-stg-logs` |
| Container Apps environment | Done | `cogent-stg-env` |
| Base infra deployment | Done | `staging-infra` succeeded with `deployWorkloads=false` |
| Key Vault secret seeding | Done | required runtime secrets are present |
| App workloads | Not complete | backend, worker, frontend, and migrate job still need a clean workload deployment with valid images |

### 15.2 - Where You Have Stopped

You have already finished:

1. Azure base infrastructure
2. Key Vault access and seeding
3. External-service secret collection
4. Blob storage setup and blob secret storage

You are currently at the point where you must:

1. verify which ACR image tags already exist
2. build and push any missing images
3. deploy the workload layer
4. verify the live staging apps

### 15.3 - The Exact Order To Continue

Follow these steps in order.

#### Step 15.3.1 - Verify Key Vault One Last Time

```powershell
az keyvault secret list --vault-name cogent-stg-kv --output table
```

Expected staging secrets include:

- `database-url`
- `redis-url`
- `secret-key`
- `auth0-domain`
- `auth0-audience`
- `auth0-m2m-client-id`
- `auth0-m2m-client-secret`
- `auth0-webhook-secret`
- `auth0-frontend-secret`
- `auth0-issuer-base-url`
- `auth0-client-id`
- `auth0-client-secret`
- `openai-api-key`
- `sentry-dsn`
- `logtail-token`
- `posthog-api-key`
- `posthog-host`
- `resend-api-key`
- `resend-from-email`
- `serpapi-api-key`
- `newsapi-api-key`
- `ngx-market-data-api-key`
- `ngx-market-data-base-url`
- `x-bearer-token`
- `azure-blob-connection-string`
- `azure-blob-model-container`

If these are present, continue. If not, reseed before moving on.

#### Step 15.3.2 - Check ACR Tags Before Building

```powershell
az acr repository show-tags --name cogentacrstg --repository cogent-backend -o table
az acr repository show-tags --name cogentacrstg --repository cogent-worker -o table
az acr repository show-tags --name cogentacrstg --repository cogent-frontend -o table
```

What to look for:

- if `latest` exists, that repository is ready for deployment
- if the repository is missing or `latest` is missing, build it

#### Step 15.3.3 - Build Backend Image

Run from the repository root:

```powershell
az acr build --registry cogentacrstg --image cogent-backend:latest --file Dockerfile .
```

What this does:

- uploads the backend source bundle to ACR
- performs the Docker build remotely
- publishes `cogent-backend:latest`

If your network drops while logs are streaming, rerun the command or verify the tag before retrying.

#### Step 15.3.4 - Build Worker Image

Run from the repository root:

```powershell
az acr build --registry cogentacrstg --image cogent-worker:latest --file Dockerfile.worker .
```

This builds and pushes the worker image used by the background job processor.

#### Step 15.3.5 - Build Frontend Image

Run from the repository root:

```powershell
az acr build --registry cogentacrstg --image cogent-frontend:latest --file frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=https://cogent-stg-backend.purpleglacier-069239e0.uksouth.azurecontainerapps.io ./frontend
```

This builds the Next.js frontend image and bakes the staging API URL into the image build.

#### Step 15.3.6 - Confirm All Three Images Exist

Rerun:

```powershell
az acr repository show-tags --name cogentacrstg --repository cogent-backend -o table
az acr repository show-tags --name cogentacrstg --repository cogent-worker -o table
az acr repository show-tags --name cogentacrstg --repository cogent-frontend -o table
```

You want:

- `cogent-backend:latest`
- `cogent-worker:latest`
- `cogent-frontend:latest`

#### Step 15.3.7 - Deploy Staging Workloads

Once the tags exist, deploy the app layer:

```powershell
az --% deployment group create --name staging-infra-apps --resource-group cogent-staging --template-file infrastructure/main.bicep --parameters infrastructure/parameters/staging.bicepparam --parameters dbAdminPassword=$DB_PASS keyVaultOperatorObjectId=d3b1d22c-0060-488a-ac8e-fa0958733078 deployWorkloads=true
```

This step creates or updates:

- `cogent-stg-backend`
- `cogent-stg-worker`
- `cogent-stg-frontend`
- `cogent-stg-migrate`

#### Step 15.3.8 - Verify Azure Container Apps

After the workload deployment finishes:

```powershell
az containerapp list --resource-group cogent-staging --output table
az containerapp show --name cogent-stg-backend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name cogent-stg-frontend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp job show --name cogent-stg-migrate --resource-group cogent-staging -o json
```

Expected result:

- backend exists
- worker exists
- frontend exists
- migration job exists
- backend and frontend return FQDNs

#### Step 15.3.9 - Run or Verify the Migration Job

If needed, start the migration job manually:

```powershell
az containerapp job start --name cogent-stg-migrate --resource-group cogent-staging
az containerapp job execution list --name cogent-stg-migrate --resource-group cogent-staging -o table
```

You want the migration execution to complete successfully.

#### Step 15.3.10 - Verify Health and Frontend Access

Backend:

```powershell
curl https://api-staging.cogent.ai/health
```

If staging DNS is not live yet, use the direct backend Container Apps FQDN instead.

Frontend:

- open `https://staging.cogent.ai` if DNS is already configured
- otherwise open the frontend Container Apps FQDN in your browser

You want:

- backend health returns `200`
- frontend loads

#### Step 15.3.11 - Verify Auth0

Check all of these in staging:

- login works
- callback works
- session persists
- logout works
- social buttons load
- Auth0 log stream can reach `https://staging.cogent.ai/api/webhooks/auth0`

#### Step 15.3.12 - Verify Signal Ingestion

After staging is live, validate the ingestion path:

- worker app is healthy
- contracts can be activated
- manual fetch works
- scheduler is running
- fetched signals appear in the database/UI

Recommended first contracts:

| Contract | Source type | Provider preset | Source URL |
|----------|-------------|-----------------|------------|
| NGX Pulse Market | `api` | `NGX Pulse Market` | `https://ngxpulse.ng/api/ngxdata/market` |
| NGX Pulse Stocks | `api` | `NGX Pulse Stocks` | `https://ngxpulse.ng/api/ngxdata/stocks` |
| News search | `api` | `NewsAPI` | `https://newsapi.org/v2/everything` |
| X search | `social` | `X` | `https://api.twitter.com/2/tweets/search/recent` |
| LinkedIn public page | `scraper` | `LinkedIn public page` | public LinkedIn page URL |

#### Step 15.3.13 - Verify External Integrations

Before calling staging complete, verify:

- Sentry receives an event
- PostHog receives an event
- Better Stack / Logtail receives logs
- Resend sends a test email
- SerpApi search succeeds
- NewsAPI contract fetch succeeds
- NGX Pulse contract fetch succeeds
- X contract fetch succeeds
- LinkedIn public scraper contract fetch succeeds
- Azure Blob access succeeds for background storage paths

### 15.4 - What To Do If A Step Fails

| Failure | Most likely cause | First check |
|--------|-------------------|-------------|
| `MANIFEST_UNKNOWN` | image tag missing in ACR | `az acr repository show-tags` |
| frontend missing | frontend image missing or workload deploy failed | `az containerapp list --resource-group cogent-staging -o table` |
| Key Vault missing secrets | seeding not completed or wrong env variable names | rerun `seed-keyvault.ps1` after setting env vars |
| app cannot pull image | tag missing or registry pull identity problem | verify ACR tags first |
| migration job fails | image, DB connection, or runtime startup error | `az containerapp job execution list` |
| login/auth webhook fails | Auth0 config mismatch | frontend webhook route + Auth0 settings |
| no signals appear | worker down, contract inactive, or fetch failure | worker health + contract activation + fetch endpoint |

### 15.5 - Your Next Single Action

From the current point reached in staging, the next action is:

1. verify which ACR tags already exist
2. build any missing backend, worker, or frontend image
3. run the workload deployment

---

## 16. Detailed Execution Playbook

This section is the **follow-it-yourself** version of the deployment guide. It is written for a junior engineer and is intentionally explicit about:

- what stage you are in
- what to click
- what to paste into the terminal
- what “good” looks like
- what to do if a step fails
- where you can choose custom domain settings such as `stem-cogent.com`

The sequence below is the recommended execution order from **right now** through staging completion and production launch.

### 16.1 - Understand the Overall Execution Order

Do the work in this exact order:

1. verify Azure login and subscription
2. verify base staging infrastructure
3. verify Key Vault secrets
4. verify or build ACR images
5. deploy staging workloads
6. verify staging apps
7. configure or switch DNS/custom domains
8. verify staging with real integrations
9. choose production domain pattern
10. deploy production
11. verify production
12. open the product to users

Do **not** skip ahead to DNS, users, or production until the previous stage is green.

### 16.2 - Stage 1: Verify Azure Login and Subscription

Purpose:

- make sure Azure CLI is pointing at the correct subscription before you run anything else

#### Portal check

1. Open `https://portal.azure.com`
2. Confirm you are signed into the account that owns `cogent-staging`
3. Open `Subscriptions`
4. Confirm subscription `605bbfa4-451d-4a87-81d0-5051f7a773b7` is visible and enabled

#### Terminal check

Paste and run:

```powershell
az account show --output table
az account list --output table
az account set --subscription 605bbfa4-451d-4a87-81d0-5051f7a773b7
az account show --output table
```

Good result:

- subscription is `605bbfa4-451d-4a87-81d0-5051f7a773b7`
- tenant is your Default Directory
- state is `Enabled`

If this fails:

- run `az logout`
- run `az login`
- rerun the commands above

### 16.3 - Stage 2: Verify Base Staging Infrastructure

Purpose:

- confirm the platform foundation is already there before touching app workloads

#### Portal clicks

1. Open `Resource groups`
2. Click `cogent-staging`
3. Confirm the following resources exist:
   - `cogentacrstg`
   - `cogent-stg-kv`
   - `cogent-stg-postgres`
   - `cogent-stg-redis`
   - `cogent-stg-logs`
   - `cogent-stg-env`

#### Terminal check

Paste and run:

```powershell
az deployment group show --name staging-infra --resource-group cogent-staging --query properties.provisioningState -o tsv
az resource list --resource-group cogent-staging --output table
```

Good result:

- deployment state is `Succeeded`
- all base resources are listed

If base infra is missing:

- rerun the base deploy:

```powershell
az --% deployment group create --name staging-infra --resource-group cogent-staging --template-file infrastructure/main.bicep --parameters infrastructure/parameters/staging.bicepparam --parameters dbAdminPassword=$DB_PASS keyVaultOperatorObjectId=d3b1d22c-0060-488a-ac8e-fa0958733078 deployWorkloads=false
```

### 16.4 - Stage 3: Verify Key Vault Secrets

Purpose:

- ensure the app will have all runtime config before workloads start

#### Portal clicks

1. Open `Key vaults`
2. Click `cogent-stg-kv`
3. Open `Objects > Secrets`
4. Confirm the required names exist

#### Terminal check

Paste and run:

```powershell
az keyvault secret list --vault-name cogent-stg-kv --output table
```

Required secrets:

- `database-url`
- `redis-url`
- `secret-key`
- `auth0-domain`
- `auth0-audience`
- `auth0-m2m-client-id`
- `auth0-m2m-client-secret`
- `auth0-webhook-secret`
- `auth0-frontend-secret`
- `auth0-issuer-base-url`
- `auth0-client-id`
- `auth0-client-secret`
- `openai-api-key`
- `sentry-dsn`
- `logtail-token`
- `posthog-api-key`
- `posthog-host`
- `resend-api-key`
- `resend-from-email`
- `serpapi-api-key`
- `newsapi-api-key`
- `ngx-market-data-api-key`
- `ngx-market-data-base-url`
- `x-bearer-token`
- `azure-blob-connection-string`
- `azure-blob-model-container`

If secrets are missing:

1. set the missing `$env:...` variables in PowerShell
2. run:

```powershell
.\scripts\seed-keyvault.ps1 -VaultName cogent-stg-kv
```

3. rerun the `az keyvault secret list` command

### 16.5 - Stage 4: Verify Blob Storage

Purpose:

- confirm background jobs and model/artifact storage can use Azure Blob

#### Portal clicks

1. Open `Storage accounts`
2. Click your staging storage account, for example `cogentstgstorage`
3. Open `Data storage > Containers`
4. Confirm container `ml-models` exists
5. Open `Security + networking > Access keys`
6. Confirm the connection string you seeded came from here

Good result:

- container exists
- connection string is valid
- Key Vault has `azure-blob-connection-string` and `azure-blob-model-container`

If you need to create storage manually:

1. `Create > Storage account`
2. Resource group: `cogent-staging`
3. Region: `UK South`
4. Performance: `Standard`
5. Redundancy: `LRS`
6. Finish creation
7. Create container `ml-models`

### 16.6 - Stage 5: Check ACR Images Before Building

Purpose:

- avoid rebuilding images that already exist
- identify which images are still missing

Paste and run:

```powershell
az acr repository show-tags --name cogentacrstg --repository cogent-backend -o table
az acr repository show-tags --name cogentacrstg --repository cogent-worker -o table
az acr repository show-tags --name cogentacrstg --repository cogent-frontend -o table
```

Interpretation:

- if `latest` exists, that image is ready
- if the repository is missing or empty, build that image

Common error:

- `repository not found`
  - means no image has been pushed yet

### 16.7 - Stage 6: Build and Push Missing Images

Purpose:

- publish the exact image tags that the staging deployment expects

#### Backend

Run from the repository root:

```powershell
az acr build --registry cogentacrstg --image cogent-backend:latest --file Dockerfile .
```

What you will see:

- source archive packaging
- Docker build logs
- push to ACR

Good result:

- build ends with success
- `latest` appears under `cogent-backend`

#### Worker

```powershell
az acr build --registry cogentacrstg --image cogent-worker:latest --file Dockerfile.worker .
```

Good result:

- build ends with success
- `latest` appears under `cogent-worker`

#### Frontend

```powershell
az acr build --registry cogentacrstg --image cogent-frontend:latest --file frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=https://cogent-stg-backend.purpleglacier-069239e0.uksouth.azurecontainerapps.io ./frontend
```

Good result:

- build ends with success
- `latest` appears under `cogent-frontend`

If your network cuts out:

- rerun the same `az acr build` command
- or first recheck the tag with `az acr repository show-tags`

If the build fails:

- read the last 20-50 lines of the build log
- common causes:
  - missing file in Docker build context
  - frontend build error
  - Python dependency install failure

### 16.8 - Stage 7: Verify the Images Exist

After all builds, rerun:

```powershell
az acr repository show-tags --name cogentacrstg --repository cogent-backend -o table
az acr repository show-tags --name cogentacrstg --repository cogent-worker -o table
az acr repository show-tags --name cogentacrstg --repository cogent-frontend -o table
```

You should see `latest` for all three.

Do not continue until all three exist.

### 16.9 - Stage 8: Deploy Staging Workloads

Purpose:

- create or update the live staging backend, worker, frontend, and migration job

Paste and run:

```powershell
az --% deployment group create --name staging-infra-apps --resource-group cogent-staging --template-file infrastructure/main.bicep --parameters infrastructure/parameters/staging.bicepparam --parameters dbAdminPassword=$DB_PASS keyVaultOperatorObjectId=d3b1d22c-0060-488a-ac8e-fa0958733078 deployWorkloads=true
```

This depends on:

- images existing in ACR
- Key Vault secrets already present

If it fails:

- `MANIFEST_UNKNOWN`
  - image tag missing
- `unable to pull image`
  - check ACR tags and identity pull configuration
- secret-related errors
  - confirm the Key Vault secrets list again

### 16.10 - Stage 9: Verify the Staging Apps

Purpose:

- confirm Azure actually created the live services

Paste and run:

```powershell
az containerapp list --resource-group cogent-staging --output table
az containerapp show --name cogent-stg-backend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name cogent-stg-frontend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp job show --name cogent-stg-migrate --resource-group cogent-staging -o json
```

Good result:

- backend exists
- worker exists
- frontend exists
- migration job exists

If frontend is missing:

- frontend image was likely missing
- or the workload deployment failed partway through

### 16.11 - Stage 10: Run or Verify Migrations

Purpose:

- make sure the database schema is up to date before using the app

To start the job manually:

```powershell
az containerapp job start --name cogent-stg-migrate --resource-group cogent-staging
```

To inspect executions:

```powershell
az containerapp job execution list --name cogent-stg-migrate --resource-group cogent-staging -o table
```

Good result:

- latest execution ends successfully

### 16.12 - Stage 11: Health and Frontend Smoke Checks

#### Backend

Use the custom domain if already configured:

```powershell
curl https://api-staging.cogent.ai/health
```

If custom DNS is not ready yet, use the direct Container Apps FQDN:

```powershell
curl https://<backend-fqdn>/health
```

Expected:

- HTTP `200`

#### Frontend

Open in browser:

- `https://staging.cogent.ai`

Or, if DNS is not ready yet:

- the direct frontend Container Apps FQDN

Expected:

- page loads
- login page or dashboard shell appears

### 16.13 - Stage 12: Auth0 Verification

Purpose:

- confirm sign-in and callback paths work before involving users

Do this manually:

1. open staging frontend
2. click login
3. complete login
4. confirm callback succeeds
5. refresh the page
6. confirm session persists
7. logout
8. confirm logout works

Check the log stream configuration in Auth0:

1. open Auth0 Dashboard
2. `Monitoring > Streams`
3. open the custom webhook stream
4. verify staging URL is correct
5. verify the authorization token matches `AUTH0_WEBHOOK_SECRET`

### 16.14 - Stage 13: Signal Ingestion Verification

Purpose:

- prove the product’s main data pipeline is actually working

Do this:

1. verify worker is up
2. create or activate one contract for each critical path
3. trigger a manual fetch
4. confirm signals appear

Recommended first contracts:

| Contract | Source type | Provider preset | Source URL |
|----------|-------------|-----------------|------------|
| NGX Pulse Market | `api` | `NGX Pulse Market` | `https://ngxpulse.ng/api/ngxdata/market` |
| NGX Pulse Stocks | `api` | `NGX Pulse Stocks` | `https://ngxpulse.ng/api/ngxdata/stocks` |
| News search | `api` | `NewsAPI` | `https://newsapi.org/v2/everything` |
| X search | `social` | `X` | `https://api.twitter.com/2/tweets/search/recent` |
| LinkedIn public page | `scraper` | `LinkedIn public page` | public LinkedIn company/profile URL |

What to verify:

- contract activates successfully
- manual fetch succeeds
- `last_fetched_at` updates
- signals appear in the app

### 16.15 - Stage 14: Choose Your Domain Strategy

This is the stage where you decide whether to use the default Cogent domains or a custom domain like `stem-cogent.com`.

You should make this decision **after workloads are healthy**, not before.

#### Option A - Keep existing Cogent domains

Use:

- staging frontend: `staging.cogent.ai`
- staging backend: `api-staging.cogent.ai`
- production frontend: `app.cogent.ai`
- production backend: `api.cogent.ai`

#### Option B - Use a custom root domain like `stem-cogent.com`

Recommended mapping:

| Purpose | Suggested domain |
|--------|-------------------|
| Staging frontend | `staging.stem-cogent.com` |
| Staging backend | `api-staging.stem-cogent.com` |
| Production frontend | `app.stem-cogent.com` or `stem-cogent.com` |
| Production backend | `api.stem-cogent.com` |

This is the point where you decide:

- whether the public app should live at `app.stem-cogent.com`
- or whether the public app should use the bare root `stem-cogent.com`

#### If you want the bare root domain

Use:

- frontend: `stem-cogent.com`
- backend: `api.stem-cogent.com`

This is a valid production pattern, but it requires:

- DNS root record support from your DNS provider
- correct apex-domain mapping strategy

For a simpler rollout, `app.stem-cogent.com` is usually easier.

### 16.16 - Stage 15: Configure Custom Domains and DNS

Do this only after staging workloads are healthy.

#### Step 16.16.1 - Get current Container Apps FQDNs

```powershell
az containerapp show --name cogent-stg-backend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
az containerapp show --name cogent-stg-frontend --resource-group cogent-staging --query properties.configuration.ingress.fqdn -o tsv
```

#### Step 16.16.2 - Create DNS records

At your domain provider:

1. open DNS management
2. create the records you need

Examples for `stem-cogent.com`:

| Record type | Name | Value |
|------------|------|-------|
| CNAME | `staging` | staging frontend ACA FQDN |
| CNAME | `api-staging` | staging backend ACA FQDN |
| CNAME | `app` | production frontend ACA FQDN |
| CNAME | `api` | production backend ACA FQDN |

If using the root domain for production frontend, your provider may require:

- ALIAS
- ANAME
- flattened CNAME

#### Step 16.16.3 - Bind the hostname in Azure

Example:

```powershell
az containerapp hostname add --name cogent-stg-backend --resource-group cogent-staging --hostname api-staging.stem-cogent.com
az containerapp hostname add --name cogent-stg-frontend --resource-group cogent-staging --hostname staging.stem-cogent.com
```

Repeat for production later.

### 16.17 - Stage 16: Update Auth0 For Your Final Domain Choice

If you change the public domain, you must update Auth0.

For example, if staging uses:

- `https://staging.stem-cogent.com`

and production uses:

- `https://app.stem-cogent.com`

then update:

1. Allowed Callback URLs
2. Allowed Logout URLs
3. Allowed Web Origins
4. Initiate Login URI
5. Auth0 log stream webhook URL

Do not forget this step. A domain change without Auth0 update will break login.

### 16.18 - Stage 17: Staging Signoff

You are ready to leave staging only when all of these are green:

- [ ] backend health `200`
- [ ] frontend loads
- [ ] login works
- [ ] logout works
- [ ] migrations succeeded
- [ ] signal ingestion works
- [ ] external integrations work
- [ ] logs and telemetry are flowing
- [ ] staging domain is correct

### 16.19 - Stage 18: Production Execution Order

Only after staging signoff:

1. create or verify `cogent-production`
2. deploy production base infra
3. seed production Key Vault
4. build/push production images
5. deploy production workloads
6. bind production custom domains
7. update Auth0 production URLs
8. run production smoke tests
9. verify billing, email, analytics, logs, and signals
10. open the app to users

### 16.20 - Stage 19: Production Go-Live Checklist

Before sending users to production:

- [ ] production frontend URL is live
- [ ] production backend health returns `200`
- [ ] production login works
- [ ] production log stream works
- [ ] provider-backed signal fetch works
- [ ] emails work
- [ ] logs and analytics work
- [ ] billing or plan flow is verified
- [ ] first-day monitoring is ready

### 16.21 - Stage 20: First Production User Launch

When everything is green:

1. announce the live URL
2. keep logs open
3. monitor signups, logins, and errors
4. verify at least one real user journey
5. stay in high-watch mode for 24-72 hours

---

## Quick Reference: Setup Order

```text
 1. Install prerequisites
 2. Configure GitHub repo and environments
 3. Create Azure resource groups
 4. Create Azure AD OIDC app registration
 5. Deploy Bicep infrastructure
 6. Verify Azure PostgreSQL Flexible Server and Key Vault `database-url`
 7. Configure Auth0 applications, connections, API, actions, and log stream
 8. Configure required external services (OpenAI, Sentry, PostHog, Better Stack, Resend, SerpApi, NewsAPI, NGX Market Data API, X API, Azure Blob)
 9. Seed Key Vault secrets
10. Configure GitHub secrets and variables
11. Configure DNS and custom domains
12. Run the fresh-clone source-control gate
13. Deploy staging
14. Verify staging, including tenant isolation and Auth0 session behavior
15. Pass the production promotion gate
16. Create the production release
17. Verify production and open `https://app.cogent.ai` to users
```

---

*Generated for the Cogent Intelligence Platform - March 2026*
