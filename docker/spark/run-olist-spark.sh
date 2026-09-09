#!/usr/bin/env bash
# Run Spark processing steps (landing CSVs must exist).
set -euo pipefail
cd /workspace/apps/ingestion_azure
export DATA_PLATFORM_ROOT=/workspace
export DATA_PLATFORM_APP=ingestion_azure
export OLIST_PROCESSING_ENGINE=spark
export SPARK_MASTER="${SPARK_MASTER:-local[*]}"
export PLATFORM_ENV=local
export LAKE_ROOT=/data/lake

/opt/bitnami/python/bin/python <<'PY'
from dataplatform.bootstrap import bootstrap
bootstrap()
from transformation.olist import (
    run_curated,
    run_read_landing,
    run_write_processing,
)
import json

result = {
    "engine": "spark",
    "landing_read": run_read_landing(),
    "processing": run_write_processing(),
    "curated": run_curated(),
}
print(json.dumps(result, indent=2, default=str))
PY
