// ADLS Gen2 — minimal cost (Standard_LRS, Hot). Portfolio Olist lake zones.
targetScope = 'resourceGroup'

@description('Azure region.')
param location string

@description('Storage account name (3–24 lowercase alphanumeric, globally unique).')
param storageAccountName string

@description('Medallion / pipeline containers (filesystems).')
param containerNames array = [
  'landing'
  'processing'
  'curated'
]

@description('Resource tags.')
param tags object = {}

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storage
  name: 'default'
}

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = [for name in containerNames: {
  parent: blobService
  name: name
  properties: {
    publicAccess: 'None'
  }
}]

output storageAccountName string = storage.name
output storageAccountId string = storage.id
output primaryEndpoints object = storage.properties.primaryEndpoints
output containerNames array = containerNames
output adlsEndpoint string = storage.properties.primaryEndpoints.dfs
