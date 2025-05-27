@description('Principal ID to assign the role to')
param principalId string

@description('Storage account name to assign role on')
param storageAccountName string

@description('Role definition ID to assign')
param roleDefinitionId string = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' // Storage Blob Data Owner by default

// Reference the storage account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

// Create role assignment
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, roleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: principalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalType: 'ServicePrincipal'
  }
}

output roleAssignmentId string = roleAssignment.id
