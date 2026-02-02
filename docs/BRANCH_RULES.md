# Branch Protection Rules

**Purpose:** Enforce code quality and prevent accidental deployments to production.

---

## Quick Setup

Go to your GitHub repository → **Settings** → **Branches** → **Add branch protection rule**

You'll create **3 rules** (one for each protected branch).

---

## Rule 1: Protect `dev` Branch

**Branch name pattern:** `dev`

### Required Settings:
- ✅ **Require a pull request before merging**
  - Require approvals: **0** (you can merge your own PRs)
  - Dismiss stale pull request approvals: ❌ (not needed)
  
- ✅ **Require status checks to pass before merging**
  - Require branches to be up to date: ✅
  - Status checks that must pass:
    - `quality-checks` (from ci.yml workflow)
  
- ✅ **Require conversation resolution before merging** (optional but recommended)

- ❌ **Do not require signed commits** (adds complexity)

- ❌ **Do not require linear history** (allows merge commits)

- ❌ **Do not lock branch** (you need to push directly sometimes)

### What This Does:
- Every commit triggers CI checks (lint, format, test)
- PRs must pass quality checks before merging
- Auto-deploys to pre-prod after merge
- Solo dev can approve their own PRs

---

## Rule 2: Protect `staging` Branch

**Branch name pattern:** `staging`

### Required Settings:
- ✅ **Require a pull request before merging**
  - Require approvals: **1** (requires your approval)
  - Dismiss stale pull request approvals: ✅
  
- ✅ **Require status checks to pass before merging**
  - Require branches to be up to date: ✅
  - Status checks that must pass:
    - `quality-checks` (from ci.yml workflow)
  
- ✅ **Require conversation resolution before merging**

- ❌ **Do not require signed commits**

- ❌ **Do not require linear history**

- ❌ **Do not include administrators** (allows you to merge in emergencies)

### What This Does:
- Requires PR from `dev` → `staging`
- Must pass CI checks
- You must approve the PR (even if you created it)
- Auto-deploys to staging after merge
- Can bypass in emergency if needed

---

## Rule 3: Protect `production` Branch

**Branch name pattern:** `production`

### Required Settings:
- ✅ **Require a pull request before merging**
  - Require approvals: **1** (minimum for production)
  - Dismiss stale pull request approvals: ✅
  
- ✅ **Require status checks to pass before merging**
  - Require branches to be up to date: ✅
  - Status checks that must pass:
    - `quality-checks` (from ci.yml workflow)
  
- ✅ **Require conversation resolution before merging**

- ✅ **Require deployments to succeed** (if configured)
  - Select environment: `production`

- ❌ **Do not require signed commits**

- ✅ **Require linear history** (recommended for production)

- ❌ **Do not lock branch**

- ❌ **Do not include administrators** (emergency bypass allowed)

### What This Does:
- Requires PR from `staging` → `production`
- Must pass comprehensive CI checks
- Requires approval before merge
- **Manual deployment** trigger (no auto-deploy)
- Requires environment approval in GitHub Actions
- Linear history keeps production clean

---

## GitHub Environment Protection (CRITICAL)

You also need to configure **GitHub Environments** for production approval.

### Setup Steps:

1. Go to: **Repository Settings** → **Environments**
2. Click **New environment**
3. Name it: `production`
4. Configure protection rules:
   - ✅ **Required reviewers**: Add yourself
   - ✅ **Wait timer**: 0 minutes (or 5 minutes for safety delay)
   - Environment secrets: Can add production-specific secrets here (optional)

### What This Does:
- Production deployments pause and wait for manual approval
- You'll get a notification to approve/reject
- Prevents accidental production deploys
- Logs who approved each deployment

---

## Recommended Workflow

### For Features:
```bash
# Work on feature
git checkout -b feature/my-feature dev
# ... make changes ...
git push origin feature/my-feature

# Create PR: feature/my-feature → dev
# CI runs automatically
# Merge PR → auto-deploys to pre-prod
```

### To Staging:
```bash
# Create PR: dev → staging
# CI runs + requires your approval
# Merge PR → auto-deploys to staging
```

### To Production:
```bash
# Create PR: staging → production
# CI runs + requires your approval
# Merge PR (does NOT auto-deploy)

# Manual deployment:
# Go to: Actions → "Deploy to Production" → Run workflow
# Select branch: production
# Click "Run workflow"
# Wait for approval request
# Approve deployment
```

---

## Summary Table

| Branch | Auto-Deploy | Approvals | CI Required | Manual Approval |
|--------|-------------|-----------|-------------|-----------------|
| `dev` | ✅ Yes | 0 | ✅ | ❌ |
| `staging` | ✅ Yes | 1 | ✅ | ❌ |
| `production` | ❌ Manual | 1 | ✅ | ✅ |

---

## Don't Overdo It

### ✅ DO:
- Require CI checks on all branches
- Require approvals for staging/production
- Use GitHub Environment protection for production
- Allow emergency bypass (don't include admins in rules)

### ❌ DON'T (Yet):
- Required signed commits (adds friction)
- Multiple approvers (you're solo/small team)
- Strict linear history on dev/staging
- Lock branches
- Force push protection (useful but can cause issues)

---

## Cost Consideration

**CI runs on every commit** (you chose Option C):
- Free tier: 2,000 minutes/month
- Each CI run: ~3-5 minutes
- Estimate: ~400-600 commits/month before paying

**Recommendation:** If you hit the limit, switch CI to PR-only:
```yaml
# In .github/workflows/ci.yml, change:
on:
  pull_request:  # Only run on PRs
    branches: [dev, staging, production]
```

---

## Testing the Rules

After setting up branch protection:

```bash
# Try to push directly to protected branch (should fail)
git checkout staging
echo "test" >> README.md
git commit -am "direct push test"
git push origin staging
# Expected: ❌ Error - branch is protected

# Correct way (via PR)
git checkout -b test-staging-pr dev
echo "test" >> README.md
git commit -am "test PR"
git push origin test-staging-pr
# Then create PR on GitHub
```

---

## Links

- **Configure branch protection**: https://github.com/Alexmarco-gif/Cogentic/settings/branches
- **Configure environments**: https://github.com/Alexmarco-gif/Cogentic/settings/environments
- **View Actions**: https://github.com/Alexmarco-gif/Cogentic/actions

---

**Next Steps:**
1. Set up the 3 branch protection rules above
2. Create `production` environment with approval
3. Test by creating a PR to `dev`
4. Verify CI runs and checks pass
