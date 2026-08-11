"""Brewery ingest DAG — landing → bronze → silver (06:00, no overlap with gold)."""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def _run_ingest():
    from brewery_etl.pipelines import run_ingest_pipeline

    return run_ingest_pipeline()


if DAG is not None:
    with DAG(
        dag_id="brewery_ingest",
        start_date=datetime(2026, 1, 1),
        schedule="0 6 * * *",
        catchup=False,
        max_active_runs=1,
        max_active_tasks=2,
        tags=["brewery", "ingest", "medallion"],
        default_args={
            "owner": "data-platform",
            "retries": 2,
            "retry_delay": timedelta(minutes=5),
            "pool": "brewery_pool",
        },
    ) as dag:
        PythonOperator(task_id="ingest_landing_bronze_silver", python_callable=_run_ingest)
