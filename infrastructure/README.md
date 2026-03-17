# Cogent — Infrastructure

This directory contains Infrastructure-as-Code (IaC) for deploying Cogent to Azure.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps Environment                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Backend     │  │   Worker     │  │   Frontend   │              │
│  │  (FastAPI)    │  │  (RQ)        │  │  (Next.js)   │              │
│  │  Port 8000    │  │  Port 8001   │  │  Port 3000   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘              │
│         │                  │                                         │
│  ┌──────┴──────────────────┴────────┐                               │
│  │  Azure Cache for Redis           │                               │
│  │  (Job queue + cache + pub/sub)   │                               │
│  └──────────────────────────────────┘                               │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │  Azure Key Vault     │  │  Log Analytics       │                │
│  │  (Secret injection)  │  │  (Container logs)    │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                      │
│  ┌──────────────────────────────────────────┤                │
│  │  Azure Database for PostgreSQL   │                │
│  │  Flexible Server + pgvector      │                │
│  └──────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────┘
         │
         │  Auth0 (external)
         │  OpenAI API (external)
         │  Sentry (external)
```

## Directory Structure

```
infrastructure/
├── main.bicep                          # Root template — orchestrates all modules
├── modules/
│   ├── container-app.bicep             # Generic Container App + health probes
│   ├── container-registry.bicep        # Azure Container Registry
│   ├── keyvault.bicep                  # Azure Key Vault
│   ├── postgres.bicep                  # Azure PostgreSQL Flexible Server
│   └── redis.bicep                     # Azure Cache for Redis
└── parameters/
    ├── staging.bicepparam              # Staging environment parameters
    └── production.bicepparam           # Production environment parameters
```

## Prerequisites

1. **Azure CLI** ≥ 2.60 with Bicep support
2. **Resource groups** created:
   - `cogent-staging`
   - `cogent-production`
3. **Azure PostgreSQL Flexible Server** provisioned via the Bicep template (see Deployment)
4. **Auth0 tenant** configured for each environment

## Deployment

### First-time setup

```bash
# 1. Create resource groups
az group create --name cogent-staging    --location uksouth
az group create --name cogent-production --location uksouth

# 2. Deploy infrastructure (staging)
az deployment group create \
  --resource-group cogent-staging \
  --template-file infrastructure/main.bicep \
  --parameters infrastructure/parameters/staging.bicepparam

# 3. Seed secrets into Key Vault (DATABASE_URL is auto-set by Bicep — use this for others)
VAULT_NAME=cogent-stg-kv \
REDIS_URL="rediss://..." \
SECRET_KEY="$(openssl rand -hex 32)" \
AUTH0_DOMAIN="staging.auth0.com" \
  ./scripts/seed-keyvault.sh

# 4. Push initial images
az acr login --name cogentacrstg
docker build -t cogentacrstg.azurecr.io/cogent-backend:initial .
docker push cogentacrstg.azurecr.io/cogent-backend:initial
# (repeat for worker and frontend)
```

### Ongoing deployments

Handled automatically by `.github/workflows/deploy.yml`:

- **Push to `main`** → builds + deploys to **staging**
- **GitHub Release** → builds + deploys to **production**

### Database migrations

```bash
# Run migrations against staging
DATABASE_URL="postgresql+asyncpg://..." ./scripts/migrate.sh upgrade head

# Roll back one migration
DATABASE_URL="postgresql+asyncpg://..." ./scripts/migrate.sh downgrade -1

# Check current revision
DATABASE_URL="postgresql+asyncpg://..." ./scripts/migrate.sh current
```

### Backup verification

```bash
AZURE_RESOURCE_GROUP=cogent-production \
AZURE_POSTGRES_SERVER=cogent-prod-postgres \
DB_ADMIN_USER=cogentadmin \
DB_ADMIN_PASSWORD=$DB_PASS \
DB_NAME=cogent \
  ./scripts/verify-backup.sh
```

## Environments

| Aspect | Staging | Production |
|--------|---------|------------|
| **Backend replicas** | 1–2 | 2–10 (autoscaled) |
| **Worker replicas** | 1 | 2 |
| **Redis SKU** | Basic C0 | Standard C2 |
| **ACR SKU** | Basic | Standard |
| **Log retention** | 30 days | 90 days |
| **Zone redundancy** | No | Yes |
| **Database** | Azure PostgreSQL Flexible Server (Burstable B2ms) | Azure PostgreSQL Flexible Server (GeneralPurpose D4s_v3) |
| **Domain** | staging.cogent.ai | app.cogent.ai |

## Secret Rotation

All secrets are stored in Azure Key Vault and referenced by Container Apps via managed identity. To rotate a secret:

```bash
# Update the secret in Key Vault
az keyvault secret set \
  --vault-name cogent-stg-kv \
  --name secret-key \
  --value "$(openssl rand -hex 32)"

# Restart the Container App to pick up the new value
az containerapp revision restart \
  --name cogent-stg-backend \
  --resource-group cogent-staging
```
