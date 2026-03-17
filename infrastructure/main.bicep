// =============================================================================
// Cogent — Infrastructure as Code (Azure Bicep)
// =============================================================================
// Deploys the full Cogent stack to Azure:
//   • Container Apps Environment + 3 Container Apps (backend, worker, frontend)
//   • Azure Container Registry
//   • Azure Cache for Redis
//   • Azure Key Vault (secrets injection)
//   • Log Analytics workspace
//
// Usage:
//   az deployment group create \
//     --resource-group cogent-<env> \
//     --template-file infrastructure/main.bicep \
//     --parameters infrastructure/parameters/staging.bicepparam
// =============================================================================

targetScope = 'resourceGroup'

// ── Parameters ──────────────────────────────────────────────────────────────
@description('Environment name (staging or production)')
@allowed(['staging', 'production'])
param environment string

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Project name used as prefix for resource names')
param projectName string = 'cogent'

@description('Backend container image (full ACR path + tag)')
param backendImage string

@description('Worker container image (full ACR path + tag)')
param workerImage string

@description('Frontend container image (full ACR path + tag)')
param frontendImage string

@description('Number of backend replicas')
@minValue(1)
@maxValue(10)
param backendMinReplicas int = environment == 'production' ? 2 : 1

@description('Max backend replicas for autoscaling')
@minValue(1)
@maxValue(30)
param backendMaxReplicas int = environment == 'production' ? 10 : 3

@description('Number of worker replicas')
@minValue(1)
@maxValue(10)
param workerReplicas int = environment == 'production' ? 2 : 1

@description('PostgreSQL administrator login username')
param dbAdminUser string = 'cogentadmin'

@description('PostgreSQL administrator login password (store in Key Vault before deploy)')
@secure()
param dbAdminPassword string

@description('Application database name')
param dbName string = 'cogent'

// ── Variables ───────────────────────────────────────────────────────────────
var envSuffix = environment == 'production' ? 'prod' : 'stg'
var resourcePrefix = '${projectName}-${envSuffix}'
var databaseUrl = 'postgresql://${dbAdminUser}:${dbAdminPassword}@${postgres.outputs.serverFqdn}:5432/${dbName}?sslmode=require'

// ── Log Analytics ───────────────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resourcePrefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: environment == 'production' ? 90 : 30
  }
}

// ── Container Registry ──────────────────────────────────────────────────────
module acr 'modules/container-registry.bicep' = {
  name: 'acr'
  params: {
    name: '${projectName}acr${envSuffix}'
    location: location
    sku: environment == 'production' ? 'Standard' : 'Basic'
  }
}

// ── Key Vault ───────────────────────────────────────────────────────────────
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    name: '${resourcePrefix}-kv'
    location: location
  }
}

// ── Azure PostgreSQL Flexible Server ────────────────────────────────────────
module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    name: '${resourcePrefix}-postgres'
    location: location
    administratorLogin: dbAdminUser
    administratorLoginPassword: dbAdminPassword
    databaseName: dbName
    skuTier: environment == 'production' ? 'GeneralPurpose' : 'Burstable'
    skuName: environment == 'production' ? 'Standard_D4s_v3' : 'Standard_B2ms'
    storageSizeGB: environment == 'production' ? 128 : 32
    backupRetentionDays: environment == 'production' ? 35 : 7
    geoRedundantBackup: environment == 'production'
  }
}

// Store the database connection string in Key Vault so Container Apps can
// reference it without the password ever appearing in Bicep outputs or logs.
resource dbUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: '${keyVault.name}/database-url'
  properties: {
    value: databaseUrl
  }
}

// ── Azure Cache for Redis ───────────────────────────────────────────────────
module redis 'modules/redis.bicep' = {
  name: 'redis'
  params: {
    name: '${resourcePrefix}-redis'
    location: location
    sku: environment == 'production' ? 'Standard' : 'Basic'
    capacity: environment == 'production' ? 2 : 0
    enableNonSslPort: false
  }
}

// ── Container Apps Environment ──────────────────────────────────────────────
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resourcePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    zoneRedundant: environment == 'production'
  }
}

// ── Backend Container App ───────────────────────────────────────────────────
module backend 'modules/container-app.bicep' = {
  name: 'backend'
  params: {
    name: '${resourcePrefix}-backend'
    location: location
    environmentId: containerEnv.id
    image: backendImage
    targetPort: 8000
    minReplicas: backendMinReplicas
    maxReplicas: backendMaxReplicas
    cpu: json('1.0')
    memory: '2Gi'
    keyVaultName: keyVault.outputs.name
    envVars: [
      { name: 'APP_ENV',           value: environment }
      { name: 'ENVIRONMENT',       value: environment }
      { name: 'REDIS_URL',         secretRef: 'redis-url' }
      { name: 'DATABASE_URL',      secretRef: 'database-url' }
      { name: 'SECRET_KEY',        secretRef: 'secret-key' }
      { name: 'AUTH0_DOMAIN',      secretRef: 'auth0-domain' }
      { name: 'AUTH0_AUDIENCE',    secretRef: 'auth0-audience' }
      { name: 'AUTH0_M2M_CLIENT_ID',     secretRef: 'auth0-m2m-client-id' }
      { name: 'AUTH0_M2M_CLIENT_SECRET', secretRef: 'auth0-m2m-client-secret' }
      { name: 'AUTH0_WEBHOOK_SECRET',    secretRef: 'auth0-webhook-secret' }
      { name: 'OPENAI_API_KEY',          secretRef: 'openai-api-key' }
      { name: 'SENTRY_DSN',              secretRef: 'sentry-dsn' }
      { name: 'CORS_ORIGINS',     value: environment == 'production'
        ? 'https://app.cogent.ai'
        : 'https://staging.cogent.ai' }
      { name: 'REQUIRE_HEALTHY_DB_ON_STARTUP',    value: 'true' }
      { name: 'REQUIRE_HEALTHY_REDIS_ON_STARTUP',  value: 'true' }
    ]
    healthProbePath: '/health'
    isExternal: true
  }
}

// ── Worker Container App ────────────────────────────────────────────────────
module worker 'modules/container-app.bicep' = {
  name: 'worker'
  params: {
    name: '${resourcePrefix}-worker'
    location: location
    environmentId: containerEnv.id
    image: workerImage
    targetPort: 8001
    minReplicas: workerReplicas
    maxReplicas: workerReplicas
    cpu: json('0.5')
    memory: '1Gi'
    keyVaultName: keyVault.outputs.name
    envVars: [
      { name: 'APP_ENV',           value: environment }
      { name: 'ENVIRONMENT',       value: environment }
      { name: 'REDIS_URL',         secretRef: 'redis-url' }
      { name: 'DATABASE_URL',      secretRef: 'database-url' }
      { name: 'OPENAI_API_KEY',    secretRef: 'openai-api-key' }
      { name: 'SECRET_KEY',        secretRef: 'secret-key' }
      { name: 'AUTH0_DOMAIN',      secretRef: 'auth0-domain' }
      { name: 'AUTH0_AUDIENCE',    secretRef: 'auth0-audience' }
      { name: 'AUTH0_M2M_CLIENT_ID',     secretRef: 'auth0-m2m-client-id' }
      { name: 'AUTH0_M2M_CLIENT_SECRET', secretRef: 'auth0-m2m-client-secret' }
    ]
    healthProbePath: '/health'
    isExternal: false
  }
}

// ── Frontend Container App ──────────────────────────────────────────────────
module frontend 'modules/container-app.bicep' = {
  name: 'frontend'
  params: {
    name: '${resourcePrefix}-frontend'
    location: location
    environmentId: containerEnv.id
    image: frontendImage
    targetPort: 3000
    minReplicas: backendMinReplicas
    maxReplicas: backendMaxReplicas
    cpu: json('0.5')
    memory: '1Gi'
    keyVaultName: keyVault.outputs.name
    envVars: [
      { name: 'NODE_ENV',          value: 'production' }
      { name: 'AUTH0_SECRET',      secretRef: 'auth0-frontend-secret' }
      { name: 'AUTH0_BASE_URL',    value: environment == 'production'
        ? 'https://app.cogent.ai'
        : 'https://staging.cogent.ai' }
      { name: 'AUTH0_ISSUER_BASE_URL', secretRef: 'auth0-issuer-base-url' }
      { name: 'AUTH0_CLIENT_ID',       secretRef: 'auth0-client-id' }
      { name: 'AUTH0_CLIENT_SECRET',   secretRef: 'auth0-client-secret' }
      { name: 'AUTH0_AUDIENCE',        secretRef: 'auth0-audience' }
      { name: 'AUTH0_WEBHOOK_SECRET',  secretRef: 'auth0-webhook-secret' }
      { name: 'NEXT_PUBLIC_API_URL',   value: environment == 'production'
        ? 'https://api.cogent.ai'
        : 'https://api-staging.cogent.ai' }
      { name: 'BACKEND_URL',          value: 'https://${backend.outputs.fqdn}' }
    ]
    healthProbePath: '/'
    isExternal: true
  }
}

// ── Migration Job ───────────────────────────────────────────────────────────
// One-shot Container Apps Job for running Alembic migrations before deployment.
resource migrateJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${resourcePrefix}-migrate'
  location: location
  properties: {
    environmentId: containerEnv.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 300
      replicaRetryLimit: 1
      secrets: [
        { name: 'database-url', keyVaultUrl: '${keyVault.outputs.vaultUri}secrets/database-url', identity: 'system' }
      ]
      registries: [
        {
          server: acr.outputs.loginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: backendImage
          command: ['alembic', 'upgrade', 'head']
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: [
            { name: 'DATABASE_URL', secretRef: 'database-url' }
          ]
        }
      ]
    }
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────
output backendFqdn string = backend.outputs.fqdn
output frontendFqdn string = frontend.outputs.fqdn
output acrLoginServer string = acr.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output redisHostname string = redis.outputs.hostname
output postgresServerFqdn string = postgres.outputs.serverFqdn
output postgresServerName string = postgres.outputs.serverName
