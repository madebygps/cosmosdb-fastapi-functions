@description('Name of the Cosmos DB account')
param name string

@description('Azure region where the Cosmos DB account will be deployed')
param location string = resourceGroup().location

@description('Tags to apply to the Cosmos DB account')
param tags object = {}

@description('Name of the database to create in the Cosmos DB account')
param databaseName string

@description('Name of the products container')
param productsContainerName string = 'products'
@description('Path used for products partition key')
param productsPartitionKeyPath string = '/category'


resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: name
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location  // Changed from location to locationName
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  name: databaseName
  parent: cosmosDbAccount
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Products container
resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: productsContainerName
  parent: cosmosDatabase
  properties: {
    resource: {
      id: productsContainerName
      partitionKey: {
        paths: [
          productsPartitionKeyPath
        ]
        kind: 'Hash'
      }
      uniqueKeyPolicy: {
        uniqueKeys: [
          {
            paths: [
              '/sku'
            ]
          }
        ]
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [  
          { path: '/sku/?' }
          { path: '/name/?' }
          { path: '/category/?' }
          { path: '/status/?' }
        ]
        excludedPaths: [
          { path: '/*' }
        ]
      }
   }
 }
}
  


output cosmosEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDatabaseName string = cosmosDatabase.name
output cosmosAccountId string = cosmosDbAccount.id
output cosmosAccountName string = cosmosDbAccount.name
output productsContainerName string = productsContainer.name
