# Agent Book on Azure — Vector Search

O lake local continua a fonte de verdade. Em `PLATFORM_ENV=dev` o ingest **também** gera embeddings e faz upsert no Azure AI Search (HNSW). O ask usa **hybrid** (texto + vetor) — o papel do Databricks Vector Search no projeto original.

## Recursos (Bicep)

`infra/agent_book.bicep` no `rg-olist-dev`: Azure OpenAI (`gpt-5-mini` + `text-embedding-3-small`) e AI Search.

```powershell
az deployment group create -g rg-olist-dev -f infra/agent_book.bicep -p infra/parameters/agent_book.dev.bicepparam
```

Se o SKU `free` do Search falhar, use `searchSku=basic` no param.

## Env

| Variável | Uso |
|----------|-----|
| `AZURE_OPENAI_ENDPOINT` | chat + embedding |
| `AZURE_OPENAI_API_KEY` | idem |
| `AZURE_SEARCH_ENDPOINT` | `https://<name>.search.windows.net` |
| `AZURE_SEARCH_API_KEY` | admin key |
| `AGENT_BOOK_SEARCH_PROVIDER` | `azure_search` (lake continua `local`) |
| `AGENT_BOOK_LLM_PROVIDER` | `azure_openai` — `ask` e `note` usam `gpt-5-mini` |
| `AGENT_BOOK_BOOK_PATH` | TXT do livro (gitignore) |

```powershell
$env:PLATFORM_ENV = "local"
$env:AGENT_BOOK_SEARCH_PROVIDER = "azure_search"
$env:AGENT_BOOK_LLM_PROVIDER = "azure_openai"
python apps/agent_book/workflows/runs/ingest.py
python apps/agent_book/workflows/runs/agent.py ask --question "O que e o ciclo de vida da engenharia de dados?"
```

Índice: `agent_book-knowledge` (campo `text_vector`, 1536 dims, cosine/HNSW). Sem as env, ingest e ask caem no retrieve local.

Ask/note rodam num LangGraph no agente (`apps/agent_book/agent/agent_book.py`): expand → retrieve → ask | note | uncovered. O grafo não entra no SDK.

Cursor: [agent_book-mcp-setup.md](./agent_book-mcp-setup.md) (`agent_book_ask` / `agent_book_note`).

## Eval no modelo (GitHub Actions)

O job `agent-book-eval` roda o golden set contra `gpt-5-mini`. Login é OIDC (mesmos secrets de `azure-infra`: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`). A action lista a conta OpenAI em `rg-olist-dev` e puxa endpoint + key — não grava a key no GitHub.

Dispara: nightly 11:00 UTC, push em `apps/agent_book/**`, ou **Actions → agent-book-eval → Run workflow**.

O CI `ci.yml` continua só echo/fixture (grátis). A principal precisa de `Cognitive Services OpenAI Contributor` (ou equivalente) no app registration do OIDC para `az ... keys list`.

Local: `make agent_book-eval`.

Livro: não commitar o TXT.
