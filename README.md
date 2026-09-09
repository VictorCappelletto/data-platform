# data-platform

Portfólio de **Engenharia de Dados** — monorepo com SDK compartilhado, pipelines independentes e um agente Agent Book que demonstra design de plataforma, medallion lakehouse, Azure e LLMOps enxuto.

**Victor Cappelletto** · [GitHub](https://github.com/VictorCappelletto)

---

## Propósito

Mostrar capacidade de **construir plataforma reutilizável**, não scripts isolados:

| Projeto | O que prova |
|---------|-------------|
| [medalion_ingestion_project](apps/medalion_ingestion_project/) | Medallion end-to-end, DQ, volume, config-driven — **local, zero custo cloud** |
| [ingestion_azure](apps/ingestion_azure/) | Pipeline Olist em Azure (ADF, ADLS, Bicep, CI) — **cloud real** |
| [agent_book](apps/agent_book/) | Agente RAG no livro *Fundamentos de Engenharia de Dados* — **local** |

Os apps compartilham `dataplatform/` (config, lake, bootstrap, Airflow factory) e o mesmo layout por processo.

---

## Stack

Python 3.10+ · YAML · Airflow · Azure (ADF, ADLS Gen2, Bicep, OpenAI) · SQL Server · PySpark · LangGraph · MCP · pytest · ruff

---

## Quick start

```bash
pip install -e ".[dev]"
pytest apps/medalion_ingestion_project/tests -q   # 31
pytest apps/ingestion_azure/tests -q                # 17
pytest apps/agent_book/tests -q                           # agent_book
```

```bash
make demo              # medallion — amostra
make demo-bulk         # medallion — ~10k orders + ~11k breweries
make azure-olist-full      # ADF end-to-end (landing → transform → publish)
make agent_book-ingest
make agent_book-ask QUESTION="O que e o ciclo de vida da engenharia de dados?"
make agent_book-note TOPIC="data warehouse"
```

---

## Documentação

| Recurso | Conteúdo |
|---------|----------|
| [medalion_ingestion_project/README.md](apps/medalion_ingestion_project/README.md) | Pipeline medallion — técnico |
| [ingestion_azure/README.md](apps/ingestion_azure/README.md) | Pipeline Olist Azure — técnico |
| [agent_book/README.md](apps/agent_book/README.md) | Agente Agent Book — Q&A e notas a partir do livro |
| [docs/architecture.md](docs/architecture.md) | SDK, config layers, orchestrator |
| [docs/lineage.md](docs/lineage.md) | Lineage por app |

Setup cloud: [azure-infra](docs/azure-infra-setup.md) · [adf](docs/azure-adf-setup.md) · [sql](docs/sql-server-setup.md) · [spark](docs/spark-processing.md) · [agent_book](docs/agent_book-azure-setup.md) · [agent_book MCP](docs/agent_book-mcp-setup.md)

---

## Repositório

```text
dataplatform/          # SDK compartilhado
apps/                  # pipelines + Agent Book (DATA_PLATFORM_APP)
config/platform/       # settings globais por ambiente
infra/                 # Bicep + ADF
docker/                # SQL init, scripts Azure, Spark
docs/
```

---

## License

MIT
