@description('Azure region for all resources.')
param location string

@description('Base name for the Container Apps environment.')
param environmentName string

@description('Name for the Container App that will host the MCP server.')
param containerAppName string

@description('Fully qualified container image reference (e.g., ghcr.io/org/workday-mcp:latest).')
param containerImage string

@description('Container registry server hostname (e.g., myregistry.azurecr.io).')
param containerRegistryServer string

@description('Minimum number of container replicas.')
@minValue(0)
param minReplicas int = 1

@description('Maximum number of container replicas.')
@minValue(1)
param maxReplicas int = 2

@description('Array of environment variables (non-secret) for the container.')
param envVars array = []

var logAnalyticsName = '${environmentName}-law'
var containerEnvName = '${environmentName}-cae'
var publicEnvVars = [for item in envVars: {
  name: item.name
  value: item.value
}]

resource managedEnv 'Microsoft.App/managedEnvironments@2024-02-02-preview' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logWorkspace.properties.customerId
        sharedKey: logWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${containerAppName}-id'
  location: location
}

resource containerApp 'Microsoft.App/containerApps@2024-02-02-preview' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        traffic: [
          {
            weight: 100
            latestRevision: true
          }
        ]
      }
      registries: [
        {
          server: containerRegistryServer
          identity: userIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          image: containerImage
          name: 'workday-mcp'
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: publicEnvVars
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            custom: {
              type: 'http'
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

output containerAppUri string = containerApp.properties.configuration.ingress.fqdn
output managedIdentityClientId string = userIdentity.properties.clientId
