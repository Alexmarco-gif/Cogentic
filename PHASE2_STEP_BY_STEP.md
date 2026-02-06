# Phase 2 Deployment - Step by Step Guide

**Current Status:** Azure infrastructure created, secrets added, git initialized
**Goal:** Deploy to Azure Pre-Prod via GitHub Actions
**Time:** ~30 minutes

---

## Prerequisites Completed ✅

- ✅ Docker installed
- ✅ Azure CLI installed and logged in
- ✅ Azure infrastructure provisioned (cogent-preprod-rg)
- ✅ Secrets added to Key Vault (cogent-kv-20260202031440)
- ✅ Git repository initialized locally

---

## Step 1: Fix Git Remote and Push to GitHub

### 1.1 Verify Current State
```powershell
cd "C:\Users\Alex Marco\Documents\Cogent"
git status
git remote -v
```

**Expected:** Should show you're on `dev` branch with remote pointing to Cogentic.git

### 1.2 Push Remaining Branches
```powershell
# Push staging branch
git push origin staging

# Push production branch
git push origin production
```

**Result:** All 3 branches now on GitHub (dev, staging, production)

---

## Step 2: Create Azure Service Principal for GitHub Actions

### 2.1 Get Your Subscription ID
```powershell
az account show --query id --output tsv
```
**Copy this ID** - you'll need it in the next step.

### 2.2 Create Service Principal
```powershell
# Get subscription ID
$subId = az account show --query id --output tsv

# Create service principal (single line - no backticks)
az ad sp create-for-rbac --name "github-actions-cogent" --role contributor --scopes "/subscriptions/$subId/resourceGroups/cogent-preprod-rg" --sdk-auth
```

**Note:** If you see "already exists" error, delete it first:
```powershell
az ad sp delete --id github-actions-cogent
# Then run the create command again
```

**Important:** Copy the ENTIRE JSON output that looks like this:
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx",
  ...
}
```

---

## Step 3: Add GitHub Secrets

### 3.1 Open GitHub Repository Settings
1. Go to: https://github.com/Alexmarco-gif/Cogentic
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### 3.2 Add Required Secrets (One by One)

**Secret 1: AZURE_CREDENTIALS**
- Name: `AZURE_CREDENTIALS`
- Value: Paste the entire JSON from Step 2.2
- Click **Add secret**

**Secret 2: AZURE_REGISTRY_NAME**
- Name: `AZURE_REGISTRY_NAME`
- Value: `cogentregistry`
- Click **Add secret**

**Secret 3: AZURE_RESOURCE_GROUP**
- Name: `AZURE_RESOURCE_GROUP`
- Value: `cogent-preprod-rg`
- Click **Add secret**

**Secret 4: KEYVAULT_NAME**
- Name: `KEYVAULT_NAME`
- Value: `cogent-kv-20260202031440`
- Click **Add secret**

**Secret 5: AUTH0_DOMAIN**
- Name: `AUTH0_DOMAIN`
- Value: `your-tenant.auth0.com` (from your .env file)
- Click **Add secret**

**Secret 6: AUTH0_AUDIENCE**
- Name: `AUTH0_AUDIENCE`
- Value: `https://api.cogent-ai.com`
- Click **Add secret**

**Secret 7: AUTH0_M2M_CLIENT_ID**
- Name: `AUTH0_M2M_CLIENT_ID`
- Value: `your-m2m-client-id` (from your .env file)
- Click **Add secret**

### 3.3 Verify All Secrets Added
You should see 7 secrets listed in GitHub Actions secrets.

---

## Step 4: Update Auth0 Secret in Key Vault (IMPORTANT)

The Auth0 secret currently has a placeholder value. Update it with your real secret:

```powershell
# Replace with the actual value from your .env file (without the < > brackets)
az keyvault secret set --vault-name cogent-kv-20260202031440 --name auth0-m2m-client-secret --value "pvXWluG7I_xUGyCUcU0krDiXyFGbVU6haqlGf2VvNcDRYsI736dHWqXt7UdXqZ_8"
```

**Already done if you've updated it!**

---

## Step 5: Update Redis URL in Key Vault (After Redis Provisions)

Check if Redis is ready:
```powershell
az redis show --name cogent-redis --resource-group cogent-preprod-rg --query "provisioningState" --output tsv
```

**If output is "Succeeded"**, update the Redis URL:

```powershell
# Get Redis key
$redisKey = az redis list-keys --resource-group cogent-preprod-rg --name cogent-redis --query primaryKey --output tsv

# Update Key Vault with real Redis URL
az keyvault secret set --vault-name cogent-kv-20260202031440 --name redis-url --value "rediss://:$redisKey@cogent-redis.redis.cache.windows.net:6380/0"
```

**If output is "Creating"**, wait 5-10 minutes and try again.

---

## Step 6: Trigger GitHub Actions Deployment

### 6.1 Make a Small Change
```powershell
# Make a test change to trigger deployment
echo "# Deployment Test" >> README.md
git add README.md
git commit -m "Trigger pre-prod deployment"
git push origin dev
```

### 6.2 Monitor Deployment
1. Go to: https://github.com/Alexmarco-gif/Cogentic/actions
2. You should see a workflow run "Deploy to Pre-Prod"
3. Click on it to watch the deployment progress
4. Wait ~10-15 minutes for first deployment

### 6.3 Check for Errors
If the workflow fails:
- Click on the failed step to see error details
- Common issues:
  - **Missing secret**: Add the missing GitHub secret
  - **Permission denied**: Check Service Principal permissions
  - **Key Vault not found**: Verify KEYVAULT_NAME secret is correct

---

## Step 7: Verify Deployment

### 7.1 Get API URL
```powershell
az containerapp show `
  --name cogent-api `
  --resource-group cogent-preprod-rg `
  --query properties.configuration.ingress.fqdn `
  --output tsv
```

**Copy this URL** - it's your pre-prod API endpoint.

### 7.2 Test Health Endpoint
```powershell
# Replace <API_URL> with the URL from above
curl https://<API_URL>/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### 7.3 Run Smoke Tests (Optional)
```powershell
# Set environment variable
$env:PREPROD_API_URL = "https://<API_URL>"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run E2E tests
pytest backend/tests/ -v -m "e2e"
```

---

## Step 8: View Logs

### 8.1 API Logs
```powershell
az containerapp logs show `
  --name cogent-api `
  --resource-group cogent-preprod-rg `
  --follow
```

Press `Ctrl+C` to stop.

### 8.2 Worker Logs
```powershell
az containerapp logs show `
  --name cogent-worker `
  --resource-group cogent-preprod-rg `
  --follow
```

---

## Troubleshooting

### Issue: Container App Not Found
**Solution:** First deployment creates the container apps. If GitHub Actions failed, check the error and fix it, then re-run the workflow.

### Issue: Database Connection Failed
**Solution:** Verify database URL in Key Vault:
```powershell
az keyvault secret show `
  --vault-name cogent-kv-20260202031440 `
  --name database-url `
  --query value `
  --output tsv
```

### Issue: Redis Connection Failed
**Solution:** Ensure Redis is provisioned and URL is updated in Key Vault (see Step 5).

### Issue: Auth0 Authentication Failed
**Solution:** Update Auth0 secret with real value (see Step 4).

### Issue: GitHub Actions Permission Denied
**Solution:** Recreate Service Principal with correct permissions:
```powershell
# Delete old one
az ad sp delete --id <APP_ID>

# Create new one (see Step 2.2)
```

---

## Branch Strategy Summary

```
dev        → Pre-prod environment (Azure Container Apps)
           → Auto-deploys on push to dev
           → URL: https://<your-app>.azurecontainerapps.io

staging    → Staging environment (Phase 3 - not configured yet)
           → Manual deploys only
           → Will create separate staging resources

production → Production environment (Phase 3 - not configured yet)
           → Manual deploys + approval required
           → Will create separate production resources
```

**Current Phase:** Working on `dev` branch only.

---

## Quick Commands Reference

```powershell
# Check deployment status
az containerapp list -g cogent-preprod-rg -o table

# View logs
az containerapp logs show --name cogent-api -g cogent-preprod-rg --follow

# Restart container
az containerapp revision restart --name cogent-api -g cogent-preprod-rg

# Scale up/down
az containerapp update --name cogent-api -g cogent-preprod-rg --min-replicas 1 --max-replicas 3

# Check GitHub Actions status
# Go to: https://github.com/Alexmarco-gif/Cogentic/actions

# Test health endpoint
curl https://<API_URL>/health

# View Key Vault secrets
az keyvault secret list --vault-name cogent-kv-20260202031440 -o table
```

---

## What Happens Next?

### ✅ When This is Complete:
- Pre-prod environment running on Azure
- Auto-deploys when you push to `dev` branch
- Cost: ~$20/month
- Can demo to stakeholders

### ⏸️ Phase 3 (When Ready for Real Users):
- Configure `staging` branch → staging environment
- Configure `production` branch → production environment
- Add custom domain
- Enable monitoring (Sentry, PostHog)
- Scale up resources

### 🛑 Stop Line (Do NOT Do Yet):
- ❌ Deploy to production
- ❌ Add custom domain
- ❌ Set up monitoring dashboards
- ❌ Multi-region deployment
- ❌ Performance optimization

---

## Success Criteria

You've completed Phase 2 when:
- [ ] All 3 branches pushed to GitHub
- [ ] 7 GitHub secrets added
- [ ] GitHub Actions workflow runs successfully
- [ ] API responds to health check
- [ ] Can view logs in Azure
- [ ] Auth0 login works (if tested)
- [ ] Cost is under $30/month

---

## Support

**Documentation:**
- Operations: `docs/PREPROD_DEPLOYMENT.md`
- Phase Summary: `docs/PHASE2_SUMMARY.md`
- GitHub Setup: `scripts/setup-github-secrets.md`

**If Stuck:**
1. Check GitHub Actions logs for errors
2. Check Azure Container Apps logs
3. Verify all secrets are correct
4. Ensure Redis is fully provisioned (takes 10 min)

---

**Repository:** https://github.com/Alexmarco-gif/Cogentic
**Key Vault:** cogent-kv-20260202031440
**Resource Group:** cogent-preprod-rg
**Estimated Completion Time:** 30 minutes
