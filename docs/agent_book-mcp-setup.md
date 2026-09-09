# Agent Book MCP — Cursor

Expõe `agent_book_chat`, `agent_book_ask`, `agent_book_quote`, `agent_book_example`, `agent_book_note` e `agent_book_feedback` no Cursor. O servidor é stdio no app (`apps/agent_book/mcp_server/`), não no SDK. O grafo LangGraph continua sendo o orquestrador: o modelo escolhe a tool, o retrieve do livro não é opcional.

## Pré-requisitos

```bash
pip install -e ".[agent_book]"
```

`.env` na raiz do repo (gitignored) com as chaves Azure. Ver [agent_book-azure-setup.md](./agent_book-azure-setup.md). Manter `PLATFORM_ENV=local`.

O livro precisa já ter sido ingerido (`make agent_book-ingest`).

## Cursor

O projeto já tem `.cursor/mcp.json` (`py -3` no Windows, para o Cursor achar o Python). Carrega `.env` via `envFile` e força:

- `AGENT_BOOK_SEARCH_PROVIDER=azure_search`
- `AGENT_BOOK_LLM_PROVIDER=azure_openai`

Neste PC o servidor também foi registrado em `%USERPROFILE%\.cursor\mcp.json`.

**Settings → MCP → refresh** (ou reiniciar o Cursor). O servidor `agent_book` deve aparecer como connected.

No chat, fala livre funciona (`agent_book_chat`). Tools explícitas também:

```text
Pergunta ao Agent Book: o que é o ciclo de vida da engenharia de dados?
```

```text
Me mostra o trecho do livro sobre data warehouse
```

```text
Gostei, bem objetiva — continua assim
```

## Tools

| Tool | Papel |
|------|--------|
| `agent_book_chat` | interpreta a fala e escolhe ask / note / example / quote / feedback |
| `agent_book_ask` | retrieve → resposta + páginas; `offer_example` |
| `agent_book_quote` | trechos crus (página + texto), sem paráfrase |
| `agent_book_example` | cenário do dia a dia |
| `agent_book_note` | retrieve → claim/evidência no gold |
| `agent_book_feedback` | elogio → perfil de estilo em gold (só positivo) |

Sem as env Azure, ask/note caem no retrieve local e no LLM echo.

Não commitar `.env` nem o TXT do livro.
