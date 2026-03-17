// =============================================================================
// Module: Azure Cache for Redis
// =============================================================================

@description('Redis cache name')
param name string

@description('Azure region')
param location string

@description('SKU tier')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

@description('Cache capacity (0–6 for Basic/Standard, 1–5 for Premium)')
@minValue(0)
@maxValue(6)
param capacity int = 0

@description('Allow non-SSL connections (should be false in production)')
param enableNonSslPort bool = false

resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: name
  location: location
  properties: {
    sku: {
      name: sku
      family: sku == 'Premium' ? 'P' : 'C'
      capacity: capacity
    }
    enableNonSslPort: enableNonSslPort
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
      'maxmemory-reserved': '50'
    }
  }
}

output hostname string = redis.properties.hostName
output sslPort int = redis.properties.sslPort
output name string = redis.name
// Connection string should be read from Key Vault, not from outputs.
// Store it manually or via a deployment script:
//   az redis list-keys --name <name> --resource-group <rg>
