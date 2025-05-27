targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Environment (from parameters) used for resource naming')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string
@description('Skip storage role assignment (to avoid duplicate errors)')
param skipRoleAssignment bool = true

@description('Resource Group name (if empty, a default will be used)')
param resourceGroupName string = ''

@description('Custom Storage Account name (optional)')
param storageAccountName string = ''

@description('Custom Cosmos DB account name (optional)')
param cosmosAccountName string = ''

@description('Name of the database inside Cosmos DB')
param cosmosDatabaseName string = 'inventory'

// App Insights & Log Analytics (for Function App)
@description('Custom Log Analytics workspace name (optional)')
param logAnalyticsName string = ''
@description('Custom App Insights name (optional)')
param applicationInsightsName string = ''

// User‐assigned identity for the Function App
@description('Optional name for a user‐assigned managed identity')
param apiUserAssignedIdentityName string = ''

var tags = {
  'azd-env-name': name
}
var token = uniqueString(subscription().id, name, location)
var prefix = '${name}-${token}'

// ───────────────────────────
// Resource Group
// ───────────────────────────
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: empty(resourceGroupName) ? '${prefix}-rg' : resourceGroupName
  location: location
  tags: tags
}

// ───────────────────────────
// Cosmos DB (serverless + 3 containers)
// ───────────────────────────
module cosmosDb 'core/database/cosmos-db.bicep' = {
  name: 'cosmosDb'
  scope: rg
  params: {
    name: empty(cosmosAccountName) ? '${prefix}-cosmos' : cosmosAccountName
    location: location
    tags: tags
    databaseName: cosmosDatabaseName
    // productsContainerName, locationsContainerName, inventoryItemsContainerName,
    // and partition paths come from defaults in the module
  }
}

// ───────────────────────────
// Storage (for Functions + deployment artifacts)
// ───────────────────────────
module storageAccount 'core/storage/storage-account.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    name: empty(storageAccountName) ? '${toLower(take(replace(prefix, '-', ''), 17))}storage' : storageAccountName
    location: location
    tags: tags
    containers: [
      { name: 'function-deployments' }
    ]
  }
}


// ───────────────────────────
// Monitoring (Log Analytics + App Insights)
// ───────────────────────────
module logAnalytics 'core/monitor/loganalytics.bicep' = {
  name: 'logAnalytics'
  scope: rg
  params: {
    name: empty(logAnalyticsName) ? '${prefix}-la' : logAnalyticsName
    location: location
    tags: tags
  }
}

module appInsights 'core/monitor/applicationinsights.bicep' = {
  name: 'appInsights'
  scope: rg
  params: {
    name: empty(applicationInsightsName) ? '${prefix}-ai' : applicationInsightsName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.id
  }
}

// ───────────────────────────
// User‐assigned Identity for the Function App
// ───────────────────────────
module userIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'userIdentity'
  scope: rg
  params: {
    name: empty(apiUserAssignedIdentityName) ? '${prefix}-ui' : apiUserAssignedIdentityName
    location: location
    tags: tags
  }
}


// ───────────────────────────
// Function App
// ───────────────────────────
module functionApp 'core/host/functions.bicep' = {
  name: 'functionApp'
  scope: rg
    params: {
      planName: '${prefix}-plan'
      appName: '${prefix}-func'
      location: location
      tags: tags
      serviceTag: { 'azd-service-name': 'api' }
      storageAccountName: storageAccount.outputs.name
      deploymentStorageContainerName: 'function-deployments'
      applicationInsightsName: appInsights.outputs.name
      skipRoleAssignment: false
      functionAppRuntime: 'python'
      functionAppRuntimeVersion: '3.11'
      maximumInstanceCount: 100
      instanceMemoryMB: 2048
      cosmosDbEndpoint: cosmosDb.outputs.cosmosEndpoint
      cosmosDbDatabase: cosmosDb.outputs.cosmosDatabaseName
      cosmosDbProductsContainer: cosmosDb.outputs.productsContainerName
    }
}

// ───────────────────────────
// Role assignments
// ───────────────────────────
// Give the Function App identity access to Cosmos DB (data & control plane)
module cosmosDataRole 'core/database/cosmos-db-data-plane-role.bicep' = {
  name: 'cosmosDataRole'
  scope: rg
  params: {
    principalId: functionApp.outputs.functionAppPrincipalId
    cosmosAccountName: cosmosDb.outputs.cosmosAccountName
    roleType: 'contributor'
  }
}

module cosmosControlRole 'core/database/cosmos-db-control-plane-role.bicep' = {
  name: 'cosmosControlRole'
  scope: rg
  params: {
    identityId: functionApp.outputs.functionAppPrincipalId
    cosmosAccountName: cosmosDb.outputs.cosmosAccountName
  }
}

// Attach Storage Blob Data Owner role to the Function App via module
module blobRoleAssign 'core/storage/blob-role-assignment.bicep' = if (!skipRoleAssignment) {
  name: 'blobRoleAssign'
  scope: rg
  params: {
    principalId: functionApp.outputs.functionAppPrincipalId
    storageAccountName: storageAccount.outputs.name
    roleDefinitionId: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
  }
}



// ───────────────────────────
// Outputs
// ───────────────────────────
output resourceGroupId string = rg.id
output functionAppName string = functionApp.outputs.functionAppName
output functionAppEndpoint string = 'https://${functionApp.outputs.functionAppName}.azurewebsites.net'
output cosmosDbEndpoint string = cosmosDb.outputs.cosmosEndpoint
output cosmosDatabaseName string = cosmosDb.outputs.cosmosDatabaseName
output storageAccountName string = storageAccount.outputs.name
output appInsightsConnectionString string = appInsights.outputs.connectionString
