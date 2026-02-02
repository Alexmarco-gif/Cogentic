# ==============================================
# AZURE PRE-PROD INFRASTRUCTURE SETUP (PowerShell)
# ==============================================
# Provisions all Azure resources for pre-prod environment
#
# Prerequisites:
# - Azure CLI installed (az)
# - Logged in: az login
# - Set subscription: az account set --subscription <subscription-id>

$ErrorActionPreference = "Stop"

# Configuration
$RESOURCE_GROUP = "cogent-preprod-rg"
$LOCATION = "eastus"
$REGISTRY_NAME = "cogentregistry"
$REDIS_NAME = "cogent-redis"
$KEYVAULT_NAME = "cogent-kv-$(Get-Date -Format 'yyyyMMddHHmmss')"
$CONTAINER_ENV_NAME = "cogent-preprod-env"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Setting up Azure Pre-Prod Environment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Resource Group: $RESOURCE_GROUP" -ForegroundColor Yellow
Write-Host "Location: $LOCATION" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "This will create Azure resources (~`$20/month). Continue? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

# Step 1: Create Resource Group
Write-Host ""
Write-Host "[1/5] Creating resource group..." -ForegroundColor Cyan
az group create `
  --name $RESOURCE_GROUP `
  --location $LOCATION `
  --tags environment=preprod project=cogent `
  --output none

Write-Host "  Resource group created" -ForegroundColor Green

# Step 2: Create Container Registry
Write-Host ""
Write-Host "[2/5] Creating container registry..." -ForegroundColor Cyan
Write-Host "  (This takes ~2 minutes)" -ForegroundColor Yellow
az acr create `
  --resource-group $RESOURCE_GROUP `
  --name $REGISTRY_NAME `
  --sku Basic `
  --admin-enabled true `
  --output none

Write-Host "  Container registry created: $REGISTRY_NAME.azurecr.io" -ForegroundColor Green

# Step 3: Create Redis Cache
Write-Host ""
Write-Host "[3/5] Creating Redis cache..." -ForegroundColor Cyan
Write-Host "  (This takes ~5-10 minutes - be patient)" -ForegroundColor Yellow
az redis create `
  --resource-group $RESOURCE_GROUP `
  --name $REDIS_NAME `
  --location $LOCATION `
  --sku Basic `
  --vm-size c0 `
  --enable-non-ssl-port false `
  --output none

Write-Host "  Redis cache created" -ForegroundColor Green

# Get Redis connection details
$redisKey = az redis list-keys `
  --resource-group $RESOURCE_GROUP `
  --name $REDIS_NAME `
  --query primaryKey `
  --output tsv

$redisHost = "$REDIS_NAME.redis.cache.windows.net"
$redisUrl = "rediss://:$redisKey@$redisHost:6380/0"

Write-Host "  Redis host: $redisHost" -ForegroundColor Green

# Step 4: Create Key Vault
Write-Host ""
Write-Host "[4/5] Creating Key Vault..." -ForegroundColor Cyan
az keyvault create `
  --resource-group $RESOURCE_GROUP `
  --name $KEYVAULT_NAME `
  --location $LOCATION `
  --enable-rbac-authorization false `
  --output none

Write-Host "  Key Vault created: $KEYVAULT_NAME.vault.azure.net" -ForegroundColor Green

# Store Redis URL in Key Vault
Write-Host "  Storing Redis URL in Key Vault..." -ForegroundColor Yellow
az keyvault secret set `
  --vault-name $KEYVAULT_NAME `
  --name redis-url `
  --value $redisUrl `
  --output none

# Step 5: Create Container Apps Environment
Write-Host ""
Write-Host "[5/5] Creating Container Apps environment..." -ForegroundColor Cyan
Write-Host "  (This takes ~3-5 minutes)" -ForegroundColor Yellow
az containerapp env create `
  --name $CONTAINER_ENV_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --output none

Write-Host "  Container Apps environment created" -ForegroundColor Green

# Save Key Vault name for later use
$KEYVAULT_NAME | Out-File -FilePath "..\keyvault-name.txt" -NoNewline

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Infrastructure setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Resources created:" -ForegroundColor Cyan
Write-Host "  Resource Group: $RESOURCE_GROUP" -ForegroundColor White
Write-Host "  Container Registry: $REGISTRY_NAME.azurecr.io" -ForegroundColor White
Write-Host "  Redis Cache: $redisHost" -ForegroundColor White
Write-Host "  Key Vault: $KEYVAULT_NAME.vault.azure.net" -ForegroundColor White
Write-Host "  Container Apps Env: $CONTAINER_ENV_NAME" -ForegroundColor White
Write-Host ""
Write-Host "Monthly cost: ~`$20" -ForegroundColor Yellow
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Add secrets to Key Vault:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   az keyvault secret set --vault-name $KEYVAULT_NAME --name database-url --value '<your-neon-url>'" -ForegroundColor White
Write-Host "   az keyvault secret set --vault-name $KEYVAULT_NAME --name auth0-m2m-client-secret --value '<your-auth0-secret>'" -ForegroundColor White
Write-Host "   az keyvault secret set --vault-name $KEYVAULT_NAME --name secret-key --value '<random-hex-32-bytes>'" -ForegroundColor White
Write-Host ""
Write-Host "   Generate random secret key:" -ForegroundColor Yellow
Write-Host "   -n 32 -c ([byte[]]::new(32) | ForEach-Object { Get-Random -Min 0 -Max 256 } | ForEach-Object { $_.ToString('x2') }) -join ''" -ForegroundColor White
Write-Host ""
Write-Host "2. Configure GitHub secrets:" -ForegroundColor Yellow
Write-Host "   See: scripts/setup-github-secrets.md" -ForegroundColor White
Write-Host ""
Write-Host "3. Deploy containers:" -ForegroundColor Yellow
Write-Host "   git add ." -ForegroundColor White
Write-Host "   git commit -m 'Phase 2: Azure pre-prod infrastructure'" -ForegroundColor White
Write-Host "   git push origin main" -ForegroundColor White
Write-Host ""
Write-Host "Key Vault name saved to: keyvault-name.txt" -ForegroundColor Green
Write-Host ""
