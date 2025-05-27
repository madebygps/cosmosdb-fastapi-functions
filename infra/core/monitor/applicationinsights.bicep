@description('Name of the Application Insights instance')
param name string


@description('Azure region where the Application Insights will be deployed')
param location string = resourceGroup().location

@description('Tags to apply to the Application Insights')
param tags object = {}

@description('Resource ID of the Log Analytics workspace to connect to')
param logAnalyticsWorkspaceId string

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspaceId
  }
}



output connectionString string = appInsights.properties.ConnectionString
output instrumentationKey string = appInsights.properties.InstrumentationKey
output name string = appInsights.name
