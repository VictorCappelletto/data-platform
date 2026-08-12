# Medallion Ingestion App

Portfolio demo: orders + brewery pipelines on medallion lake layers.

## Layout (frontline-style)

```text
apps/medalion_ingestion_project/
├── config/              # all app configuration
│   ├── app.yml          # app id, lake prefix, domain settings
│   ├── constants.yml
│   ├── dags/
│   └── products/
├── src/                 # pipeline code
├── dags/                # thin Airflow modules
└── seeds/
```

Lake data: `{lake_root}/{env}/medalion_ingestion_project/{layer}/...`

## Env

```bash
DATA_PLATFORM_APP=medalion_ingestion_project
DATA_PLATFORM_ROOT=.
PLATFORM_ENV=local
```
