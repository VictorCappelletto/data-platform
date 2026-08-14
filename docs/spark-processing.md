# Spark processing — Olist pipeline

PySpark engine for `ingestion_azure`, aligned with [olist_processing.ipynb](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1/blob/main/Databricks/olist_processing.ipynb).

## Engines

| Engine | Env | Deps | Uso |
|--------|-----|------|-----|
| `local` | default | `pyarrow` | Dev rápido, sem JVM |
| `spark` | `OLIST_PROCESSING_ENGINE=spark` | `pyspark` | Igual Databricks |

## Windows

Requisitos extras para PySpark escrever parquet:

1. **Java 17+** — `winget install Microsoft.OpenJDK.17`
2. **JAVA_HOME** — ex.: `C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot`
3. **winutils.exe + hadoop.dll** — script do repo (baixa Hadoop 3.3.6 de [cdarlint/winutils](https://github.com/cdarlint/winutils) para `docker/spark/hadoop/bin/`):

```powershell
powershell -ExecutionPolicy Bypass -File docker/spark/setup-hadoop-windows.ps1
```

O código define `HADOOP_HOME`, adiciona `bin` ao `PATH`, copia `hadoop.dll` para `%JAVA_HOME%\bin` e aplica short paths (8.3) para evitar quebra com OneDrive/`Área de Trabalho`. Tudo isso acontece automaticamente ao usar `OLIST_PROCESSING_ENGINE=spark`.

Opcional — persistir `HADOOP_HOME`:

```powershell
[Environment]::SetEnvironmentVariable('HADOOP_HOME', '<repo>\docker\spark\hadoop', 'User')
```

**Nota:** PySpark 4.x usa Hadoop 3.5 internamente; os binários 3.3.6 funcionam para escrita parquet local. Se falhar após upgrade do PySpark, re-execute o setup ou use `OLIST_PROCESSING_ENGINE=local`.

4. **Paths unicode** — OneDrive `Área de Trabalho` quebra Spark; o código copia o lake para `%TEMP%\data-platform-spark-lake` automaticamente.

Sem winutils, use `OLIST_PROCESSING_ENGINE=local` para processing/curated (pyarrow) — landing export e Spark **read** já funcionam.

## Instalar

```powershell
pip install -e ".[olist]"
# ou
pip install pyspark pyarrow pyodbc
```

## Rodar com Spark local (sem cluster)

```powershell
set DATA_PLATFORM_APP=ingestion_azure
set OLIST_PROCESSING_ENGINE=spark
set SPARK_MASTER=local[*]
python -c "from dataplatform.bootstrap import bootstrap; bootstrap('ingestion_azure'); from workflows.runs.olist_demo import run_full; print(run_full())"
```

## Cluster Docker (profile spark)

Workers precisam ver os CSVs em `data/lake`:

```powershell
docker compose --profile spark up -d spark-master spark-worker
set SPARK_MASTER=spark://localhost:7077
set OLIST_PROCESSING_ENGINE=spark
set LAKE_ROOT=./data/lake
python -c "from dataplatform.bootstrap import bootstrap; bootstrap('ingestion_azure'); from workflows.runs.olist_demo import run_full; print(run_full())"
```

UI Spark: http://localhost:8081

## Módulo

| Notebook | Spark module |
|----------|--------------|
| `spark.read.csv` landing | `SparkOlistProcessor.read_landing_csv` |
| `df.write.parquet` | `SparkOlistProcessor.write_parquet` |
| `filter(col == RJ)` | `SparkOlistProcessor.apply_filters` |
| curated CSV | `SparkOlistProcessor.write_csv` |

Código: `apps/ingestion_azure/transformation/olist.py`

## ADLS + Spark (futuro)

Com `OLIST_LAKE_BACKEND=adls` e jars `hadoop-azure`, paths `abfss://` funcionam como no mount do notebook. Para portfolio local, use `local` + `file://` URIs.
