// =============================================================================
// Bicep Parameters — Staging Environment
// =============================================================================
// Deploy:
//   az deployment group create \
//     --resource-group cogent-staging \
//     --template-file infrastructure/main.bicep \
//     --parameters infrastructure/parameters/staging.bicepparam

using '../main.bicep'

param environment = 'staging'
param location = 'uksouth'

// Container images — updated by CI/CD pipeline
param backendImage = 'cogentacrstg.azurecr.io/cogent-backend:latest'
param workerImage = 'cogentacrstg.azurecr.io/cogent-worker:latest'
param frontendImage = 'cogentacrstg.azurecr.io/cogent-frontend:latest'

// Staging runs minimal replicas
param backendMinReplicas = 1
param backendMaxReplicas = 2
param workerReplicas = 1

// Staging now deploys workloads by default. For first-time infra-only setup, override with:
//   az deployment group create ... --parameters deployWorkloads=false
param deployWorkloads = true

// Database
param dbAdminUser = 'cogentadmin'
param dbName = 'cogent'
// Placeholder only. Override at deploy time:
//   az deployment group create ... --parameters dbAdminPassword=$DB_PASS
param dbAdminPassword = 'REPLACE_AT_DEPLOY_TIME'
