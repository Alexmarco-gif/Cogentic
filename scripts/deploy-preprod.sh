#!/bin/bash
# ==============================================
# DEPLOY TO AZURE PRE-PROD
# ==============================================
# Builds Docker images and deploys to Azure Container Apps
#
# Prerequisites:
# - Infrastructure created (run setup-azure-preprod.sh first)
# - Secrets stored in Key Vault
# - Docker installed

set -e  # Exit on error

# Configuration
RESOURCE_GROUP="cogent-preprod-rg"
REGISTRY_NAME="cogentregistry"
KEYVAULT_NAME="${KEYVAULT_NAME:-cogent-kv}"  # Override if different
CONTAINER_ENV_NAME="cogent-preprod-env"
IMAGE_TAG="${1:-latest}"  # Use argument or default to 'latest'

echo "=========================================="
echo "🚀 Deploying to Azure Pre-Prod"
echo "=========================================="
echo "Image tag: $IMAGE_TAG"
echo ""

# Step 1: Login to Azure Container Registry
echo "🔐 Logging in to container registry..."
az acr login --name "$REGISTRY_NAME"

# Step 2: Build and push API image
echo "🔨 Building API image..."
az acr build \
  --registry "$REGISTRY_NAME" \
  --image "api:$IMAGE_TAG" \
  --image "api:latest" \
  --file Dockerfile \
  .

echo "   ✅ API image pushed"

# Step 3: Build and push Worker image
echo "🔨 Building Worker image..."
az acr build \
  --registry "$REGISTRY_NAME" \
  --image "worker:$IMAGE_TAG" \
  --image "worker:latest" \
  --file Dockerfile.worker \
  .

echo "   ✅ Worker image pushed"

# Step 4: Get Key Vault secrets
echo "🔐 Fetching secrets from Key Vault..."
DATABASE_URL=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name database-url --query value -o tsv)
AUTH0_SECRET=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name auth0-m2m-client-secret --query value -o tsv)
SECRET_KEY=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name secret-key --query value -o tsv)
REDIS_URL=$(az keyvault secret show --vault-name "$KEYVAULT_NAME" --name redis-url --query value -o tsv)

# Step 5: Deploy or Update API Container App
echo "🚢 Deploying API container..."
if az containerapp show --name cogent-api --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  # Update existing
  az containerapp update \
    --name cogent-api \
    --resource-group "$RESOURCE_GROUP" \
    --image "$REGISTRY_NAME.azurecr.io/api:$IMAGE_TAG"
  
  echo "   ✅ API updated"
else
  # Create new
  az containerapp create \
    --name cogent-api \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_ENV_NAME" \
    --image "$REGISTRY_NAME.azurecr.io/api:$IMAGE_TAG" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 2 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --secrets \
      database-url="$DATABASE_URL" \
      auth0-m2m-client-secret="$AUTH0_SECRET" \
      secret-key="$SECRET_KEY" \
      redis-url="$REDIS_URL" \
    --env-vars \
      ENVIRONMENT=preprod \
      DATABASE_URL=secretref:database-url \
      AUTH0_M2M_CLIENT_SECRET=secretref:auth0-m2m-client-secret \
      SECRET_KEY=secretref:secret-key \
      REDIS_URL=secretref:redis-url \
      AUTH0_DOMAIN="$AUTH0_DOMAIN" \
      AUTH0_AUDIENCE="$AUTH0_AUDIENCE" \
      AUTH0_M2M_CLIENT_ID="$AUTH0_M2M_CLIENT_ID" \
    --registry-server "$REGISTRY_NAME.azurecr.io" \
    --registry-username "$REGISTRY_NAME" \
    --registry-password "$(az acr credential show -n $REGISTRY_NAME --query passwords[0].value -o tsv)"
  
  echo "   ✅ API deployed"
fi

# Get API URL
API_URL=$(az containerapp show \
  --name cogent-api \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)

# Step 6: Deploy or Update Worker Container App
echo "🚢 Deploying Worker container..."
if az containerapp show --name cogent-worker --resource-group "$RESOURCE_GROUP" &>/dev/null; then
  # Update existing
  az containerapp update \
    --name cogent-worker \
    --resource-group "$RESOURCE_GROUP" \
    --image "$REGISTRY_NAME.azurecr.io/worker:$IMAGE_TAG"
  
  echo "   ✅ Worker updated"
else
  # Create new
  az containerapp create \
    --name cogent-worker \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_ENV_NAME" \
    --image "$REGISTRY_NAME.azurecr.io/worker:$IMAGE_TAG" \
    --min-replicas 0 \
    --max-replicas 1 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --secrets \
      database-url="$DATABASE_URL" \
      redis-url="$REDIS_URL" \
    --env-vars \
      ENVIRONMENT=preprod \
      DATABASE_URL=secretref:database-url \
      REDIS_URL=secretref:redis-url \
    --registry-server "$REGISTRY_NAME.azurecr.io" \
    --registry-username "$REGISTRY_NAME" \
    --registry-password "$(az acr credential show -n $REGISTRY_NAME --query passwords[0].value -o tsv)"
  
  echo "   ✅ Worker deployed"
fi

# Summary
echo ""
echo "=========================================="
echo "✅ Deployment complete!"
echo "=========================================="
echo ""
echo "🌐 API URL: https://$API_URL"
echo ""
echo "📋 Next steps:"
echo "   1. Test health endpoint: curl https://$API_URL/health"
echo "   2. Run smoke tests: pytest tests/test_preprod.py"
echo "   3. Monitor logs: az containerapp logs show --name cogent-api -g $RESOURCE_GROUP --follow"
echo ""
