// =============================================================================
// Module: Azure Key Vault
// =============================================================================
// Central secret store. Container Apps reference secrets via Key Vault URIs
// with managed identity access.

@description('Key Vault name (must be globally unique)')
param name string

@description('Azure region')
param location string

@description('Optional extra access policies to apply at vault creation time')
param additionalAccessPolicies array = []

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: additionalAccessPolicies
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true     // Prevent accidental permanent deletion
    enableRbacAuthorization: false  // Using access policies (simpler for Container Apps)
    networkAcls: {
      defaultAction: 'Allow'        // Restrict to VNet in production if desired
      bypass: 'AzureServices'
    }
  }
}

output name string = kv.name
output vaultUri string = kv.properties.vaultUri
