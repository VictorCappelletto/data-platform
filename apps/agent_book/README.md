# agent_book

Agente **Agent Book** — interpreta *Fundamentos de Engenharia de Dados* (Reis/Housley).  
Pergunta → trechos do livro → resposta com página. Depois: nota estruturada no lake.

O TXT do livro fica em `seeds/` (gitignore). Testes usam um fixture de 3 páginas, não o livro.

---

## Fluxo

```text
seeds/*.txt
        │
        ▼  knowledge ingest
bronze/knowledge/chunks
        │
        ├─ local: keyword retrieve
        └─ Azure: embedding → AI Search (hybrid)
        │
        ▼  LangGraph: [route] → expand → retrieve → ask | note | example | quote | uncovered
        ├─► ask  → resposta + citações
        ├─► example → cenário do dia a dia
        ├─► quote → trechos crus (página + texto)
        ├─► note → gold/agent/notes
        └─► feedback → perfil em gold/agent/profile (só elogio)
```

Chunking: **não atravessa página**. Retrieve em `dev`: **vector + texto (hybrid)** no Azure AI Search — equivalente ao Vector Search do Databricks. Local continua keyword (testes sem cloud).

---

## Quick start

Coloque o TXT em `apps/agent_book/seeds/fundamentos-de-engenharia-de-dados.txt`  
ou `AGENT_BOOK_BOOK_PATH` para o download.

```bash
pytest apps/agent_book/tests -q
python apps/agent_book/workflows/runs/ingest.py
python apps/agent_book/workflows/runs/agent.py ask --question "O que e o ciclo de vida da engenharia de dados?"
python apps/agent_book/workflows/runs/agent.py note --topic "data warehouse"
python apps/agent_book/workflows/runs/agent.py example --topic "data warehouse"
```

`make agent_book-ingest` · `make agent_book-ask QUESTION="..."` · `make agent_book-note TOPIC="..."` · `make agent_book-example TOPIC="..."` · `make agent_book-quote QUERY="..."` · `make agent_book-chat MESSAGE="..."`

Ask local usa echo (trechos). Com `AGENT_BOOK_LLM_PROVIDER=azure_openai` o `gpt-5-mini` sintetiza o `ask`, o `example` e o `note`. `agent_book_chat` escolhe a tool a partir da fala livre; o retrieve continua obrigatório nas tools do livro. Feedback positivo grava um perfil de estilo no gold (não é fine-tune).

Ingest é explícito (`make agent_book-ingest`) — o retrieve não dispara ingest sozinho. Prompts versionados em `config/agent/templates/prompts.yml` (`prompt_id` / `prompt_sha` no resultado). Último turn grava trace em `gold/agent/trace`. Eval do fixture no CI: `evals/golden.yml`. Eval no modelo: GitHub Action `agent-book-eval` (OIDC, nightly) ou `make agent_book-eval` local.

MCP no Cursor: [docs/agent_book-mcp-setup.md](../../docs/agent_book-mcp-setup.md) — `agent_book_chat`, `agent_book_ask`, `agent_book_quote`, `agent_book_example`, `agent_book_note`, `agent_book_feedback`.

Se o trecho não estiver nos chunks, o Agent Book responde que o livro não cobre o assunto.

---

## Princípios

config over code · orchestrator fino · livro fora do git · cloud é connector opcional
