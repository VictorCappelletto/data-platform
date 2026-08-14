# Azure MCP + CLI — setup para `ingestion_azure`

Permite que o agente no Cursor crie e gerencie recursos Azure (Storage, Data Factory, Resource Groups, etc.) usando suas credenciais locais após `az login`.

Documentação oficial: [Azure MCP Server — Cursor](https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started/tools/cursor)

## 1. Pré-requisitos

| Item | Status |
|------|--------|
| Conta Azure + subscription | Você precisa criar/ativar |
| Node.js LTS | Para o MCP (`npx @azure/mcp`) |
| Azure CLI | `winget install Microsoft.AzureCLI` |
| Cursor MCP | Configurado em `~/.cursor/mcp.json` |

## 2. MCP no Cursor

Já adicionado em `%USERPROFILE%\.cursor\mcp.json`:

```json
"azure-mcp": {
  "command": "npx",
  "args": ["-y", "@azure/mcp@latest", "server", "start"]
}
```

**Reinicie o Cursor** (ou Settings → MCP → refresh) para carregar o servidor.

## 3. Login Azure (obrigatório — você faz uma vez)

```powershell
az login
az account show
az account list --output table
```

Opcional — fixar subscription:

```powershell
az account set --subscription "Nome ou ID da subscription"
```

O Azure MCP **reutiliza** as credenciais do `az login` — não precisa de API key separada no MCP.

## 4. Permissões recomendadas (Olist pipeline)

Para criar RG + Storage (ADLS) + Data Factory:

| Role | Escopo |
|------|--------|
| **Contributor** | Resource Group `rg-olist-dev` |
| **Storage Blob Data Contributor** | Storage account (ADLS) |

Conta gratuita / créditos: [Azure account](https://azure.microsoft.com/pricing/purchase-options/azure-account)

## 5. Testar no chat do Cursor

Após reiniciar o Cursor e `az login`:

```text
List my Azure resource groups
```

ou

```text
List storage accounts in my subscription
```

## 6. Infra criada / próximos passos

Resource Group **`rg-olist-dev`** (eastus) já existe. Guia completo: [azure-infra-setup.md](./azure-infra-setup.md).

Ordem recomendada:

1. ✅ Resource Group
2. GitHub OIDC (3 secrets, sem client secret)
3. Storage ADLS Gen2 (LRS, mínimo)
4. Data Factory + Self-hosted IR (SQL local)

## 7. O que o agente poderá fazer depois

- Deploy Bicep via GitHub Actions
- Storage Account com hierarchical namespace (ADLS Gen2)
- Containers `landing`, `processing`, `curated`
- Azure Data Factory
- Listar / inspecionar recursos existentes

## 7. SQL Server local + ADF

O SQL Server Docker (`localhost:1433`) **não é acessível diretamente** pelo ADF na nuvem. Opções:

1. **Self-hosted Integration Runtime** na sua máquina (recomendado para dev)
2. **Azure SQL Database** na nuvem
3. Pipeline local Python (`ingestion_azure`) enquanto IR não estiver pronto

## Troubleshooting

| Problema | Solução |
|----------|---------|
| MCP não aparece | Reiniciar Cursor; verificar Node.js |
| "Not authenticated" | Rodar `az login` no terminal |
| `az` não encontrado | Reiniciar terminal após `winget install Microsoft.AzureCLI` |
| MCP lento no start | Pin version: `@azure/mcp@2.0.0-beta.13` em vez de `@latest` |
