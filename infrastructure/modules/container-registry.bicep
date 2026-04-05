// =============================================================================
// Module: Azure Container Registry
// =============================================================================

@description('ACR name (must be globally unique, alphanumeric only)')
param name string

@description('Azure region')
param location string

@description('SKU tier')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  sku: { name: sku }
  properties: {
    adminUserEnabled: false      // Use managed identity, not admin credentials
    publicNetworkAccess: 'Enabled'
    policies: sku == 'Premium'
      ? {
          retentionPolicy: {
            status: 'enabled'
            days: 30
          }
        }
      : {}
  }
}

output loginServer string = acr.properties.loginServer
output name string = acr.name
