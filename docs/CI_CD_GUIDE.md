# CI/CD Workflow Guide

**Your Setup:** Standard 3-environment pipeline with automated quality checks.

---

## Overview

```
Feature Branch → dev → staging → production
     ↓           ↓        ↓          ↓
    CI       Pre-prod  Staging    Prod
  (checks)   (auto)    (auto)   (manual)
```

### What Runs When:

| Event | Workflow | What Happens |
|-------|----------|--------------|
| Any commit | `ci.yml` | Lint, format check, tests |
| Push to `dev` | `deploy-preprod.yml` | CI + deploy to pre-prod |
| Push to `staging` | `deploy-staging.yml` | CI + deploy to staging |
| Manual trigger | `deploy-production.yml` | CI + approval + deploy to prod |

---

## Workflow 1: CI (Code Quality)

**File:** `.github/workflows/ci.yml`  
**Triggers:** Every commit to any branch  
**Duration:** ~3-5 minutes

### Steps:
1. **Lint with ruff** - Catches syntax errors, undefined names
2. **Format check with black** - Ensures consistent code style
3. **Run tests with pytest** - Validates functionality
4. **Upload coverage** (on PRs only) - Code coverage reports

### What Gets Checked:
```python
# Linting (ruff)
- Syntax errors (E9)
- Undefined names (F63, F7, F82)
- Code style violations (E, W)
- Import sorting (I)

# Formatting (black)
- Line length: 88 characters
- Consistent indentation
- String quote style

# Tests (pytest)
- All tests except preprod/e2e
- Minimum coverage tracking
- Fails on first error
```

### Passing Criteria:
- ✅ No syntax errors
- ✅ Code formatted with black
- ✅ All tests pass
- ⚠️ Coverage doesn't fail build (just reports)

---

## Workflow 2: Deploy to Pre-Prod

**File:** `.github/workflows/deploy-preprod.yml`  
**Triggers:** Push to `dev` branch  
**Duration:** ~10-15 minutes  
**Environment:** `dev` → Pre-Prod (cogent-preprod-rg)

### Steps:
1. Checkout code
2. Login to Azure
3. Build Docker images (API + Worker)
4. Get secrets from Key Vault
5. Deploy to Container Apps
6. Health check

### What Gets Deployed:
- **API Container**: FastAPI app on port 8000
- **Worker Container**: Background job processor
- **Resource Group**: `cogent-preprod-rg`
- **Environment**: `cogent-preprod-env`

### Auto-Deploy:
```bash
# Any push to dev triggers deployment
git checkout dev
git merge feature/my-feature
git push origin dev
# → CI runs → Builds → Deploys to pre-prod
```

---

## Workflow 3: Deploy to Staging

**File:** `.github/workflows/deploy-staging.yml`  
**Triggers:** Push to `staging` branch  
**Duration:** ~15-20 minutes  
**Environment:** `staging` → Staging (cogent-staging-rg)

### Steps:
1. **Run CI checks first** (inline)
2. Build separate staging images
3. Create staging infrastructure (if needed)
4. Deploy to staging environment
5. Health check

### First-Time Setup:
When you first push to `staging`, the workflow will:
- Create `cogent-staging-rg` resource group
- Create `cogent-staging-env` Container Apps environment
- Create `cogent-staging-api` and `cogent-staging-worker` apps
- Use dev secrets (or staging-specific if configured)

### Usage:
```bash
# Merge dev to staging
git checkout staging
git merge dev
git push origin staging
# → CI checks → Builds staging images → Auto-deploys
```

---

## Workflow 4: Deploy to Production

**File:** `.github/workflows/deploy-production.yml`  
**Triggers:** Manual only (workflow_dispatch)  
**Duration:** ~20-30 minutes  
**Environment:** `production` → Production (cogent-production-rg)

### Steps:
1. **Comprehensive CI checks**
2. **Wait for manual approval** ⏸️
3. Build production images
4. Create production infrastructure (if needed)
5. Deploy with increased resources
6. Health check (fails deployment if unhealthy)
7. Notify on success

### Differences from Staging:
- Higher resources (1 CPU, 2GB RAM for API)
- Minimum 1 replica (no scale to zero)
- Uses production-specific secrets
- Requires manual approval
- Rollback on health check failure

### How to Deploy:
1. Merge staging → production (via PR)
2. Go to: https://github.com/Alexmarco-gif/Cogentic/actions
3. Select "Deploy to Production"
4. Click "Run workflow"
5. Select branch: `production`
6. Click "Run workflow" button
7. Wait for approval notification
8. Review changes and approve
9. Deployment continues
10. Verify health check passes

---

## Code Quality Tools

### Ruff (Linter)
```bash
# Run locally
ruff check backend/

# Auto-fix issues
ruff check backend/ --fix

# Check specific rules
ruff check backend/ --select=E9,F63,F7,F82
```

**Configured in:** `pyproject.toml`

### Black (Formatter)
```bash
# Check formatting
black --check backend/

# Format code
black backend/

# Format single file
black backend/main.py
```

### Pytest (Testing)
```bash
# Run all tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing

# Run specific test file
pytest backend/tests/test_auth.py -v

# Run specific test
pytest backend/tests/test_auth.py::test_login -v
```

---

## Local Development Workflow

### 1. Create Feature Branch
```bash
git checkout dev
git pull origin dev
git checkout -b feature/my-awesome-feature
```

### 2. Write Code + Tests
```python
# backend/api/v1/my_feature.py
@router.get("/my-feature")
async def my_feature():
    return {"status": "awesome"}

# backend/tests/test_my_feature.py
def test_my_feature():
    response = client.get("/my-feature")
    assert response.status_code == 200
```

### 3. Run Quality Checks Locally
```bash
# Format code
black backend/

# Check linting
ruff check backend/

# Run tests
pytest backend/tests/ -v
```

### 4. Commit and Push
```bash
git add .
git commit -m "Add awesome feature"
git push origin feature/my-awesome-feature
```

### 5. Create Pull Request
- Go to GitHub repository
- Click "Pull requests" → "New pull request"
- Base: `dev` ← Compare: `feature/my-awesome-feature`
- CI runs automatically
- Wait for green checkmarks
- Merge PR

### 6. Auto-Deploy to Pre-Prod
- Merge triggers `deploy-preprod.yml`
- Wait ~10-15 minutes
- Check deployment: https://github.com/Alexmarco-gif/Cogentic/actions
- Test API: `curl https://<API_URL>/health`

---

## Promoting to Staging

### When to Promote:
- Multiple features completed on dev
- Pre-prod testing successful
- Ready for stakeholder demo
- Need more stable environment

### How to Promote:
```bash
# Ensure dev is up to date
git checkout dev
git pull origin dev

# Merge to staging
git checkout staging
git pull origin staging
git merge dev

# Push (triggers auto-deploy to staging)
git push origin staging

# Monitor deployment
# https://github.com/Alexmarco-gif/Cogentic/actions
```

---

## Promoting to Production

### When to Promote:
- Staging fully tested
- Stakeholders approved
- Ready for real users
- No known critical bugs

### How to Promote:
```bash
# Create PR: staging → production
git checkout staging
git pull origin staging
git checkout production
git pull origin production

# Create PR on GitHub (don't merge directly)
git push origin production

# After PR approved and merged:
# 1. Go to Actions tab
# 2. Select "Deploy to Production"
# 3. Run workflow on production branch
# 4. Approve deployment when prompted
# 5. Monitor deployment
```

---

## Handling Failed Deployments

### CI Failed (Red X)
```bash
# View error in GitHub Actions
# Fix locally:
black backend/
ruff check backend/ --fix
pytest backend/tests/ -v

# Commit fix
git add .
git commit -m "Fix CI issues"
git push origin <branch>
```

### Deployment Failed
```bash
# View deployment logs
az containerapp logs show \
  --name cogent-api \
  --resource-group <resource-group> \
  --follow

# Common issues:
# 1. Secrets not found → Check Key Vault
# 2. Image build failed → Check Dockerfile
# 3. Health check failed → Check /health endpoint
```

### Production Rollback
```bash
# Find last successful revision
az containerapp revision list \
  --name cogent-production-api \
  --resource-group cogent-production-rg \
  -o table

# Activate previous revision
az containerapp revision activate \
  --name cogent-production-api \
  --resource-group cogent-production-rg \
  --revision <previous-revision-name>
```

---

## Quick Reference Commands

### Check CI Status
```bash
# View all workflow runs
gh run list --limit 10

# View specific run
gh run view <run-id>

# Watch latest run
gh run watch
```

### Check Deployments
```bash
# Pre-prod
az containerapp list -g cogent-preprod-rg -o table

# Staging
az containerapp list -g cogent-staging-rg -o table

# Production
az containerapp list -g cogent-production-rg -o table
```

### View Logs
```bash
# Pre-prod API
az containerapp logs show --name cogent-api -g cogent-preprod-rg --follow

# Staging API
az containerapp logs show --name cogent-staging-api -g cogent-staging-rg --follow

# Production API
az containerapp logs show --name cogent-production-api -g cogent-production-rg --follow
```

---

## GitHub Actions Secrets Required

All secrets are already configured (from Phase 2 Step 3):
- `AZURE_CREDENTIALS` - Service Principal JSON
- `AZURE_REGISTRY_NAME` - cogentregistry
- `AZURE_RESOURCE_GROUP` - cogent-preprod-rg
- `KEYVAULT_NAME` - cogent-kv-20260202031440
- `AUTH0_DOMAIN` - Your Auth0 tenant
- `AUTH0_AUDIENCE` - https://api.cogent-ai.com
- `AUTH0_M2M_CLIENT_ID` - Your M2M client ID

---

## Cost Monitoring

### GitHub Actions Minutes:
- Free tier: 2,000 minutes/month
- Current usage: ~5 min/commit × commits
- If exceeded: Switch CI to PR-only

### Azure Resources:
- **Pre-prod**: ~$20/month (scale to zero)
- **Staging**: ~$30/month (when created)
- **Production**: ~$100/month (min 1 replica)

**Total estimate:** $150/month when all 3 environments active.

---

## Best Practices

### ✅ DO:
- Run quality checks locally before pushing
- Create PRs for all changes to protected branches
- Test in pre-prod before promoting to staging
- Test in staging before promoting to production
- Write tests for new features
- Keep commits small and focused

### ❌ DON'T:
- Push directly to `staging` or `production`
- Skip CI checks
- Deploy to production without staging test
- Commit without running tests locally
- Push broken code to dev

---

## Next Steps

1. ✅ Configure branch protection rules (see [BRANCH_RULES.md](./BRANCH_RULES.md))
2. ✅ Test CI by creating a PR
3. ✅ Deploy to pre-prod (already configured)
4. ⏸️ Deploy to staging (when needed)
5. ⏸️ Deploy to production (Phase 3)

---

**Links:**
- GitHub Actions: https://github.com/Alexmarco-gif/Cogentic/actions
- Branch Settings: https://github.com/Alexmarco-gif/Cogentic/settings/branches
- Environment Settings: https://github.com/Alexmarco-gif/Cogentic/settings/environments
