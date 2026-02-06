# PHASE 2 QUICK START (PowerShell)
# Run this script to execute all Phase 2 setup steps

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "PHASE 2 INFRASTRUCTURE SETUP" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Prerequisites
Write-Host "STEP 1: Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

docker --version *>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker installed" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Docker not found" -ForegroundColor Red
    exit 1
}

az --version 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Azure CLI installed" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Azure CLI not found" -ForegroundColor Red
    exit 1
}

git --version *>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Git installed" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Git not found" -ForegroundColor Red
    exit 1
}

$accountJson = az account show 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Logged into Azure" -ForegroundColor Green
} else {
    Write-Host "Not logged into Azure. Please run: az login" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "All prerequisites met!" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Test Docker Build:" -ForegroundColor Yellow
Write-Host "   cd .."
Write-Host "   docker build -t cogent-api ."
Write-Host ""
Write-Host "2. Provision Azure Infrastructure:" -ForegroundColor Yellow
Write-Host "   cd scripts"
Write-Host "   # Edit setup-azure-preprod.sh with your settings"
Write-Host "   bash setup-azure-preprod.sh"
Write-Host ""
Write-Host "3. Add Secrets to Key Vault:" -ForegroundColor Yellow
Write-Host "   az keyvault secret set --vault-name <keyvault-name> --name database-url --value '<your-value>'"
Write-Host "   az keyvault secret set --vault-name <keyvault-name> --name auth0-m2m-client-secret --value '<your-value>'"
Write-Host "   az keyvault secret set --vault-name <keyvault-name> --name secret-key --value '<random-32-byte-hex>'"
Write-Host ""
Write-Host "4. Configure GitHub Secrets:" -ForegroundColor Yellow
Write-Host "   See: scripts/setup-github-secrets.md"
Write-Host ""
Write-Host "5. Deploy:" -ForegroundColor Yellow
Write-Host "   git add ."
Write-Host "   git commit -m 'Phase 2: Azure pre-prod infrastructure'"
Write-Host "   git push origin main"
Write-Host ""
Write-Host "6. Run E2E Smoke Tests:" -ForegroundColor Yellow
Write-Host "   `$env:PREPROD_API_URL='https://your-api.azurecontainerapps.io'"
Write-Host "   pytest backend/tests/ -v -m 'e2e'"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - docs/PREPROD_DEPLOYMENT.md"
Write-Host "  - docs/PHASE2_SUMMARY.md"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
