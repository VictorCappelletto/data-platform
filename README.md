# data-platform

Monorepo de **plataforma de dados** para portfólio e experimentação. Combina um SDK compartilhado, apps isolados por domínio, orquestração Airflow orientada a YAML e arquitetura medallion (landing → bronze → silver → gold).

Inspirado em padrões de empresas como GROW e frontline-force: config centralizada, código de negócio dentro do app, infra global reutilizável.

---

## O que é este repositório?

| Pergunta | Resposta |
|----------|----------|
| **Para quê?** | Demonstrar pipelines de ingestão, transformação, KPIs, DQ e export em um lake medallion |
| **Para quem?** | Você (dev/data engineer) navegando, estendendo ou clonando como base para novos projetos |
| **O que roda hoje?** | App [`medalion_ingestion_project`](apps/medalion_ingestion_project/) — orders + brewery |
| **Como orquestra?** | Airflow (Docker Compose local) ou scripts Python sem cluster |
| **Onde ficam os dados?** | `data/lake/{env}/{app_id}/{layer}/...` (local por padrão) |

---

## Comece por aqui

| # | Documento | Conteúdo |
|---|-----------|----------|
| 1 | Este README | Visão geral e navegação do repositório |
| 2 | [apps/medalion_ingestion_project/README.md](apps/medalion_ingestion_project/README.md) | Estrutura e processos do app demo |
| 3 | [docs/architecture.md](docs/architecture.md) | Design, camadas de config, comparação com GROW/frontline |
| 4 | [docs/lineage.md](docs/lineage.md) | Lineage dos dados (orders + brewery) |
| 5 | [.env.example](.env.example) | Variáveis de ambiente |

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
│   └── medalion_ingestion_project/
│       ├── config/                 #   app.yml, workflows/, orchestration/, <processo>/
│       ├── orchestrator/           #   entry points Airflow (orders, brewery, analytics)
│       ├── workflows/              #   módulos Airflow + runs/ (demos locais)
│       ├── extraction/             #   base.py + brewery.py
│       ├── ingestion/              #   base.py + brewery.py + orders.py (flat)
│       ├── transformation/         #   base.py + brewery.py, kpi.py, export.py
│       ├── seeds/                  #   dados de entrada (CSV/JSON) do demo
│       ├── tests/                  #   testes do app + SDK (data quality, platform)
│       └── README.md               #   doc específica do app
├── docs/                           # documentação da plataforma
│   ├── architecture.md             #   design, config loader, orchestration
│   └── lineage.md                  #   fluxo de dados orders + brewery
└── docker-compose.yml              # stack local (Airflow + Postgres + MinIO)
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
| Criar um novo app | Copiar `apps/medalion_ingestion_project/` → `apps/<novo>/` |

---

## App ativo: `medalion_ingestion_project`

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
| `DATA_PLATFORM_APP` | `medalion_ingestion_project` | Qual app carregar |
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
| [docs/architecture.md](docs/architecture.md) | Entender design, camadas (workflow / orchestrator / domain), config loader e como adicionar apps |
| [docs/lineage.md](docs/lineage.md) | Ver de onde vêm e para onde vão os dados (orders e brewery) |

Documentação por app:

| Documento | Quando ler |
|-----------|------------|
| [apps/medalion_ingestion_project/README.md](apps/medalion_ingestion_project/README.md) | Estrutura do app demo, processos e como rodar tasks individuais |

---

## License

MIT — Victor Cappelletto
