# Phase 2: Azure Pre-Prod Deployment Guide

**Status:** Infrastructure Validation Phase
**Environment:** PRE-PROD (No real users)
**Monthly Cost:** ~$20

---

## Overview

This guide covers deploying and operating the Cogent application in Azure Pre-Prod environment.

**What you have:**
- FastAPI backend containerized
- Background worker for job processing
- Automated CI/CD via GitHub Actions
- Azure Container Apps (serverless containers)
- Managed Redis, PostgreSQL, and secrets

---

## Prerequisites

### Local Tools
- Azure CLI (`az`) - [Install](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- Docker (for local testing)
- Git
- Bash shell (WSL, Git Bash, or native)

### Azure Resources
- Active Azure subscription
- Billing enabled
- Sufficient quota for Container Apps

### Credentials
- Auth0 tenant configured
- Neon PostgreSQL database URL
- GitHub repository with Actions enabled

---

## Initial Setup (Do Once)

### 1. Provision Azure Infrastructure

Run the setup script:

```bash
cd scripts
chmod +x setup-azure-preprod.sh
./setup-azure-preprod.sh
```

**What this creates:**
- Resource Group: `cogent-preprod-rg`
- Container Registry: `cogentregistry.azurecr.io`
- Redis Cache: `cogent-redis.redis.cache.windows.net`
- Key Vault: `cogent-kv-<timestamp>.vault.azure.net`
- Container Apps Environment: `cogent-preprod-env`

**Time:** ~10 minutes (Redis takes longest)

### 2. Store Secrets in Key Vault

After infrastructure is created, add your secrets:

```bash
KEYVAULT_NAME="cogent-kv-<your-timestamp>"  # From setup output

# Database
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name database-url \
  --value "postgresql+asyncpg://user:pass@host/db?ssl=require"

# Auth0
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name auth0-m2m-client-secret \
  --value "your-auth0-secret"

# Application
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name secret-key \
  --value "$(openssl rand -hex 32)"

# Redis (auto-populated by setup script)
# Already set if you ran setup-azure-preprod.sh
```

### 3. Configure GitHub Secrets

Follow: [`scripts/setup-github-secrets.md`](../scripts/setup-github-secrets.md)

**Required secrets:**
- `AZURE_CREDENTIALS` (Service Principal JSON)
- `AZURE_REGISTRY_NAME` = `cogentregistry`
- `AZURE_RESOURCE_GROUP` = `cogent-preprod-rg`
- `KEYVAULT_NAME` = `cogent-kv-<timestamp>`
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AUTH0_M2M_CLIENT_ID`

### 4. Deploy Containers

**Option A: Via GitHub Actions (Recommended)**

```bash
# Commit and push to main branch
git add .
git commit -m "Deploy to pre-prod"
git push origin main

# Or trigger manually
gh workflow run deploy-preprod.yml
```

**Option B: Manual Deploy**

```bash
cd scripts
chmod +x deploy-preprod.sh
./deploy-preprod.sh
```

**Time:** ~5 minutes (first deploy), ~2 minutes (updates)

---

## Daily Operations

### Check Deployment Status

```bash
# List all container apps
az containerapp list \
  --resource-group cogent-preprod-rg \
  --output table

# Get API URL
az containerapp show \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --query properties.configuration.ingress.fqdn -o tsv
```

### View Logs

```bash
# API logs (live tail)
az containerapp logs show \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --follow

# Worker logs
az containerapp logs show \
  --name cogent-worker \
  --resource-group cogent-preprod-rg \
  --follow

# Recent errors only
az containerapp logs show \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --type console \
  | grep -i error
```

### Run Smoke Tests

```bash
# Set API URL
export PREPROD_API_URL="https://cogent-api.azurecontainerapps.io"

# Optional: Add test token for authenticated tests
export AUTH0_TEST_TOKEN="your-test-token"

# Run E2E tests
pytest backend/tests/ -v -m "e2e"
```

### Scale Containers

```bash
# Scale API to handle more load
az containerapp update \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --min-replicas 1 \
  --max-replicas 5

# Scale down to save costs
az containerapp update \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --min-replicas 0 \
  --max-replicas 2
```

### Update Environment Variables

```bash
# Add new env var
az containerapp update \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --set-env-vars NEW_VAR=value

# Update existing secret
az keyvault secret set \
  --vault-name $KEYVAULT_NAME \
  --name database-url \
  --value "new-value"

# Restart to pick up changes
az containerapp revision restart \
  --name cogent-api \
  --resource-group cogent-preprod-rg
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check revision status
az containerapp revision list \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --output table

# View startup logs
az containerapp logs show \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --tail 100
```

**Common issues:**
- Missing secrets in Key Vault
- Invalid database URL format
- Port mismatch (should be 8000)
- Image pull failure (check registry credentials)

### Database Connection Failed

```bash
# Test database connectivity from local machine
psql "postgresql+asyncpg://user:pass@host/db?ssl=require"

# Check if IP is whitelisted in Neon (if using IP restrictions)
# Neon allows all IPs by default
```

### Redis Connection Failed

```bash
# Get Redis connection string
az redis show \
  --name cogent-redis \
  --resource-group cogent-preprod-rg \
  --query hostName -o tsv

# Check if Redis is running
az redis show \
  --name cogent-redis \
  --resource-group cogent-preprod-rg \
  --query provisioningState -o tsv
```

### High Costs

```bash
# Check resource costs
az consumption usage list \
  --resource-group cogent-preprod-rg

# Scale down to zero replicas when not in use
az containerapp update \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --min-replicas 0 \
  --max-replicas 0
```

---

## Promoting to Production (Phase 3)

When ready for real users:

### 1. Create Production Infrastructure

```bash
# Copy and modify setup script
cp scripts/setup-azure-preprod.sh scripts/setup-azure-prod.sh

# Change resource names:
# - cogent-preprod-rg → cogent-prod-rg
# - Redis: Basic → Standard C1
# - Scale: min-replicas 1 → 2

./scripts/setup-azure-prod.sh
```

### 2. Configure Production Secrets

```bash
# Use separate Key Vault for production
PROD_KEYVAULT="cogent-prod-kv-$(date +%s)"

# Add production secrets
az keyvault secret set \
  --vault-name $PROD_KEYVAULT \
  --name database-url \
  --value "production-database-url"
```

### 3. Update GitHub Actions

Create `.github/workflows/deploy-prod.yml` (copy from preprod workflow)

**Key changes:**
- Trigger: Only on git tags (`v*`)
- Environment: `ENVIRONMENT=production`
- Resource group: `cogent-prod-rg`
- Add manual approval step

### 4. Deploy to Production

```bash
# Create release tag
git tag -a v1.0.0 -m "Production release 1.0.0"
git push origin v1.0.0

# Workflow triggers automatically
# Approve in GitHub Actions UI
```

### 5. Configure Custom Domain

```bash
# Add custom domain to Container App
az containerapp hostname add \
  --name cogent-api \
  --resource-group cogent-prod-rg \
  --hostname api.yourdomain.com

# Get validation TXT record and add to DNS
```

---

## Cost Optimization

### During Development
- Scale to 0 replicas when not in use
- Use free tiers (Redis C0, Key Vault free ops)
- Delete pre-prod on weekends if not testing

### Before Launch
- Keep pre-prod minimal (0-1 replicas)
- Use Azure Cost Alerts
- Review Container Apps metrics monthly

### Post-Launch (Phase 4)
- Enable auto-scale based on metrics
- Use Azure Reserved Instances (if steady traffic)
- Move to Standard Redis only if needed

---

## Monitoring (Phase 4 - NOT NOW)

**Currently implemented:**
- Azure Container Apps built-in metrics
- Console logs via `az containerapp logs`
- Prometheus metrics exposed (not scraped yet)

**Add later (when you have users):**
- Sentry for error tracking
- Application Insights
- Grafana dashboards
- Uptime monitoring (UptimeRobot, Better Uptime)

---

## Rollback Procedure

If a deployment breaks production:

```bash
# List revisions
az containerapp revision list \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --output table

# Rollback to previous revision
az containerapp revision activate \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --revision cogent-api--<previous-revision>

# Or deploy specific image tag
az containerapp update \
  --name cogent-api \
  --resource-group cogent-preprod-rg \
  --image cogentregistry.azurecr.io/api:<previous-sha>
```

---

## Security Checklist

**✅ Currently implemented:**
- Secrets in Key Vault (not hardcoded)
- Non-root container user
- HTTPS only (Container Apps default)
- Auth0 JWT validation
- CORS configured

**⏸️ Add in Phase 4:**
- Azure Front Door (WAF, DDoS protection)
- Network isolation (VNET integration)
- Container scanning (Trivy, Snyk)
- Rotate secrets quarterly

---

## Support & Escalation

**Self-service:**
1. Check logs: `az containerapp logs`
2. Run E2E tests: `pytest backend/tests/ -v -m "e2e"`
3. Review recent commits: `git log --oneline -10`

**Need help:**
- Azure Support: Portal → Support → New Request
- Auth0 Support: Dashboard → Support
- Neon Support: Console → Support

**Break glass:**
```bash
# Emergency: Tear down pre-prod
az group delete --name cogent-preprod-rg --yes --no-wait

# Cost: $0 after deletion
# Rebuild time: 1 hour (run setup scripts again)
```

---

## What's Next?

**Current Phase:** PHASE 2 ✅
**Next Phase:** PHASE 3 (Product & Features)

Before moving to Phase 3:
- [ ] Pre-prod environment is stable for 1 week
- [ ] All smoke tests pass consistently
- [ ] Costs are under $30/month
- [ ] Team understands rollback procedure
- [ ] Production promotion path is documented

**Don't do yet:**
- ❌ Custom domain
- ❌ Production deployment
- ❌ Monitoring dashboards
- ❌ Performance optimization
- ❌ Load testing

---

## Quick Reference

```bash
# Deploy
git push origin main

# Check status
az containerapp show --name cogent-api -g cogent-preprod-rg --query properties.runningStatus

# View logs
az containerapp logs show --name cogent-api -g cogent-preprod-rg --follow

# Test
curl https://cogent-api.azurecontainerapps.io/health

# Rollback
az containerapp revision activate --name cogent-api -g cogent-preprod-rg --revision <prev>

# Tear down
az group delete --name cogent-preprod-rg --yes
```
