// Portfolio Olist pipeline — minimal-cost baseline.
// Deploy: az deployment sub create -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam sqlAdminPassword=$MSSQL_SA_PASSWORD

targetScope = 'subscription'

@description('Resource group name for all Olist/Azure dev resources.')
param resourceGroupName string = 'rg-olist-dev'

@description('Primary region (eastus = lower cost for portfolio workloads).')
param location string = 'eastus'

@description('Azure SQL region (use eastus2 if eastus SQL provisioning is restricted on the subscription).')
param sqlLocation string = 'eastus2'

@description('Globally unique storage account name (auto-generated if empty).')
param storageAccountName string = ''

@description('Globally unique Data Factory name (auto-generated if empty).')
param dataFactoryName string = ''

@description('Globally unique Azure SQL server name (auto-generated if empty).')
param sqlServerName string = ''

@description('Azure SQL administrator login.')
param sqlAdminLogin string = 'olistadmin'

@secure()
@description('Azure SQL administrator password.')
param sqlAdminPassword string

@description('ADLS Gen2 container names (lake zones).')
param containerNames array = [
  'landing'
  'processing'
  'curated'
]

@description('Tags applied to all resources.')
param tags object = {
  project: 'olist'
  environment: 'dev'
  purpose: 'portfolio'
  'managed-by': 'github-actions'
}

var resolvedStorageAccountName = empty(storageAccountName)
  ? 'stolist${take(uniqueString(subscription().subscriptionId, resourceGroupName, location), 13)}'
  : storageAccountName

var resolvedDataFactoryName = empty(dataFactoryName)
  ? 'adf-olist${take(uniqueString(subscription().subscriptionId, resourceGroupName, location, 'adf'), 8)}'
  : dataFactoryName

var resolvedSqlServerName = empty(sqlServerName)
  ? 'sql-olist${take(uniqueString(subscription().subscriptionId, resourceGroupName, location, 'sql'), 8)}'
  : sqlServerName

resource rg 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module storage 'modules/storage.bicep' = {
  name: 'storage-adls'
  scope: rg
  params: {
    location: location
    tags: tags
    storageAccountName: resolvedStorageAccountName
    containerNames: containerNames
  }
}

module datafactory 'modules/datafactory.bicep' = {
  name: 'datafactory-olist'
  scope: rg
  params: {
    location: location
    tags: tags
    dataFactoryName: resolvedDataFactoryName
    storageAccountName: storage.outputs.storageAccountName
  }
}

module sql 'modules/sql.bicep' = {
  name: 'sql-olist'
  scope: rg
  params: {
    location: sqlLocation
    tags: tags
    sqlServerName: resolvedSqlServerName
    sqlAdminLogin: sqlAdminLogin
    sqlAdminPassword: sqlAdminPassword
  }
}

output resourceGroupName string = rg.name
output resourceGroupId string = rg.id
output location string = rg.location
output storageAccountName string = storage.outputs.storageAccountName
output storageAccountId string = storage.outputs.storageAccountId
output adlsEndpoint string = storage.outputs.adlsEndpoint
output containerNames array = storage.outputs.containerNames
output dataFactoryName string = datafactory.outputs.dataFactoryName
output dataFactoryId string = datafactory.outputs.dataFactoryId
output sqlServerName string = sql.outputs.sqlServerName
output sqlServerFqdn string = sql.outputs.sqlServerFqdn
output sqlAdminLogin string = sql.outputs.sqlAdminLogin
output olistDatabaseName string = sql.outputs.olistDatabaseName
output olistDwDatabaseName string = sql.outputs.olistDwDatabaseName
