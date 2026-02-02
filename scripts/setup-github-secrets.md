# Azure Pre-Prod GitHub Secrets Setup

Configure these secrets in your GitHub repository for CI/CD deployment.

## Required Secrets

Navigate to: `Settings → Secrets and variables → Actions → New repository secret`

### 1. AZURE_CREDENTIALS

Service Principal credentials for GitHub Actions to deploy to Azure.

**Create Service Principal:**

```bash
az ad sp create-for-rbac \
  --name "github-actions-cogent" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/cogent-preprod-rg \
  --sdk-auth
```

Copy the entire JSON output and paste as secret value.

### 2. AZURE_REGISTRY_NAME

```
cogentregistry
```

### 3. AZURE_RESOURCE_GROUP

```
cogent-preprod-rg
```

### 4. KEYVAULT_NAME

```
cogent-kv-<your-timestamp>
```

(Get from: `az keyvault list --resource-group cogent-preprod-rg --query [0].name -o tsv`)

### 5. AUTH0_DOMAIN

```
your-tenant.auth0.com
```

### 6. AUTH0_AUDIENCE

```
https://api.cogent-ai.com
```

### 7. AUTH0_M2M_CLIENT_ID

```
<your-m2m-client-id>
```

## Optional: Environment-Specific Secrets

If you want to run tests in CI/CD:

- `PREPROD_API_URL` - Set after first deployment
- `AUTH0_TEST_USER_TOKEN` - For integration tests

## Verify Setup

```bash
# List all secrets (names only)
gh secret list

# Test workflow
gh workflow run deploy-preprod.yml
```

## Security Notes

- ✅ Service Principal has minimal permissions (contributor on resource group only)
- ✅ Secrets are encrypted in GitHub
- ✅ Use Key Vault references in Container Apps (never hardcode in workflows)
- ❌ Never commit secrets to git
- ❌ Never log secrets in CI/CD output
