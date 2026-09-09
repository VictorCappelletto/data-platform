using '../main.bicep'

param resourceGroupName = 'rg-olist-dev'
param location = 'eastus'
param storageAccountName = ''
param dataFactoryName = ''
param sqlServerName = ''
param sqlAdminLogin = 'olistadmin'
// Pass at deploy: sqlAdminPassword=$MSSQL_SA_PASSWORD

param containerNames = [
  'landing'
  'processing'
  'curated'
]
