// Azure Container Registry — Olist transform image (Custom Activity).
targetScope = 'resourceGroup'

@description('Azure region.')
param location string

@description('ACR name (5–50 alphanumeric, globally unique).')
param acrName string

@description('Resource tags.')
param tags object = {}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
output acrId string = acr.id
