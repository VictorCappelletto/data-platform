# Olist transform/publish — ADF Custom Activity (Azure Batch).
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates unixodbc unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY dataplatform ./dataplatform
COPY apps/ingestion_azure ./apps/ingestion_azure

RUN pip install --no-cache-dir -e ".[azure]"

ENV DATA_PLATFORM_ROOT=/app \
    DATA_PLATFORM_APP=ingestion_azure \
    OLIST_LAKE_BACKEND=adls \
    OLIST_PROCESSING_ENGINE=local \
    PLATFORM_ENV=azure \
    PYTHONUNBUFFERED=1

WORKDIR /app/apps/ingestion_azure

ENTRYPOINT ["python", "workflows/runs/olist_demo.py"]
CMD ["--mode", "transform_from_landing"]
