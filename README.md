# data-platform

Monorepo de **plataforma de dados** para portfólio e experimentação. Combina um SDK compartilhado, apps isolados por domínio, orquestração orientada a YAML e arquitetura medallion.

**Referências de arquitetura e código:** padrões GROW / frontline-force (config por processo, base classes, orchestrator fino) e pipeline Azure Olist do [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1) (ADF → ADLS → transform → consumo SQL → Power BI).

---

## Descrição técnica

### Objetivo

Demonstrar duas linhas de pipeline no **mesmo monorepo**, compartilhando SDK (`dataplatform/`) e convenções de código, sem acoplar domínios entre apps:

| App | Caso de uso | Orquestração | Lake / storage |
|-----|-------------|--------------|----------------|
| [`medalion_ingestion_project`](apps/medalion_ingestion_project/) | Demo medallion genérico (orders + brewery) | Airflow (YAML + orchestrator) | Filesystem local / S3 |
| [`ingestion_azure`](apps/ingestion_azure/) | Pipeline Olist Azure (port do notebook Databricks) | ADF (landing) + scripts Python (transform/consumo) | ADLS Gen2 + SQL Server |

Ambos seguem o **mesmo modelo de código**: config YAML por processo, classes base por etapa, lógica de domínio em módulos flat (`extraction/`, `ingestion/`, `transformation/`, `consumption/`), entry points finos para execução local ou remota.

### Modelo de código (padrão a manter)

Este repositório adota o layout enterprise simplificado abaixo. Novos apps e refactors devem **preservar essas camadas** — amanhã validaremos aderência total ao modelo do projeto de referência.

```text
apps/<app_id>/
├── config/
│   ├── app.yml                         # id, lake_prefix, overrides por ambiente
│   ├── constants.yml                   # constantes do app
│   ├── <processo>/config_<processo>.yml  # domínios por etapa (extraction, ingestion, …)
│   ├── orchestration/*.yml             # task → orchestrator → domain module
│   └── workflows/*.yml                 # schedule, DAG, dependências
├── <processo>/                         # código de domínio (flat)
│   ├── base.py                         # ProjectProcessBase / hooks compartilhados
│   └── <dominio>.py                    # implementação concreta
├── orchestrator/                       # front door — bootstrap + delega ao domínio
├── runtime.py                          # bootstrap env + PYTHONPATH
├── workflows/                          # DAGs Airflow + runs/ (demos locais)
├── seeds/                              # fixtures locais (substituem fonte remota em dev)
└── tests/
```

**Regras de implementação:**

| Regra | Detalhe |
|-------|---------|
| Config over code | Domínios, tabelas, filtros, layers e schedules vivem em YAML; Python lê via `ConfigLoader(app=...)` |
| Base + hooks | Cada processo tem `base.py`; domínios implementam só hooks (`extract()`, `to_bronze()`, `transform()`, …) |
| Orchestrator fino | Airflow/CLI/scripts chamam `orchestrator.*:run`, nunca lógica de negócio inline |
| SDK compartilhado | I/O de lake, config, DQ, logging e Airflow factory ficam em `dataplatform/` — sem regra de negócio |
| App isolado | `DATA_PLATFORM_APP` seleciona o app; apps não importam código um do outro |
| Lake prefixado | Paths: `{lake_root}/{env}/{lake_prefix}/{layer}/...` |

**Mapeamento com projetos de referência:**

| Conceito | GROW / frontline | Este repo |
|----------|------------------|-----------|
| Projeto / app | `projects/grow/` ou `notebooks/<app>/` | `apps/<app_id>/` |
| Workflow | `workflows/*.json` | `config/workflows/*.yml` |
| Orchestrator | `orchestrator/*.ipynb` | `orchestrator/<domain>/*.py` |
| Domínio | `projects/grow/<domain>/` | `<processo>/<dominio>.py` |
| Config por etapa | `configs/<processo>/` | `config/<processo>/config_<processo>.yml` |

Documentação detalhada: [docs/architecture.md](docs/architecture.md).

### Pipeline Olist Azure (`ingestion_azure`)

Port Python do notebook [`olist_processing.ipynb`](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1/blob/main/Databricks/olist_processing.ipynb), alinhado ao diagrama do [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1):

```text
SQL Server (olist)                    ← fonte operacional (Docker local)
        │
        ▼  Azure Data Factory + SHIR   ← pl_olist_landing_copy (8 CSVs)
ADLS Gen2  landing/
        │
        ▼  transformation              ← pyarrow local ou PySpark (substitui Databricks)
ADLS Gen2  processing/ + curated/
        │
        ├─► Spark SQL customers_db     ← catálogo externo (opcional, local/adls)
        └─► SQL Server olist_dw        ← bronze / silver / gold (consumo analítico)
                │
                ▼
            Power BI Desktop         ← gold.customers_RJ
```

**Componentes Azure (dev):**

| Recurso | Nome / artefato | Função |
|---------|-----------------|--------|
| Resource Group | `rg-olist-dev` | Agrupa recursos |
| Storage ADLS Gen2 | `stolist*` — containers `landing`, `processing`, `curated` | Data lake |
| Data Factory | `adf-olist*` + `infra/adf/` | Copy SQL → landing |
| Self-hosted IR | `shir-olist-dev` | Ponte SQL Docker ↔ ADF |
| IaC | `infra/main.bicep` | Deploy + RBAC (MI ADF → storage) |
| CI/CD | `.github/workflows/azure-infra.yml`, `azure-adf-landing.yml` | Deploy OIDC |

**Mapeamento lake ↔ SQL Server (medallion de consumo):**

| Zona ADLS / local | Schema `olist_dw` | Conteúdo |
|-------------------|-------------------|----------|
| `landing/*.csv` | `bronze.*` | 8 tabelas raw |
| `processing/*.parquet` | `silver.*` | 8 tabelas + `customers_RJ` |
| `curated/*.csv` | `gold.*` | `customers_RJ` (Power BI) |

**Engines de processamento:**

| Engine | Variável | Uso |
|--------|----------|-----|
| Local (pyarrow) | `OLIST_PROCESSING_ENGINE=local` | Default, sem JVM |
| PySpark | `OLIST_PROCESSING_ENGINE=spark` | Paridade com Databricks |
| ADLS I/O | `OLIST_LAKE_BACKEND=adls` | `abfss://` via `DefaultAzureCredential` |

**Substituições conscientes vs. diagrama original:**

| Componente original | Implementação atual | Status |
|--------------------|---------------------|--------|
| Databricks | Python + PySpark local | ✅ lógica portada |
| Azure Synapse | SQL Server `olist_dw` | ✅ consumo SQL |
| Power BI service | Power BI Desktop + doc | ⚠️ conexão manual |
| Orquestração end-to-end ADF | ADF só landing; transform via script/Makefile | ⚠️ parcial |

Mapeamento notebook → módulos: [docs/olist-databricks-mapping.md](docs/olist-databricks-mapping.md).

### Pipeline demo medallion (`medalion_ingestion_project`)

Pipeline clássico **landing → bronze → silver → gold** com Airflow:

| Domínio | Fluxo | DAGs |
|---------|-------|------|
| Orders | seed CSV → landing → bronze → silver → KPIs → export | `hdl_ingest` → `kpi_metrics` → `analytics_export` |
| Brewery | API/fixture → landing → bronze → silver → DQ → gold | `brewery_ingest` → `brewery_dq_gold` |

Lake: `data/lake/local/medalion_ingestion_project/{landing,bronze,silver,gold}/`.

Lineage: [docs/lineage.md](docs/lineage.md).

### Stack e dependências

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.10+ |
| Config | YAML + `python-dotenv` |
| Orquestração local | Airflow 2.9 (Docker Compose) |
| Orquestração Azure | ADF + GitHub Actions (OIDC) |
| Lake local | Filesystem / MinIO (S3 compat) |
| Lake Azure | ADLS Gen2 (`azure-identity`, `azure-storage-file-datalake`) |
| SQL | SQL Server 2022 (Docker), `pyodbc` |
| Processamento | `pyarrow`, `pyspark` (opcional) |
| Qualidade | `dataplatform.data_quality` |
| IaC | Bicep (`infra/`) |
| CI | GitHub Actions — lint (`ruff`) + `pytest` |

Instalação por perfil (`pyproject.toml`):

```bash
pip install -e ".[dev]"      # testes + lint
pip install -e ".[olist]"     # ingestion_azure (pyodbc, pyarrow, pyspark, azure)
pip install -e ".[spark]"     # PySpark standalone
```

### Comandos principais (Olist Azure)

```powershell
make sql-init                  # olist + olist_dw (bronze/silver/gold)
make azure-infra-deploy        # RG + storage + ADF (Bicep)
make azure-adf-publish         # publica artefatos ADF
make azure-adf-trigger         # SQL → ADLS landing
make azure-olist-transform     # landing → processing → curated (ADLS)
make azure-olist-publish-sql   # lake → olist_dw (bronze/silver/gold)
make olist-publish-sql         # idem, lake local
make olist-spark-catalog       # Spark SQL customers_db
```

Ver [Makefile](Makefile), [docs/azure-adf-setup.md](docs/azure-adf-setup.md), [docs/power-bi-setup.md](docs/power-bi-setup.md).

### Estado atual e próxima revisão

| Área | Status |
|------|--------|
| SDK + app demo medallion | ✅ funcional (Airflow + demos locais) |
| Infra Azure (storage, ADF, SHIR) | ✅ deployado e testado |
| Pipeline Olist end-to-end | ✅ SQL → ADLS → transform → SQL consumo |
| Aderência código ↔ Curso_Pipeline_Azure1 | ✅ [architecture-audit.md](docs/architecture-audit.md) |
| Aderência código ↔ GROW/frontline | ✅ [architecture-audit.md](docs/architecture-audit.md) |
| Databricks workspace / Synapse | ⏸️ fora de escopo (custo) |
| `.pbix` versionado | ⏸️ não iniciado |

**Auditoria concluída (2026-08-13):** ver [docs/architecture-audit.md](docs/architecture-audit.md). `ingestion_azure` recebeu camada `orchestrator/` + workflows YAML alinhados ao padrão medalion.

---

## O que é este repositório?

| Pergunta | Resposta |
|----------|----------|
| **Para quê?** | Demonstrar pipelines medallion + pipeline Azure Olist em monorepo portfolio-ready |
| **Para quem?** | Data engineers navegando, estendendo ou clonando como base |
| **O que roda hoje?** | [`medalion_ingestion_project`](apps/medalion_ingestion_project/) (Airflow) + [`ingestion_azure`](apps/ingestion_azure/) (ADF + ADLS + SQL) |
| **Como orquestra?** | Airflow (demo) · ADF + scripts Make (Azure) · runners Python locais |
| **Onde ficam os dados?** | `data/lake/{env}/{app_id}/...` (local) · `abfss://{container}@...` (Azure) |

---

## Comece por aqui

| # | Documento | Conteúdo |
|---|-----------|----------|
| 1 | Este README | Visão geral, descrição técnica e navegação |
| 2 | [docs/architecture.md](docs/architecture.md) | Design, camadas de config, padrão GROW/frontline |
| 3 | [docs/lineage.md](docs/lineage.md) | Lineage orders, brewery e Olist Azure |
| 4 | [apps/medalion_ingestion_project/README.md](apps/medalion_ingestion_project/README.md) | App demo medallion (Airflow) |
| 5 | [apps/ingestion_azure/README.md](apps/ingestion_azure/README.md) | Pipeline Olist Azure (ADF + ADLS) |
| 6 | [docs/olist-databricks-mapping.md](docs/olist-databricks-mapping.md) | Notebook Databricks → módulos Python |
| 7 | [docs/power-bi-setup.md](docs/power-bi-setup.md) | Consumo Power BI (`olist_dw.gold.*`) |
| 8 | [.env.example](.env.example) | Variáveis de ambiente |

### Rodar em 2 minutos (sem Docker)

```bash
python -m pip install -e ".[dev]"

# Windows
set DATA_PLATFORM_APP=medalion_ingestion_project
set PLATFORM_ENV=local

# Linux/macOS
# export DATA_PLATFORM_APP=medalion_ingestion_project
# export PLATFORM_ENV=local

python apps/medalion_ingestion_project/workflows/runs/orders_demo.py   # orders: landing → gold → export
python apps/medalion_ingestion_project/workflows/runs/brewery_demo.py  # brewery: landing → gold + DQ
python apps/medalion_ingestion_project/orchestrator/quality/inspect_lake.py                 # validar paths e row counts
pytest -q
```

### Rodar com Airflow (Docker)

```bash
cp .env.example .env
docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler
```

UI: http://localhost:8080 — usuário/senha: `admin` / `admin`

---

## Como navegar no repositório

```text
data-platform/
│
├── config/                         # CONFIG GLOBAL (compartilhada entre apps)
│   ├── platform/                   #   local | dev | prod — lake, secrets, logging
│   ├── constants.yml               #   layers medallion (landing, bronze, silver, gold)
│   └── env/                        #   templates .env por ambiente
│
├── dataplatform/                   # SDK compartilhado (flat)
│   ├── config.py                   #   YAML loader + settings
│   ├── lake.py                     #   LayerPaths, LakeIO, Spark
│   ├── data_quality.py             #   checks + runner
│   ├── utils.py                    #   logging, dates, retry, secrets
│   └── airflow.py                  #   factory — monta DAGs a partir de YAML
│
├── apps/                           # APPS (cada um autocontido)
│   ├── medalion_ingestion_project/ # demo medallion — Airflow, orders + brewery
│   │   ├── config/                 #   app.yml, workflows/, orchestration/, <processo>/
│   │   ├── orchestrator/           #   entry points Airflow
│   │   ├── extraction/ ingestion/ transformation/
│   │   ├── seeds/ tests/ workflows/
│   │   └── README.md
│   └── ingestion_azure/            # pipeline Olist Azure — ADF + ADLS + SQL
│       ├── config/                 #   extraction, ingestion, transformation, consumption
│       │   ├── orchestration/      #   task → orchestrator → domain
│       │   └── workflows/          #   DAG graphs (Airflow-ready)
│       ├── orchestrator/           #   1 módulo por processo
│       ├── workflows/runs/         #   extraction | ingestion | transformation | consumption + olist_demo
│       ├── extraction/ ingestion/ transformation/ consumption/
│       ├── runtime.py tests/
│       └── README.md
├── infra/                          # Bicep (storage, ADF) + artefatos ADF (JSON)
├── docker/                         # scripts Azure, SQL init, Spark/Hadoop Windows
├── docs/                           # documentação da plataforma
│   ├── architecture.md lineage.md
│   ├── azure-*.md power-bi-setup.md olist-databricks-mapping.md
│   └── …
└── docker-compose.yml              # stack local (Airflow + Postgres + MinIO + SQL Server)
```

### Onde mexer para cada tarefa

| Quero… | Onde ir |
|--------|---------|
| Alterar schedule ou tasks de um workflow | `apps/<app>/config/workflows/*.yml` |
| Alterar mapeamento task → script Python | `apps/<app>/config/orchestration/*.yml` |
| Alterar entry point que o Airflow executa | `apps/<app>/orchestrator/` |
| Alterar regra de DQ ou domínio | `apps/<app>/config/<processo>/config_<processo>.yml` |
| Alterar lógica de pipeline | `apps/<app>/<processo>/` (ex: `ingestion/orders.py`) |
| Rodar workflow localmente | `python apps/<app>/workflows/runs/*_demo.py` |
| Alterar dados de entrada do demo | `apps/<app>/seeds/` |
| Alterar lake root ou ambiente | `config/platform/local.yml` + `.env` |
| Adicionar utilitário compartilhado | `dataplatform/` |
| Rodar pipeline Olist (local) | `DATA_PLATFORM_APP=ingestion_azure` + ver [app README](apps/ingestion_azure/README.md) |
| Deploy / pipeline Azure | `make azure-*` — ver [docs/azure-adf-setup.md](docs/azure-adf-setup.md) |

| Criar um novo app | Copiar `apps/medalion_ingestion_project/` → `apps/<novo>/` |

---

## App: `ingestion_azure`

Pipeline Olist espelhando [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1): SQL Server → ADF → ADLS → transform → `olist_dw` (bronze/silver/gold) → Power BI.

```powershell
set DATA_PLATFORM_APP=ingestion_azure
pip install -e ".[olist]"
make sql-init
make azure-adf-trigger          # requer Azure + SHIR online
make azure-olist-transform
make azure-olist-publish-sql
```

Detalhes: [app README](apps/ingestion_azure/README.md) · [lineage Olist](docs/lineage.md#olist-azure-pipeline-ingestion_azure) · [power-bi-setup](docs/power-bi-setup.md)

---

## App: `medalion_ingestion_project`

Demonstração medallion com dois domínios:

| Pipeline | DAG(s) | Fluxo |
|----------|--------|-------|
| **Orders** | `hdl_ingest` → `kpi_metrics` → `analytics_export` | seed CSV → landing → bronze → silver → KPIs → export |
| **Brewery** | `brewery_ingest` → `brewery_dq_gold` | API/fixture → landing → bronze → silver → DQ → gold |

Seeds (dados de demo):

```text
apps/medalion_ingestion_project/seeds/
├── orders_raw.csv           # 6 pedidos (orders pipeline)
└── breweries_sample.json  # 4 cervejarias, 3 após dedup (brewery pipeline)
```

Lake gerado localmente:

```text
data/lake/local/medalion_ingestion_project/
├── landing/
├── bronze/
├── silver/
└── gold/
```

Detalhes: [app README](apps/medalion_ingestion_project/README.md) · [lineage](docs/lineage.md) · [architecture](docs/architecture.md)

---

## Configuração

### Variáveis de ambiente principais

| Variável | Exemplo | Função |
|----------|---------|--------|
| `DATA_PLATFORM_APP` | `medalion_ingestion_project` ou `ingestion_azure` | Qual app carregar |
| `DATA_PLATFORM_ROOT` | `.` | Raiz do repositório |
| `PLATFORM_ENV` | `local` | Ambiente (`local`, `dev`, `prod`) |
| `LAKE_ROOT` | `./data/lake` | Raiz do data lake |

Ver [.env.example](.env.example) para a lista completa.

### Camadas de config

| Camada | Arquivo | Conteúdo |
|--------|---------|----------|
| Platform | `config/platform/{env}.yml` | Lake, secrets, logging |
| App | `apps/<id>/config/app.yml` | App id, lake prefix |
| Processo | `apps/<id>/config/<processo>/config_<processo>.yml` | Domínios, layers, DQ, KPIs |
| Orchestration | `apps/<id>/config/orchestration/*.yml` | Registro task → orchestrator → domain module |
| Workflow | `apps/<id>/config/workflows/*.yml` | Schedule, tasks (`orchestrator:` entry points) |

---

## Desenvolvimento

```bash
# Instalar
python -m pip install -e ".[dev]"

# Qualidade
pytest -q
ruff check dataplatform apps

# Demos
python apps/medalion_ingestion_project/workflows/runs/orders_demo.py
python apps/medalion_ingestion_project/workflows/runs/brewery_demo.py
python apps/medalion_ingestion_project/orchestrator/quality/inspect_lake.py
```

CI (GitHub Actions): lint → test (inclui validação de imports dos workflows) — ver [.github/workflows/ci.yml](.github/workflows/ci.yml).

---

## Adicionar um novo app

1. Copie `apps/medalion_ingestion_project/` → `apps/<novo_app_id>/`
2. Edite `config/app.yml` (id, lake prefix, domínios)
3. Adapte pipelines em `extraction/`, `ingestion/`, `transformation/`
4. Coloque seeds em `apps/<novo_app_id>/seeds/`
5. Configure `DATA_PLATFORM_APP=<novo_app_id>` no `.env` e `docker-compose.yml`
6. Monte `apps/<novo_app_id>/workflows/` no Airflow

Guia completo: [docs/architecture.md](docs/architecture.md)

---

## Documentação

Documentação canônica da plataforma em [`docs/`](docs/):

| Documento | Quando ler |
|-----------|------------|
| [docs/architecture-audit.md](docs/architecture-audit.md) | Auditoria de aderência ao modelo de código e Curso_Pipeline_Azure1 |
| [docs/lineage.md](docs/lineage.md) | Fluxo de dados (orders, brewery, Olist Azure) |
| [docs/azure-infra-setup.md](docs/azure-infra-setup.md) | Deploy RG + storage (Bicep) |
| [docs/azure-adf-setup.md](docs/azure-adf-setup.md) | ADF, SHIR, pipeline landing |
| [docs/olist-databricks-mapping.md](docs/olist-databricks-mapping.md) | Notebook → código Python |
| [docs/power-bi-setup.md](docs/power-bi-setup.md) | Conectar Power BI ao `olist_dw` |
| [docs/spark-processing.md](docs/spark-processing.md) | Engine PySpark local |
| [docs/sql-server-setup.md](docs/sql-server-setup.md) | SQL Server Docker + schemas |

Documentação por app:

| Documento | Quando ler |
|-----------|------------|
| [apps/medalion_ingestion_project/README.md](apps/medalion_ingestion_project/README.md) | Demo medallion, processos, tasks |
| [apps/ingestion_azure/README.md](apps/ingestion_azure/README.md) | Pipeline Olist, variáveis, roadmap |

---

## License

MIT — Victor Cappelletto
