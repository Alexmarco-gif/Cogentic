// =============================================================================
// Bicep Parameters — Production Environment
// =============================================================================
// Deploy:
//   az deployment group create \
//     --resource-group cogent-production \
//     --template-file infrastructure/main.bicep \
//     --parameters infrastructure/parameters/production.bicepparam

using '../main.bicep'

param environment = 'production'
param location = 'uksouth'

// Container images — updated by CI/CD pipeline on release
param backendImage = 'cogentacrprod.azurecr.io/cogent-backend:latest'
param workerImage = 'cogentacrprod.azurecr.io/cogent-worker:latest'
param frontendImage = 'cogentacrprod.azurecr.io/cogent-frontend:latest'

// Production runs with redundancy
param backendMinReplicas = 2
param backendMaxReplicas = 10
param workerReplicas = 2

// Database
param dbAdminUser = 'cogentadmin'
param dbName = 'cogent'
// Placeholder only. Override at deploy time:
//   az deployment group create ... --parameters dbAdminPassword=$DB_PASS
param dbAdminPassword = 'REPLACE_AT_DEPLOY_TIME'
