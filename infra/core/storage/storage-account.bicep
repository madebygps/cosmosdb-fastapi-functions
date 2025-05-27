@description('Name of the storage account')
param name string

@description('Azure region where the storage account will be deployed')
param location string = resourceGroup().location

@description('Tags to apply to the storage account')
param tags object = {}

@description('Access tier for the storage account')
@allowed([
  'Hot'
  'Cool'
  'Premium'
])
param accessTier string = 'Hot'

@description('Allow or disallow public access to all blobs or containers in the storage account')
param allowBlobPublicAccess bool = false

@description('Allow or disallow cross-tenant replication of data in the storage account')
param allowCrossTenantReplication bool = true

@description('Allow or disallow shared key access to the storage account')
param allowSharedKeyAccess bool = true // This should be true to allow key-based access

@description('Array of container configurations to create in the storage account')
param containers array = []

@description('Use OAuth authentication as the default when accessing the storage account')
param defaultToOAuthAuthentication bool = false

@description('Type of storage account')
param kind string = 'StorageV2'

@description('The minimum TLS version to be permitted on requests to storage')
param minimumTlsVersion string = 'TLS1_2'

@description('SKU configuration for the storage account')
param sku object = { name: 'Standard_LRS' }

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: sku
  properties: {
    accessTier: accessTier
    allowBlobPublicAccess: allowBlobPublicAccess
    allowCrossTenantReplication: allowCrossTenantReplication
    allowSharedKeyAccess: allowSharedKeyAccess // Explicitly use parameter value
    defaultToOAuthAuthentication: defaultToOAuthAuthentication // Explicitly use parameter value
    minimumTlsVersion: minimumTlsVersion
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = if (!empty(containers)) {
  parent: storageAccount
  name: 'default'
  properties: {}
}

resource containerResource 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for container in containers: {
  parent: blobServices
  name: container.name
  properties: {
    publicAccess: container.?publicAccess ?? 'None'
  }
}]

output name string = storageAccount.name
output primaryEndpoints object = storageAccount.properties.primaryEndpoints
