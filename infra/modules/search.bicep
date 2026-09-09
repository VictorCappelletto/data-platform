// Azure AI Search — Agent Book knowledge retrieval (Databricks Vector Search stand-in).
targetScope = 'resourceGroup'

@description('Azure region.')
param location string

@description('Globally unique search service name (lowercase alphanumeric, 2–60).')
param searchServiceName string

@description('SKU. free = one per subscription; basic ≈ US$ 75/month.')
@allowed([
  'free'
  'basic'
])
param sku string = 'free'

@description('Resource tags.')
param tags object = {}

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: sku
  }
  properties: {
    replicaCount: sku == 'free' ? 1 : 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

output searchServiceName string = search.name
output searchEndpoint string = 'https://${search.name}.search.windows.net'
