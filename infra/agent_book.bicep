// Agent Book AI stack — deploy into existing rg-olist-dev. Does not touch ADF/SQL.
targetScope = 'resourceGroup'

@description('Azure region (same as Olist storage).')
param location string = 'eastus'

@description('Globally unique OpenAI account name (leave empty to generate).')
param openaiAccountName string = ''

@description('Globally unique AI Search name (leave empty to generate).')
param searchServiceName string = ''

@description('AI Search SKU.')
@allowed([
  'free'
  'basic'
])
param searchSku string = 'free'

@description('Resource tags.')
param tags object = {
  project: 'agent_book'
  environment: 'dev'
  purpose: 'portfolio'
  'managed-by': 'bicep'
}

var uniqueSuffix = take(uniqueString(resourceGroup().id, location, 'agent_book'), 8)
var resolvedOpenaiName = empty(openaiAccountName) ? 'oai-agentbook${uniqueSuffix}' : openaiAccountName
var resolvedSearchName = empty(searchServiceName) ? 'srchagentbook${uniqueSuffix}' : searchServiceName

module openai 'modules/openai.bicep' = {
  name: 'agent-book-openai'
  params: {
    location: location
    accountName: resolvedOpenaiName
    customSubDomainName: resolvedOpenaiName
    tags: tags
  }
}

module search 'modules/search.bicep' = {
  name: 'agent-book-search'
  params: {
    location: location
    searchServiceName: resolvedSearchName
    sku: searchSku
    tags: tags
  }
}

output openaiAccountName string = openai.outputs.accountName
output openaiEndpoint string = openai.outputs.endpoint
output openaiChatDeployment string = openai.outputs.chatDeploymentName
output openaiEmbeddingDeployment string = openai.outputs.embeddingDeploymentName
output searchServiceName string = search.outputs.searchServiceName
output searchEndpoint string = search.outputs.searchEndpoint
