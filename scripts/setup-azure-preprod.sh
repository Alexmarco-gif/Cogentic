#!/bin/bash
# ==============================================
# AZURE PRE-PROD INFRASTRUCTURE SETUP
# ==============================================
# Provisions all Azure resources for pre-prod environment
# Run once to create infrastructure
#
# Prerequisites:
# - Azure CLI installed (az)
# - Logged in: az login
# - Set subscription: az account set --subscription <subscription-id>

set -e  # Exit on error

# Configuration
RESOURCE_GROUP="cogent-preprod-rg"
LOCATION="eastus"
REGISTRY_NAME="cogentregistry"
REDIS_NAME="cogent-redis"
KEYVAULT_NAME="cogent-kv-$(date +%s)"  # Unique name
CONTAINER_ENV_NAME="cogent-preprod-env"

echo "=========================================="
echo "🚀 Setting up Azure Pre-Prod Environment"
echo "=========================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Step 1: Create Resource Group
echo "📦 Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --tags environment=preprod project=cogent

# Step 2: Create Container Registry
echo "📦 Creating container registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REGISTRY_NAME" \
  --sku Basic \
  --admin-enabled true

echo "   ✅ Container registry created: $REGISTRY_NAME.azurecr.io"

# Step 3: Create Redis Cache (Free tier)
echo "📦 Creating Redis cache (this may take 5-10 minutes)..."
az redis create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REDIS_NAME" \
  --location "$LOCATION" \
  --sku Basic \
  --vm-size c0 \
  --enable-non-ssl-port false

# Get Redis connection string
REDIS_KEY=$(az redis list-keys \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REDIS_NAME" \
  --query primaryKey -o tsv)

REDIS_HOST="$REDIS_NAME.redis.cache.windows.net"
REDIS_URL="rediss://:$REDIS_KEY@$REDIS_HOST:6380/0"

echo "   ✅ Redis cache created: $REDIS_HOST"

# Step 4: Create Key Vault
echo "📦 Creating Key Vault..."
az keyvault create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$KEYVAULT_NAME" \
  --location "$LOCATION" \
  --enable-rbac-authorization false

echo "   ✅ Key Vault created: $KEYVAULT_NAME"

# Step 5: Store secrets in Key Vault
echo "🔐 Storing secrets in Key Vault..."
echo "   ⚠️  You need to manually add these secrets:"
echo ""
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name database-url --value '<your-neon-url>'"
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name auth0-m2m-client-secret --value '<your-auth0-secret>'"
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name secret-key --value '<your-app-secret-key>'"
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name redis-url --value '$REDIS_URL'"
echo ""

# Step 6: Create Container Apps Environment
echo "📦 Creating Container Apps environment..."
az containerapp env create \
  --name "$CONTAINER_ENV_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

echo "   ✅ Container Apps environment created"

# Summary
echo ""
echo "=========================================="
echo "✅ Infrastructure setup complete!"
echo "=========================================="
echo ""
echo "📋 Next steps:"
echo "   1. Add secrets to Key Vault (commands above)"
echo "   2. Configure GitHub secrets (see scripts/setup-github-secrets.md)"
echo "   3. Run: ./scripts/deploy-preprod.sh"
echo ""
echo "📊 Resources created:"
echo "   • Resource Group: $RESOURCE_GROUP"
echo "   • Container Registry: $REGISTRY_NAME.azurecr.io"
echo "   • Redis Cache: $REDIS_HOST"
echo "   • Key Vault: $KEYVAULT_NAME.vault.azure.net"
echo "   • Container Apps Env: $CONTAINER_ENV_NAME"
echo ""
echo "💰 Estimated monthly cost: ~$20"
echo ""
