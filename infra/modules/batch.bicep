// Azure Batch — ADF Custom Activity pool + staging storage (account key for ADF compatibility).
targetScope = 'resourceGroup'

@description('Azure region.')
param location string

@description('Batch account name (3–24 lowercase alphanumeric, globally unique).')
param batchAccountName string

@description('Batch pool name.')
param poolName string = 'olist-pool'

@description('Dedicated staging storage for Batch/ADF (shared key enabled).')
param batchStorageAccountName string

@description('ACR login server (e.g. myacr.azurecr.io).')
param acrLoginServer string

@description('Transform container image reference in ACR.')
param transformImageName string = 'olist-transform:latest'

@description('ADF system-assigned MI principal — Contributor on Batch account.')
param dataFactoryPrincipalId string

@description('Main ADLS storage — pool MI gets Blob Data Contributor for transform I/O.')
param lakeStorageAccountId string

@description('Resource tags.')
param tags object = {}

var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: split(acrLoginServer, '.')[0]
}

resource batchStorage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: batchStorageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    isHnsEnabled: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: true
    publicNetworkAccess: 'Enabled'
  }
}

resource batchBlobService 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: batchStorage
  name: 'default'
}

resource batchContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  parent: batchBlobService
  name: 'adf-batch'
  properties: {
    publicAccess: 'None'
  }
}

resource poolIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-olist-batch-pool'
  location: location
  tags: tags
}

resource lakeStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: last(split(lakeStorageAccountId, '/'))
}

resource poolLakeAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(lakeStorage.id, poolIdentity.id, storageBlobDataContributorRoleId)
  scope: lakeStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: poolIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource poolAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, poolIdentity.id, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: poolIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource batchAccount 'Microsoft.Batch/batchAccounts@2024-02-01' = {
  name: batchAccountName
  location: location
  tags: tags
  properties: {
    poolAllocationMode: 'BatchService'
    autoStorage: {
      storageAccountId: batchStorage.id
      authenticationMode: 'StorageKeys'
    }
  }
}

resource adfBatchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(batchAccount.id, dataFactoryPrincipalId, contributorRoleId)
  scope: batchAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: dataFactoryPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource pool 'Microsoft.Batch/batchAccounts/pools@2024-02-01' = {
  parent: batchAccount
  name: poolName
  dependsOn: [
    poolLakeAccess
    poolAcrPull
  ]
  properties: {
    vmSize: 'Standard_D2s_v3'
    taskSlotsPerNode: 1
    taskSchedulingPolicy: {
      nodeFillType: 'Pack'
    }
    deploymentConfiguration: {
      virtualMachineConfiguration: {
        imageReference: {
          publisher: 'microsoft-azure-batch'
          offer: 'ubuntu-server-container'
          sku: '20-04-lts'
          version: 'latest'
        }
        nodeAgentSkuId: 'batch.node.ubuntu 20.04'
        containerConfiguration: {
          type: 'DockerCompatible'
          containerImageNames: [
            '${acrLoginServer}/${transformImageName}'
          ]
          containerRegistries: [
            {
              registryServer: acrLoginServer
              identityReference: {
                resourceId: poolIdentity.id
                clientId: poolIdentity.properties.clientId
              }
            }
          ]
        }
      }
    }
    networkConfiguration: {
      publicIPAddressConfiguration: {
        provision: 'BatchManaged'
      }
    }
    scaleSettings: {
      fixedScale: {
        targetDedicatedNodes: 0
        targetLowPriorityNodes: 1
      }
    }
    identity: {
      type: 'UserAssigned'
      userAssignedIdentities: {
        '${poolIdentity.id}': {}
      }
    }
  }
}

output batchAccountName string = batchAccount.name
output batchAccountUrl string = batchAccount.properties.accountEndpoint
output batchPoolName string = pool.name
output batchStorageAccountName string = batchStorage.name
output acrLoginServer string = acrLoginServer
output transformImageName string = transformImageName
output batchPoolIdentityClientId string = poolIdentity.properties.clientId
