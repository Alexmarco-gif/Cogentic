# CI/CD Quick Start

**Setup Time:** 10 minutes  
**What You Get:** Automated testing, linting, formatting, and deployment pipeline

---

## Step 1: Setup Local Tools (5 minutes)

```powershell
# Run the setup script
cd "C:\Users\Alex Marco\Documents\Cogent"
.\scripts\setup-ci-tools.ps1
```

This will:
- ✅ Install ruff, black, pytest
- ✅ Optionally setup pre-commit hooks
- ✅ Test all tools are working

---

## Step 2: Configure Branch Protection (5 minutes)

Go to: https://github.com/Alexmarco-gif/Cogentic/settings/branches

### Create 3 Rules:

**Rule 1: `dev` branch**
- ✅ Require pull request before merging
- ✅ Require status checks: `quality-checks`
- Approvals: 0 (you can self-approve)

**Rule 2: `staging` branch**
- ✅ Require pull request before merging
- ✅ Require status checks: `quality-checks`
- Approvals: 1 (requires your approval)

**Rule 3: `production` branch**
- ✅ Require pull request before merging
- ✅ Require status checks: `quality-checks`
- Approvals: 1
- ✅ Require linear history

**Detailed instructions:** [docs/BRANCH_RULES.md](./docs/BRANCH_RULES.md)

---

## Step 3: Setup Production Environment (2 minutes)

Go to: https://github.com/Alexmarco-gif/Cogentic/settings/environments

1. Click "New environment"
2. Name: `production`
3. ✅ Required reviewers: Add yourself
4. Wait timer: 0 minutes (or 5 for safety delay)
5. Save

---

## Step 4: Test the CI Pipeline (3 minutes)

```powershell
# Create a test branch
git checkout -b test-ci

# Make a small change
echo "# CI Test" >> README.md

# Format and commit
black backend/
git add .
git commit -m "test: CI pipeline"

# Push and create PR
git push origin test-ci
```

Then:
1. Go to: https://github.com/Alexmarco-gif/Cogentic/pulls
2. Create PR: `test-ci` → `dev`
3. Watch CI run automatically
4. When green, merge PR
5. Watch auto-deploy to pre-prod

---

## What Happens Now?

### Every Commit:
```
git commit → CI runs (lint, format, test) → ✅ or ❌
```

### Push to dev:
```
git push origin dev → CI checks → Build images → Deploy to pre-prod
```

### Push to staging:
```
git push origin staging → CI checks → Build images → Deploy to staging
```

### Production Deploy:
```
Manual trigger → CI checks → Wait for approval → Deploy to production
```

---

## Daily Workflow

### 1. Start New Feature
```powershell
git checkout dev
git pull origin dev
git checkout -b feature/my-feature
```

### 2. Write Code
```python
# backend/api/v1/my_feature.py
# ... your code ...
```

### 3. Run Local Checks
```powershell
# Format code
black backend/

# Lint
ruff check backend/ --fix

# Test
pytest backend/tests/ -v
```

### 4. Commit and Push
```powershell
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature
```

### 5. Create PR
- Go to GitHub
- Create PR: `feature/my-feature` → `dev`
- CI runs automatically
- Merge when green

### 6. Auto-Deploy
- Merge triggers deployment to pre-prod
- Check: https://github.com/Alexmarco-gif/Cogentic/actions
- Test: `curl https://<API_URL>/health`

---

## Quick Commands

```powershell
# Format all code
black backend/

# Check linting
ruff check backend/

# Fix linting issues
ruff check backend/ --fix

# Run tests
pytest backend/tests/ -v

# Run tests with coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing

# Do everything
black backend/ && ruff check backend/ --fix && pytest backend/tests/ -v
```

---

## Troubleshooting

### CI Failed: Syntax Error
```powershell
# Fix the error shown in GitHub Actions
# Then push again
git add .
git commit -m "fix: syntax error"
git push origin <branch>
```

### CI Failed: Format Error
```powershell
# Format the code
black backend/

# Commit
git add .
git commit -m "style: format code"
git push origin <branch>
```

### CI Failed: Test Error
```powershell
# Fix the failing test
# Run locally to verify
pytest backend/tests/test_whatever.py -v

# Commit fix
git add .
git commit -m "fix: failing test"
git push origin <branch>
```

### Deployment Failed
```powershell
# Check logs
az containerapp logs show --name cogent-api -g cogent-preprod-rg --follow

# Common fixes:
# 1. Check secrets in Key Vault
# 2. Check Dockerfile builds locally
# 3. Check health endpoint works
```

---

## Cost Tracking

### GitHub Actions Minutes:
- **Free tier:** 2,000 minutes/month
- **Your usage:** ~5 min per commit
- **Limit:** ~400 commits/month

**If you hit the limit:**
```yaml
# In .github/workflows/ci.yml, change to PR-only:
on:
  pull_request:
    branches: [dev, staging, production]
```

### Azure Costs:
- **Pre-prod:** ~$20/month (running now)
- **Staging:** ~$30/month (when created)
- **Production:** ~$100/month (Phase 3)

---

## What's Running?

### Workflows Created:
1. ✅ **ci.yml** - Code quality checks on all commits
2. ✅ **deploy-preprod.yml** - Auto-deploy to pre-prod (dev branch)
3. ✅ **deploy-staging.yml** - Auto-deploy to staging (staging branch)
4. ✅ **deploy-production.yml** - Manual deploy to production

### Tools Configured:
- ✅ **ruff** - Fast Python linter
- ✅ **black** - Code formatter
- ✅ **pytest** - Test runner
- ✅ **pre-commit** - Optional git hooks

### Environments:
- ✅ **dev** → Pre-prod (cogent-preprod-rg) - Running
- ⏸️ **staging** → Staging (cogent-staging-rg) - Creates on first push
- ⏸️ **production** → Production (cogent-production-rg) - Manual setup

---

## Next Actions

### Now:
1. ✅ Run `.\scripts\setup-ci-tools.ps1`
2. ✅ Configure branch protection rules
3. ✅ Setup production environment
4. ✅ Create test PR to verify CI works

### Soon (When Needed):
- ⏸️ Create staging environment (push to staging branch)
- ⏸️ Create production environment (manual trigger)
- ⏸️ Add monitoring (Sentry, PostHog)
- ⏸️ Custom domain for production

---

## Documentation

- **Full guide:** [docs/CI_CD_GUIDE.md](./docs/CI_CD_GUIDE.md)
- **Branch rules:** [docs/BRANCH_RULES.md](./docs/BRANCH_RULES.md)
- **Phase 2 guide:** [PHASE2_STEP_BY_STEP.md](../PHASE2_STEP_BY_STEP.md)

---

## Success Checklist

- [ ] Local CI tools installed (`setup-ci-tools.ps1`)
- [ ] Branch protection rules configured (dev, staging, production)
- [ ] Production environment created with approval
- [ ] Test PR created and CI passed
- [ ] Test PR merged and deployed to pre-prod
- [ ] Health check successful

**When all checked:** You're ready to ship features with confidence! 🚀
