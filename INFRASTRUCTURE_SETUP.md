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
| ACR SKU | Basic |
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

### 7.2 OpenAI

Create an API key and set:
- `OPENAI_API_KEY`

Current model usage in code:
- `gpt-4o`
- `gpt-4o-mini`
- `text-embedding-3-small`

### 7.3 Sentry

Create a DSN and set:
- `SENTRY_DSN`

### 7.4 PostHog

| Setting | Value |
|---------|-------|
| Project API key | `POSTHOG_API_KEY` |
| Host / ingestion URL | `POSTHOG_HOST` |
| Runtime | backend |

### 7.5 Better Stack / Logtail

| Setting | Value |
|---------|-------|
| Source token | `LOGTAIL_TOKEN` |
| Runtime | backend |

### 7.6 Resend

| Setting | Value |
|---------|-------|
| API key | `RESEND_API_KEY` |
| Verified sender | `RESEND_FROM_EMAIL` |
| Runtime | backend, worker |

### 7.7 SerpApi

| Setting | Value |
|---------|-------|
| API key | `SERPAPI_API_KEY` |
| Runtime | backend, worker |

### 7.8 NewsAPI

| Setting | Value |
|---------|-------|
| API key | `NEWSAPI_API_KEY` |
| Runtime | backend, worker |
| Contract source type | `api` |
| Contract provider preset | `newsapi` |

Notes:
- The Contract Studio now supports a `NewsAPI` preset under `Source type = api`.
- The backend injects the runtime API key automatically; you do not store it per contract.

### 7.9 NGX Pulse API

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

### 7.10 X API

| Setting | Value |
|---------|-------|
| Bearer token | `X_BEARER_TOKEN` |
| Runtime | backend, worker |
| Contract source type | `social` |
| Contract provider preset | `x` |

Notes:
- The Contract Studio now supports an `X` preset under `Source type = social`.
- The backend injects the runtime bearer token automatically; you do not store it per contract.

### 7.11 LinkedIn Public Scraper

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

### 7.12 Azure Blob Storage

Provision a Storage Account and Blob container for model / artifact persistence.

| Setting | Value |
|---------|-------|
| Connection string | `AZURE_BLOB_CONNECTION_STRING` |
| Container name | `AZURE_BLOB_MODEL_CONTAINER` |
| Suggested container | `ml-models` |
| Runtime | backend, worker |

### 7.13 Reserved Runtime Settings

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

### 13.1 - Rollback

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

### 13.2 - Ongoing Operations

| Task | Frequency | How |
|------|-----------|-----|
| Check error rates | Daily | Sentry |
| Review uptime | Daily | uptime monitor |
| Check PostgreSQL metrics | Weekly | Azure Portal -> PostgreSQL Flexible Server |
| Review Redis memory | Weekly | Azure Portal -> Redis |
| Run load tests | Before major releases | `scripts/load_test.py` |
| Rotate secrets | Quarterly | reseed Key Vault |
| Review logs | Weekly | Log Analytics / Better Stack |

### 13.3 - Useful Commands

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
