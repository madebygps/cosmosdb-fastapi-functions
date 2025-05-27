@description('Principal ID to assign the role to')
param principalId string

@description('Name of the Cosmos DB account')
param cosmosAccountName string

// Define the built-in data plane role IDs for Cosmos DB
// These are standard GUIDs for SQL API roles
var cosmosDataRoleIds = {
  'Cosmos DB Built-in Data Reader': '00000000-0000-0000-0000-000000000001'
  'Cosmos DB Built-in Data Contributor': '00000000-0000-0000-0000-000000000002'
}

@description('Role to assign: contributor or reader')
@allowed([
  'contributor'
  'reader'
])
param roleType string = 'contributor'

// Map friendly role type to CosmosDB SQL role definition ID
var roleDefinitionId = roleType == 'contributor' ? cosmosDataRoleIds['Cosmos DB Built-in Data Contributor'] : cosmosDataRoleIds['Cosmos DB Built-in Data Reader']

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosAccountName
}

// Format the role definition ID with the proper path structure
var fullRoleDefinitionId = '${cosmosDbAccount.id}/sqlRoleDefinitions/${roleDefinitionId}'

resource dataPlaneRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  name: guid(cosmosDbAccount.id, principalId, roleDefinitionId)
  parent: cosmosDbAccount
  properties: {
    principalId: principalId
    roleDefinitionId: fullRoleDefinitionId
    scope: cosmosDbAccount.id
  }
}

output roleAssignmentId string = dataPlaneRoleAssignment.id
