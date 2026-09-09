using '../main.bicep'

param resourceGroupName = 'rg-olist-dev'
param location = 'eastus'

// Leave empty to auto-generate: stolist + unique hash (globally unique)
param storageAccountName = ''

// Leave empty to auto-generate: adf-olist + unique hash (globally unique)
param dataFactoryName = ''

param containerNames = [
  'landing'
  'processing'
  'curated'
]
