// =============================================================================
// Module: Container App
// =============================================================================

@description('Container App name')
param name string

@description('Azure region')
param location string

@description('Container Apps Environment resource ID')
param environmentId string

@description('Container image (full path incl. tag)')
param image string

@description('Port the container listens on')
param targetPort int

@description('Minimum replica count')
param minReplicas int = 1

@description('Maximum replica count')
param maxReplicas int = 3

@description('CPU cores (e.g. 0.5, 1.0)')
param cpu string

@description('Memory (e.g. 1Gi, 2Gi)')
param memory string

@description('Key Vault name for secret references')
param keyVaultName string

@description('Environment variables array')
param envVars array = []

@description('Key Vault secret names that should be exposed to the container app')
param secrets array = []

@description('Health probe path')
param healthProbePath string = '/health'

@description('Whether the app accepts external (internet) traffic')
param isExternal bool = false

@description('Optional Azure Container Registry login server')
param registryServer string = ''

@description('Optional Azure Container Registry name for AcrPull assignment')
param registryName string = ''

@description('Optional user-assigned identity resource ID to use for ACR pulls')
param registryIdentityResourceId string = ''

var containerAppSecrets = [
  for secretName in secrets: {
    name: secretName
    keyVaultUrl: 'https://${keyVaultName}.vault.azure.net/secrets/${secretName}'
    identity: empty(registryIdentityResourceId) ? 'system' : registryIdentityResourceId
  }
]

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = if (!empty(registryName)) {
  name: registryName
}

// ── Resource ────────────────────────────────────────────────────────────────
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: empty(registryIdentityResourceId)
    ? {
        type: 'SystemAssigned'
      }
    : {
        type: 'SystemAssigned,UserAssigned'
        userAssignedIdentities: {
          '${registryIdentityResourceId}': {}
        }
      }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: containerAppSecrets
      ingress: {
        external: isExternal
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
      registries: empty(registryServer) ? [] : [
        {
          server: registryServer
          identity: empty(registryIdentityResourceId) ? 'system' : registryIdentityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: envVars
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: healthProbePath
                port: targetPort
              }
              initialDelaySeconds: 15
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: healthProbePath
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
            {
              type: 'Startup'
              httpGet: {
                path: healthProbePath
                port: targetPort
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// ── Key Vault Access ────────────────────────────────────────────────────────
// Grant the Container App's managed identity GET access to Key Vault secrets.
resource kvAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: '${keyVaultName}/add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: empty(registryIdentityResourceId)
          ? containerApp.identity.principalId
          : reference(registryIdentityResourceId, '2023-01-31').principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}

// ── Outputs ─────────────────────────────────────────────────────────────────
output fqdn string = containerApp.properties.configuration.ingress.fqdn
output principalId string = containerApp.identity.principalId
