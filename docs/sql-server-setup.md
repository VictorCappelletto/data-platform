# SQL Server local — setup Olist

Primeira etapa do projeto Olist/Azure: banco SQL Server local como fonte de dados (equivalente ao SQL Server do curso, substituindo Kaggle/ADLS em dev).

## Opção A — Docker (recomendado)

Requisito: Docker Desktop em execução.

```powershell
# 1. Copie variáveis
copy .env.example .env

# 2. Suba o SQL Server
docker compose up -d sqlserver

# 3. Aguarde ~30s e rode o init (schema + dados mock)
.\docker\sql\setup.ps1 -UseDocker
```

Conexão:

| Campo | Valor |
|-------|-------|
| Server | `localhost,1433` |
| Database | `olist` |
| User | `sa` |
| Password | valor de `MSSQL_SA_PASSWORD` no `.env` (default: `Olist@Dev123!`) |

## Opção B — SQL Server Express (Windows nativo)

```powershell
winget install Microsoft.SQLServer.2022.Express --accept-package-agreements
winget install Microsoft.Sqlcmd --accept-package-agreements
winget install Microsoft.msodbcsql.18 --accept-package-agreements
```

Após instalar, habilite TCP/IP no **SQL Server Configuration Manager** e defina senha do `sa`.

```powershell
$env:MSSQL_SA_PASSWORD = "SuaSenhaForte!"
.\docker\sql\setup.ps1 -Server "localhost\SQLEXPRESS"
```

## Verificar

```powershell
sqlcmd -S localhost,1433 -U sa -P "Olist@Dev123!" -C -Q "USE olist; SELECT COUNT(*) AS orders FROM dbo.orders;"
```

Resultado esperado: `3` orders (dados mock em `docker/sql/init/02_seed_sample_data.sql`).

## Próximas etapas (roadmap)

1. ~~SQL Server local + schema Olist~~
2. App `olist_ingestion_project` — extrair do SQL → lake local
3. Linked service Azure Data Factory → SQL Server (via gateway ou Azure quando migrar)
4. Pipelines ADF → ADLS / Databricks (como no [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1))

## Dados mock vs produção

| Ambiente | Fonte |
|----------|-------|
| Local | `docker/sql/init/02_seed_sample_data.sql` (3 orders, 3 customers) |
| Dev/prod | Kaggle full dataset ou restore backup → SQL Server |
| Azure | ADF copia SQL → ADLS landing |
