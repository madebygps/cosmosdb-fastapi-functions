metadata description = 'Assign RBAC role for control plane access to Azure Cosmos DB.'

@description('Id of the role definition to assign to the targeted principal in the context of the account.')
param roleDefinitionId string = '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/230815da-be43-4aae-9cb4-875f7bd000aa' // Cosmos DB Operator role

@description('Id of the identity/principal to assign this role in the context of the account.')
param identityId string

@description('Name of the Cosmos DB account')
param cosmosAccountName string

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosAccountName
}

resource controlPlaneRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cosmosDbAccount.id, roleDefinitionId, identityId)
  scope: cosmosDbAccount
  properties: {
    roleDefinitionId: roleDefinitionId
    principalId: identityId
    principalType: 'ServicePrincipal'
  }
}

output roleAssignmentId string = controlPlaneRoleAssignment.id
