// =============================================================================
// Module: Azure Database for PostgreSQL Flexible Server
// =============================================================================
// Provisions a PostgreSQL Flexible Server with:
//   • SSL enforcement (TLS 1.2+)
//   • pgvector extension enabled
//   • Initial application database created
//   • Configurable SKU (Burstable for staging, GeneralPurpose for production)

@description('Server name (must be globally unique)')
param name string

@description('Azure region')
param location string

@description('Administrator login username')
param administratorLogin string

@description('Administrator login password')
@secure()
param administratorLoginPassword string

@description('Name of the application database to create')
param databaseName string = 'cogent'

@description('PostgreSQL version')
param postgresVersion string = '16'

@description('SKU tier: Burstable | GeneralPurpose | MemoryOptimized')
@allowed(['Burstable', 'GeneralPurpose', 'MemoryOptimized'])
param skuTier string = 'Burstable'

@description('SKU name (e.g. Standard_B2ms, Standard_D4s_v3)')
param skuName string = 'Standard_B2ms'

@description('Storage size in GB')
param storageSizeGB int = 32

@description('Backup retention days')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Enable geo-redundant backups (production only)')
param geoRedundantBackup bool = false

// ── Flexible Server ──────────────────────────────────────────────────────────
resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: postgresVersion
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackup ? 'Enabled' : 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'  // Enable ZoneRedundant in production if desired
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
  }
}

// ── SSL enforcement — require TLS 1.2+ ──────────────────────────────────────
resource sslParam 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'ssl_min_protocol_version'
  properties: {
    value: 'TLSv1.2'
    source: 'user-override'
  }
}

// ── Enable pgvector extension ────────────────────────────────────────────────
resource pgvectorExtension 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'azure.extensions'
  properties: {
    value: 'vector'
    source: 'user-override'
  }
  dependsOn: [sslParam]
}

// ── Application database ─────────────────────────────────────────────────────
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ── Allow Azure services to reach the server ─────────────────────────────────
// For production, replace this with VNet integration or specific IP rules.
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: server
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ── Outputs ──────────────────────────────────────────────────────────────────
output serverFqdn string = server.properties.fullyQualifiedDomainName
output serverName string = server.name
output databaseName string = database.name
