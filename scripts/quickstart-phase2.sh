#!/bin/bash
# ==============================================
# PHASE 2 QUICK START
# ==============================================
# Run this script to execute all Phase 2 setup steps
# This is a guided walkthrough - read each step before proceeding

set -e

echo "=========================================="
echo "📋 PHASE 2 INFRASTRUCTURE SETUP"
echo "=========================================="
echo ""
echo "This script will guide you through:"
echo "  1. Local Docker validation"
echo "  2. Azure infrastructure provisioning"
echo "  3. Secret configuration"
echo "  4. First deployment"
echo "  5. Smoke tests"
echo ""
read -p "Ready to start? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. Run this script when ready."
    exit 0
fi

# Step 1: Prerequisites check
echo ""
echo "=========================================="
echo "STEP 1: Checking prerequisites..."
echo "=========================================="

command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install: https://docker.com"; exit 1; }
echo "✅ Docker installed"

command -v az >/dev/null 2>&1 || { echo "❌ Azure CLI not found. Install: https://aka.ms/install-azure-cli"; exit 1; }
echo "✅ Azure CLI installed"

command -v git >/dev/null 2>&1 || { echo "❌ Git not found"; exit 1; }
echo "✅ Git installed"

# Check if logged into Azure
az account show >/dev/null 2>&1 || { 
    echo "❌ Not logged into Azure. Running 'az login'..."
    az login
}
echo "✅ Logged into Azure"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "📌 Using subscription: $SUBSCRIPTION_ID"

# Step 2: Local Docker test
echo ""
echo "=========================================="
echo "STEP 2: Testing Docker build locally..."
echo "=========================================="
read -p "Build Docker image? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker build -t cogent-api -f Dockerfile .
    echo "✅ Docker image built successfully"
    echo ""
    echo "To test locally, run:"
    echo "  docker run -p 8000:8000 --env-file .env cogent-api"
    echo ""
    read -p "Press Enter to continue..."
fi

# Step 3: Azure infrastructure
echo ""
echo "=========================================="
echo "STEP 3: Provisioning Azure infrastructure..."
echo "=========================================="
echo "⚠️  This will create resources in Azure (~$20/month)"
echo ""
read -p "Proceed with Azure setup? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd scripts
    chmod +x setup-azure-preprod.sh
    ./setup-azure-preprod.sh
    cd ..
    echo ""
    echo "✅ Azure infrastructure created"
fi

# Step 4: Configure secrets
echo ""
echo "=========================================="
echo "STEP 4: Configure secrets in Key Vault..."
echo "=========================================="
echo ""
echo "You need to add these secrets manually:"
echo ""
echo "1. Get your Key Vault name:"
echo "   KEYVAULT_NAME=\$(az keyvault list -g cogent-preprod-rg --query [0].name -o tsv)"
echo ""
echo "2. Add secrets:"
echo "   az keyvault secret set --vault-name \$KEYVAULT_NAME --name database-url --value 'your-neon-url'"
echo "   az keyvault secret set --vault-name \$KEYVAULT_NAME --name auth0-m2m-client-secret --value 'your-auth0-secret'"
echo "   az keyvault secret set --vault-name \$KEYVAULT_NAME --name secret-key --value '\$(openssl rand -hex 32)'"
echo ""
read -p "Have you added secrets to Key Vault? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Add secrets before proceeding to deployment"
    exit 0
fi

# Step 5: GitHub secrets
echo ""
echo "=========================================="
echo "STEP 5: Configure GitHub secrets..."
echo "=========================================="
echo ""
echo "Follow the guide: scripts/setup-github-secrets.md"
echo ""
echo "Required secrets:"
echo "  - AZURE_CREDENTIALS"
echo "  - AZURE_REGISTRY_NAME=cogentregistry"
echo "  - AZURE_RESOURCE_GROUP=cogent-preprod-rg"
echo "  - KEYVAULT_NAME=<your-keyvault-name>"
echo "  - AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_M2M_CLIENT_ID"
echo ""
read -p "Have you configured GitHub secrets? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  Configure GitHub secrets to enable CI/CD"
    echo "You can still deploy manually using: ./scripts/deploy-preprod.sh"
fi

# Step 6: Deploy
echo ""
echo "=========================================="
echo "STEP 6: First deployment..."
echo "=========================================="
echo ""
echo "Choose deployment method:"
echo "  1. Manual deploy (using scripts/deploy-preprod.sh)"
echo "  2. Git push (triggers GitHub Actions)"
echo ""
read -p "Deploy now? (1/2/n) " -n 1 -r
echo
if [[ $REPLY == "1" ]]; then
    cd scripts
    chmod +x deploy-preprod.sh
    ./deploy-preprod.sh
    cd ..
elif [[ $REPLY == "2" ]]; then
    echo "Committing changes and pushing to main..."
    git add .
    git commit -m "Phase 2: Azure pre-prod infrastructure" || echo "Nothing to commit"
    git push origin main
    echo ""
    echo "✅ Pushed to main - check GitHub Actions for deployment status"
    echo "   URL: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
fi

# Step 7: Validation
echo ""
echo "=========================================="
echo "STEP 7: Validate deployment..."
echo "=========================================="
echo ""
echo "Getting API URL..."
API_URL=$(az containerapp show --name cogent-api --resource-group cogent-preprod-rg --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo "⚠️  API not deployed yet. Wait for deployment to complete."
else
    echo "✅ API URL: https://$API_URL"
    echo ""
    echo "Testing health endpoint..."
    if curl -f "https://$API_URL/health" 2>/dev/null; then
        echo "✅ Health check passed!"
    else
        echo "⚠️  Health check failed - container may still be starting"
    fi
    
    echo ""
    echo "Run smoke tests:"
    echo "  export PREPROD_API_URL=https://$API_URL"
    echo "  pytest backend/tests/test_preprod.py -v"
fi

# Summary
echo ""
echo "=========================================="
echo "✅ PHASE 2 SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "📋 What you have:"
echo "  • Azure Container Apps (API + Worker)"
echo "  • Azure Container Registry"
echo "  • Redis Cache"
echo "  • Key Vault with secrets"
echo "  • CI/CD via GitHub Actions"
echo ""
echo "📖 Documentation:"
echo "  • Operations: docs/PREPROD_DEPLOYMENT.md"
echo "  • Summary: docs/PHASE2_SUMMARY.md"
echo ""
echo "🚀 Next steps:"
echo "  1. Run smoke tests (see above)"
echo "  2. Test Auth0 login flow"
echo "  3. Monitor for 1 week"
echo "  4. Move to Phase 3 (Product features)"
echo ""
echo "💰 Monthly cost: ~\$20"
echo ""
echo "🛠️  Useful commands:"
echo "  • View logs: az containerapp logs show --name cogent-api -g cogent-preprod-rg --follow"
echo "  • Check status: az containerapp list -g cogent-preprod-rg -o table"
echo "  • Scale down: az containerapp update --name cogent-api -g cogent-preprod-rg --min-replicas 0"
echo "  • Tear down: az group delete --name cogent-preprod-rg --yes"
echo ""
