metadata description = 'Deploys an Azure Function App with Flex Consumption Plan.'

@description('Name of the App Service Plan')
param planName string

@description('Name of the Function App')
param appName string

@description('Azure region where the resources will be deployed')
param location string = resourceGroup().location

@description('Name of the storage account')
param storageAccountName string

@description('Name of the storage container for function app deployments')
param deploymentStorageContainerName string

@description('Name of Application Insights resource')
param applicationInsightsName string

@description('Tags to apply to all resources')
param tags object = {}
@description('Additional tags to apply only to the Function App resource')
param serviceTag object = {}
@description('Cosmos DB endpoint URL')
param cosmosDbEndpoint string
@description('Cosmos DB database name')
param cosmosDbDatabase string
@description('Products container name in Cosmos DB')
param cosmosDbProductsContainer string

@description('Runtime language for the Function App')
@allowed(['dotnet-isolated', 'python', 'java', 'node', 'powerShell'])
param functionAppRuntime string = 'python'

@description('Runtime version for the Function App')
@allowed(['3.10', '3.11', '7.4', '8.0', '9.0', '10', '11', '17', '20', '21', '22'])
param functionAppRuntimeVersion string = '3.11'

@description('Maximum instance count for the Function App')
@minValue(40)
@maxValue(1000)
param maximumInstanceCount int = 100

@description('Memory allocation per instance in MB')
@allowed([512, 2048, 4096])
param instanceMemoryMB int = 2048

@description('Whether the plan should be zone redundant')
param zoneRedundant bool = false

@description('Whether to skip the storage role assignment creation (useful for redeployments)')
param skipRoleAssignment bool = false

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: storageAccountName
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

resource flexFuncPlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  properties: {
    reserved: true
    zoneRedundant: zoneRedundant
  }
}

resource flexFuncApp 'Microsoft.Web/sites@2024-04-01' = {
  name: appName
  location: location
  tags: union(tags, serviceTag)
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: flexFuncPlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storage.name
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'PYTHON_ENABLE_WORKER_EXTENSIONS'
          value: '1'
        }

        {
          name: 'APPLICATIONINSIGHTS_ENABLE_DEPENDENCY_CORRELATION'
          value: 'true'
        }
        {
          name: 'COSMOSDB_ENDPOINT'
          value: cosmosDbEndpoint
        }
        {
          name: 'COSMOSDB_DATABASE'
          value: cosmosDbDatabase
        }
        {
          name: 'COSMOSDB_CONTAINER_PRODUCTS'
          value: cosmosDbProductsContainer
        }
      ]

    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentStorageContainerName}'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: maximumInstanceCount
        instanceMemoryMB: instanceMemoryMB
      }
      runtime: {
        name: functionAppRuntime
        version: functionAppRuntimeVersion
      }
    }
  }
}

// Blob Data Owner role ID
var storageRoleDefinitionId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'

// Grant Function App access to storage account using managed identity
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!skipRoleAssignment){
  name: guid(storage.id, flexFuncApp.id, storageRoleDefinitionId)
  scope: storage
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageRoleDefinitionId)
    principalId: flexFuncApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output functionAppId string = flexFuncApp.id
output functionAppName string = flexFuncApp.name
output functionAppPrincipalId string = flexFuncApp.identity.principalId
