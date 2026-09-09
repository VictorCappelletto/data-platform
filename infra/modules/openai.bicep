// Azure OpenAI — pay-per-token chat + embeddings for Agent Book.
targetScope = 'resourceGroup'

@description('Azure region.')
param location string

@description('Globally unique Cognitive Services account name.')
param accountName string

@description('Custom subdomain (required for Azure OpenAI keys/endpoint).')
param customSubDomainName string

@description('Chat deployment name.')
param chatDeploymentName string = 'gpt-5-mini'

@description('Chat model name.')
param chatModelName string = 'gpt-5-mini'

@description('Chat model version.')
param chatModelVersion string = '2025-08-07'

@description('Embedding deployment name.')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('Embedding model name.')
param embeddingModelName string = 'text-embedding-3-small'

@description('Embedding model version.')
param embeddingModelVersion string = '1'

@description('Resource tags.')
param tags object = {}

resource account 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: 'Enabled'
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: account
  name: chatDeploymentName
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
  }
  sku: {
    name: 'GlobalStandard'
    capacity: 10
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: account
  name: embeddingDeploymentName
  dependsOn: [
    chatDeployment
  ]
  properties: {
    model: {
      format: 'OpenAI'
      name: embeddingModelName
      version: embeddingModelVersion
    }
  }
  sku: {
    name: 'Standard'
    capacity: 50
  }
}

output accountName string = account.name
output endpoint string = account.properties.endpoint
output chatDeploymentName string = chatDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
