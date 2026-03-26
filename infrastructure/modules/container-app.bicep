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
param cpu object

@description('Memory (e.g. 1Gi, 2Gi)')
param memory string

@description('Key Vault name for secret references')
param keyVaultName string

@description('Environment variables array')
param envVars array = []

@description('Health probe path')
param healthProbePath string = '/health'

@description('Whether the app accepts external (internet) traffic')
param isExternal bool = false

@description('Optional Azure Container Registry login server')
param registryServer string = ''

@description('Optional Azure Container Registry name for AcrPull assignment')
param registryName string = ''

var containerAppSecrets = [
  for envVar in envVars: if (contains(envVar, 'secretRef')) {
    name: envVar.secretRef
    keyVaultUrl: 'https://${keyVaultName}.vault.azure.net/secrets/${envVar.secretRef}'
    identity: 'system'
  }
]

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = if (!empty(registryName)) {
  name: registryName
}

// ── Resource ────────────────────────────────────────────────────────────────
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
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
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: image
          resources: {
            cpu: cpu
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

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(registryName)) {
  scope: registry
  name: guid(registryName, containerApp.identity.principalId, 'AcrPull')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
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
        objectId: containerApp.identity.principalId
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
