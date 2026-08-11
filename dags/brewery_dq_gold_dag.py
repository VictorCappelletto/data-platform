"""Brewery DQ + gold DAG — runs after ingest (07:30, staggered schedule)."""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def _run_dq_gold():
    from brewery_etl.pipelines import run_dq_gold

    return run_dq_gold()


if DAG is not None:
    with DAG(
        dag_id="brewery_dq_gold",
        start_date=datetime(2026, 1, 1),
        schedule="30 7 * * *",
        catchup=False,
        max_active_runs=1,
        max_active_tasks=1,
        tags=["brewery", "dq", "gold"],
        default_args={
            "owner": "data-platform",
            "retries": 2,
            "retry_delay": timedelta(minutes=5),
            "pool": "brewery_pool",
        },
    ) as dag:
        PythonOperator(task_id="dq_and_gold", python_callable=_run_dq_gold)
